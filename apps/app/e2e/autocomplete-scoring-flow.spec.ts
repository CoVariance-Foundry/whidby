import { test, expect, type Page, type Request } from "@playwright/test";
import { signIn } from "./helpers/auth";

/**
 * Diagnoses the Huntsville autocomplete-selection bug.
 *
 * The user reports: selecting Huntsville from the autocomplete dropdown still
 * produces "Scoring engine did not return a result." This test exercises the
 * exact flow — type, wait for suggestions, click one, submit — while capturing
 * the outbound network request to /api/agent/scoring to confirm whether the
 * structured metadata (dataforseo_location_code, place_id, state) actually
 * makes it into the POST body.
 */

test.setTimeout(120_000);

test.describe("Autocomplete → score flow (Huntsville diagnosis)", () => {
  test("selecting Huntsville from autocomplete attaches structured metadata to scoring request", async ({
    page,
  }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });
    await page.goto("/niche-finder");
    await page.waitForLoadState("networkidle");

    // -- Step 0: verify the places suggest API is reachable once signed in -----
    const placesCheck = await page.evaluate(async () => {
      try {
        const res = await fetch("/api/agent/places/suggest?q=Phoenix&limit=3");
        return { status: res.status, ok: res.ok, body: await res.text() };
      } catch (err) {
        return { status: 0, ok: false, body: String(err) };
      }
    });
    test.info().annotations.push({
      type: "places-health-check",
      description: `status=${placesCheck.status} ok=${placesCheck.ok} body=${placesCheck.body.slice(0, 500)}`,
    });

    // -- Step 1: type "Huntsville" keystroke-by-keystroke ----------------------
    // data-testid="city-input" is directly on the <input> (forwarded prop).
    const cityInput = page.getByTestId("city-input");
    await expect(cityInput).toBeVisible({ timeout: 10_000 });

    // Clear and type to trigger the real React onChange + debounced fetch.
    await cityInput.click();
    await cityInput.pressSequentially("Huntsville", { delay: 50 });

    // Wait for the autocomplete listbox to appear.
    const listbox = page.getByRole("listbox", { name: /city suggestions/i });
    let listboxVisible = false;
    try {
      await expect(listbox).toBeVisible({ timeout: 15_000 });
      listboxVisible = true;
    } catch {
      // Listbox never appeared — capture diagnostic info.
      test.info().annotations.push({
        type: "listbox-visible",
        description: "false — autocomplete dropdown never appeared after typing",
      });
    }

    // Also directly call the places API from the authenticated browser context
    // to check what data we'd get.
    const placesResponse = await page.evaluate(async () => {
      try {
        const res = await fetch("/api/agent/places/suggest?q=Huntsville&limit=8");
        if (!res.ok) return { error: `HTTP ${res.status}`, body: await res.text() };
        return await res.json();
      } catch (err) {
        return { error: String(err) };
      }
    });
    test.info().annotations.push({
      type: "places-api-response",
      description: JSON.stringify(placesResponse).slice(0, 2000),
    });

    // Check if any suggestion has a dataforseo_location_code.
    const suggestions = Array.isArray(placesResponse) ? placesResponse : [];
    const withDfsCode = suggestions.filter(
      (s: Record<string, unknown>) =>
        typeof s.dataforseo_location_code === "number" &&
        s.dataforseo_location_code > 0,
    );
    test.info().annotations.push({
      type: "suggestions-with-dfs-code",
      description: `${withDfsCode.length} of ${suggestions.length}`,
    });

    if (!listboxVisible) {
      // If listbox didn't show, fall back to just submitting the raw text to
      // see what request body the form produces.
      test.info().annotations.push({
        type: "fallback",
        description: "Submitting with raw text since autocomplete dropdown did not appear.",
      });
    } else {
      // Capture what suggestions came back.
      const options = listbox.getByRole("option");
      const optionCount = await options.count();
      test.info().annotations.push({
        type: "suggestion-count",
        description: String(optionCount),
      });

      for (let i = 0; i < Math.min(optionCount, 5); i++) {
        const text = await options.nth(i).textContent();
        test.info().annotations.push({
          type: `suggestion-${i}`,
          description: text ?? "(empty)",
        });
      }

      // Click the first selectable suggestion.
      const firstOption = options.first();
      const disabled = await firstOption.getAttribute("aria-disabled");
      if (disabled !== "true" && optionCount > 0) {
        await firstOption.click();
        await page.waitForTimeout(300);
      }
    }

    // After selection (or fallback), capture the input value.
    const inputValueAfterSelect = await page.getByTestId("city-input").inputValue();
    test.info().annotations.push({
      type: "input-after-select",
      description: inputValueAfterSelect,
    });

    await page.waitForTimeout(200);

    // -- Step 4: fill in service and capture the scoring request ---------------
    await page.getByTestId("service-input").fill("tree removal");

    // Set up a request interceptor BEFORE clicking submit.
    let capturedScoringBody: Record<string, unknown> | null = null;

    const scoringPromise = page.waitForRequest((req: Request) => {
      if (
        req.url().includes("/api/agent/scoring") &&
        req.method() === "POST"
      ) {
        try {
          capturedScoringBody = JSON.parse(req.postData() ?? "{}");
        } catch {
          /* ignore parse errors */
        }
        return true;
      }
      return false;
    });

    await page.getByTestId("submit-btn").click();
    await scoringPromise;

    // -- Step 5: analyze the captured request body ----------------------------
    expect(capturedScoringBody).not.toBeNull();
    test.info().annotations.push({
      type: "scoring-request-body",
      description: JSON.stringify(capturedScoringBody),
    });

    // THE KEY ASSERTIONS: did the structured metadata make it?
    const body = capturedScoringBody!;
    expect(body.city).toBeTruthy();
    expect(body.service).toBe("tree removal");

    // These fields should be populated if autocomplete selection worked correctly.
    // If they're missing, that's the bug.
    const hasState = typeof body.state === "string" && body.state.length > 0;
    const hasDfsCode =
      typeof body.dataforseo_location_code === "number" &&
      (body.dataforseo_location_code as number) > 0;
    const hasPlaceId =
      typeof body.place_id === "string" && (body.place_id as string).length > 0;

    test.info().annotations.push({
      type: "metadata-check",
      description: JSON.stringify({
        hasState,
        state: body.state ?? null,
        hasDfsCode,
        dataforseo_location_code: body.dataforseo_location_code ?? null,
        hasPlaceId,
        place_id: body.place_id ?? null,
      }),
    });

    // After the GET-method fix, the DFS bridge should resolve location codes.
    // If the backend has valid DFS credentials, we expect codes in the response.
    if (withDfsCode.length > 0) {
      expect(
        hasDfsCode,
        "Places API returned suggestions with dataforseo_location_code, " +
          "but the scoring request body is missing it. " +
          "The autocomplete selection is not propagating structured metadata.",
      ).toBe(true);

      expect(
        hasState,
        "Autocomplete selection should propagate the state field.",
      ).toBe(true);
    }

    // When the DFS bridge is healthy, at least one Huntsville suggestion
    // should carry a location code. Log a diagnostic note if not.
    if (withDfsCode.length === 0 && suggestions.length > 0) {
      test.info().annotations.push({
        type: "dfs-bridge-gap",
        description:
          "DFS bridge returned 0 location codes — check if the locations() " +
          "endpoint is reachable and returning data (GET vs POST fix applied?).",
      });
    }

    // -- Step 6: wait for result and capture outcome --------------------------
    const resultOrError = page.locator(
      '[data-testid="result-card"], [data-testid="error-banner"]',
    );
    await expect(resultOrError.first()).toBeVisible({ timeout: 90_000 });

    const errorBanner = page.getByTestId("error-banner");
    if (await errorBanner.isVisible()) {
      const errorText = await errorBanner.textContent();
      test.info().annotations.push({
        type: "scoring-error",
        description: errorText ?? "unknown",
      });

      // If we sent a dfs code and still got an error, that's a different bug.
      if (hasDfsCode) {
        test.fail(
          true,
          `Scoring failed despite valid dataforseo_location_code in request: ${errorText}`,
        );
      }
    } else {
      const score = await page.getByTestId("opportunity-score").textContent();
      test.info().annotations.push({
        type: "scoring-result",
        description: `opportunity_score=${score}`,
      });
    }
  });

  test("typing after autocomplete selection clears structured metadata (regression)", async ({
    page,
  }) => {
    await signIn(page, { expectLandOn: /\/(reports|$)/ });
    await page.goto("/niche-finder");
    await page.waitForLoadState("networkidle");

    const cityInput = page.getByTestId("city-input");
    await expect(cityInput).toBeVisible({ timeout: 10_000 });

    // Select from autocomplete first (use Phoenix which is known to exist).
    await cityInput.click();
    await cityInput.pressSequentially("Phoenix", { delay: 50 });
    const listbox = page.getByRole("listbox", { name: /city suggestions/i });

    let selected = false;
    try {
      await expect(listbox).toBeVisible({ timeout: 15_000 });
      const options = listbox.getByRole("option");
      const count = await options.count();
      if (count > 0 && (await options.first().getAttribute("aria-disabled")) !== "true") {
        await options.first().click();
        await page.waitForTimeout(300);
        selected = true;
      }
    } catch {
      // Listbox didn't appear.
    }

    if (!selected) {
      test.skip(true, "No selectable autocomplete suggestions available.");
      return;
    }

    // Now TYPE an extra character — this goes through handleInputChange which
    // calls onChange(q) WITHOUT a suggestion, clearing state/placeId/dfsCode.
    await cityInput.press("End");
    await cityInput.pressSequentially("x", { delay: 50 });

    await page.getByTestId("service-input").fill("roofing");

    let capturedBody: Record<string, unknown> | null = null;
    const reqPromise = page.waitForRequest((req: Request) => {
      if (req.url().includes("/api/agent/scoring") && req.method() === "POST") {
        try {
          capturedBody = JSON.parse(req.postData() ?? "{}");
        } catch {
          /* */
        }
        return true;
      }
      return false;
    });

    await page.getByTestId("submit-btn").click();
    await reqPromise;

    test.info().annotations.push({
      type: "body-after-extra-typing",
      description: JSON.stringify(capturedBody),
    });

    // After extra typing, the metadata SHOULD be cleared (current behavior).
    // This test documents that behavior as a known risk: any post-selection
    // keystroke in the city input wipes the structured metadata.
    expect(capturedBody).not.toBeNull();
    const hasStateAfterTyping =
      typeof capturedBody!.state === "string" && (capturedBody!.state as string).length > 0;
    const hasDfsAfterTyping =
      typeof capturedBody!.dataforseo_location_code === "number";

    test.info().annotations.push({
      type: "metadata-after-extra-type",
      description: JSON.stringify({
        hasState: hasStateAfterTyping,
        hasDfsCode: hasDfsAfterTyping,
      }),
    });

    // This confirms the "any keystroke after selection clears metadata" behavior.
    // If this assertion fails, it means the bug has been fixed upstream.
    expect(hasStateAfterTyping).toBe(false);
    expect(hasDfsAfterTyping).toBe(false);
  });
});
