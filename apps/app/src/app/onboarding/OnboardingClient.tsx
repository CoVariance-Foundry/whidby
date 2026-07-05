"use client";

import { useCallback, useEffect, useState } from "react";
import ServicePicker, {
  type OnboardingServiceChoice,
} from "@/components/onboarding/ServicePicker";
import TargetPicker, {
  type OnboardingTargetChoice,
} from "@/components/onboarding/TargetPicker";
import OnboardingSummary from "@/components/onboarding/OnboardingSummary";
import type {
  CoachOrAgency,
  OnboardingFocus,
  OnboardingIntent,
  OnboardingStrategyRouting,
} from "@/lib/onboarding/types";

type Step = "welcome" | "service" | "target" | "confirm";

type ProfileResponse = {
  status?: string;
  profile?: {
    recommended_strategy_id?: OnboardingStrategyRouting["starter"];
    available_strategy_ids?: OnboardingStrategyRouting["available"];
    next_route?: OnboardingStrategyRouting["next_route"];
  } | null;
  routing?: OnboardingStrategyRouting;
  target?: {
    niche_keyword?: string | null;
    service_category_id?: string | null;
    geo_scope?: OnboardingTargetChoice["geo_scope"];
    city?: string | null;
    state?: string | null;
    cbsa_code?: string | null;
    place_id?: string | null;
    dataforseo_location_code?: number | null;
    resolved_label?: string | null;
    metadata_source?: OnboardingTargetChoice["metadata_source"] | null;
  } | null;
  message?: string;
};

const DEFAULT_ROUTING: OnboardingStrategyRouting = {
  starter: "easy_win",
  available: ["easy_win", "gbp_blitz", "keyword_hijack"],
  rationale: "Start with one city and one service so the first report is concrete.",
  next_route: "/",
};

type ProfileChoice = {
  intent: OnboardingIntent;
  focus: OnboardingFocus;
  coach_or_agency?: CoachOrAgency;
  label: string;
  description: string;
};

const PROFILE_CHOICES: ProfileChoice[] = [
  {
    intent: "find_first",
    focus: "niche",
    label: "First niche",
    description: "Find one service and one city to start.",
  },
  {
    intent: "scale",
    focus: "replicate",
    label: "Scale repeatable",
    description: "Compare repeatable plays across markets.",
  },
  {
    intent: "coach_agency",
    focus: "agency",
    coach_or_agency: "agency",
    label: "Agency pipeline",
    description: "Source opportunities for clients or operators.",
  },
  {
    intent: "researching",
    focus: "process",
    label: "Research only",
    description: "Browse cached opportunities before committing.",
  },
];

async function readProfileJson(res: Response): Promise<ProfileResponse> {
  try {
    return (await res.json()) as ProfileResponse;
  } catch {
    return {};
  }
}

export default function OnboardingClient() {
  const [step, setStep] = useState<Step>("welcome");
  const [routing, setRouting] = useState<OnboardingStrategyRouting | null>(null);
  const [service, setService] = useState<OnboardingServiceChoice | null>(null);
  const [target, setTarget] = useState<OnboardingTargetChoice | null>(null);
  const [profileChoice, setProfileChoice] = useState<ProfileChoice>(PROFILE_CHOICES[0]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function loadProfile() {
      try {
        const res = await fetch("/api/onboarding/profile", { method: "GET" });
        const json = await readProfileJson(res);
        if (!alive) return;

        if (!res.ok) {
          setError(json.message ?? "Onboarding profile could not be loaded.");
          return;
        }

        if (json.status === "success" && json.profile) {
          setRouting({
            starter: json.profile.recommended_strategy_id ?? DEFAULT_ROUTING.starter,
            available: json.profile.available_strategy_ids ?? DEFAULT_ROUTING.available,
            rationale: DEFAULT_ROUTING.rationale,
            next_route: json.profile.next_route ?? DEFAULT_ROUTING.next_route,
          });
        }

        if (json.target?.niche_keyword) {
          setService({
            id: json.target.service_category_id ?? null,
            label: json.target.niche_keyword,
            is_custom: !json.target.service_category_id,
          });
          setTarget({
            geo_scope: json.target.geo_scope ?? "city",
            city: json.target.city ?? undefined,
            state: json.target.state ?? undefined,
            cbsa_code: json.target.cbsa_code ?? undefined,
            place_id: json.target.place_id ?? undefined,
            dataforseo_location_code: json.target.dataforseo_location_code ?? undefined,
            resolved_label:
              json.target.resolved_label ??
              json.target.city ??
              json.target.state ??
              "Nationwide",
            metadata_source: json.target.metadata_source ?? "typed",
          });
          setStep("confirm");
        }
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadProfile();
    return () => {
      alive = false;
    };
  }, []);

  const ensureProfile = useCallback(async () => {
    if (routing) return routing;

    const res = await fetch("/api/onboarding/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intent: profileChoice.intent,
        focus: profileChoice.focus,
        ...(profileChoice.coach_or_agency
          ? { coach_or_agency: profileChoice.coach_or_agency }
          : {}),
      }),
    });
    const json = await readProfileJson(res);

    if (!res.ok || json.status !== "success" || !json.routing) {
      throw new Error(json.message ?? "Onboarding profile could not be saved.");
    }

    setRouting(json.routing);
    return json.routing;
  }, [profileChoice, routing]);

  const startFlow = async () => {
    setError(null);
    try {
      await ensureProfile();
      setStep("service");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Onboarding could not start.");
    }
  };

  return (
    <div className="app">
      <main
        style={{
          width: "100%",
          minHeight: "100vh",
          display: "grid",
          placeItems: "start center",
          padding: "48px 20px",
        }}
      >
        <div
          style={{
            width: "min(760px, 100%)",
            borderTop: "1px solid var(--rule)",
            paddingTop: 22,
          }}
        >
          <header
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16,
              marginBottom: 28,
            }}
          >
            <div className="navbar-brand">
              <span className="navbar-mark">W</span>
              Widby
            </div>
            <div
              aria-label={`Current onboarding step: ${step}`}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "var(--ink-3)",
                textTransform: "uppercase",
              }}
            >
              {step}
            </div>
          </header>

          {loading ? (
            <div role="status" className="page-sub">
              Loading onboarding...
            </div>
          ) : (
            <div
              style={{
                background: "var(--paper)",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: "28px",
              }}
            >
              {error && (
                <div
                  role="alert"
                  style={{
                    marginBottom: 18,
                    padding: "11px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--danger)",
                    background: "var(--danger-soft)",
                    color: "var(--danger)",
                    fontSize: 13,
                  }}
                >
                  {error}
                </div>
              )}

              {step === "welcome" && (
                <section aria-labelledby="welcome-heading">
                  <p className="field-label">Step 1 of 4</p>
                  <h1 id="welcome-heading" className="page-h1" style={{ margin: 0 }}>
                    Let&apos;s choose your first market.
                  </h1>
                  <p className="page-sub">
                    We will capture one service and one geography, then hand the
                    report to the same entitlement checks used by the scoring app.
                  </p>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                      gap: 10,
                      marginTop: 24,
                    }}
                  >
                    {PROFILE_CHOICES.map((choice) => (
                      <label
                        key={`${choice.intent}-${choice.focus}`}
                        style={{
                          minHeight: 112,
                          padding: 12,
                          borderRadius: 8,
                          border:
                            profileChoice === choice
                              ? "1px solid var(--accent)"
                              : "1px solid var(--rule)",
                          background:
                            profileChoice === choice
                              ? "var(--accent-soft)"
                              : "var(--card)",
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="radio"
                          name="onboarding-intent"
                          checked={profileChoice === choice}
                          onChange={() => setProfileChoice(choice)}
                          style={{ margin: 0 }}
                        />
                        <div
                          style={{
                            fontFamily: "var(--serif)",
                            fontSize: 17,
                            marginTop: 10,
                          }}
                        >
                          {choice.label}
                        </div>
                        <div className="page-sub" style={{ marginTop: 4, fontSize: 13 }}>
                          {choice.description}
                        </div>
                      </label>
                    ))}
                  </div>

                  <button
                    type="button"
                    className="btn-primary"
                    onClick={startFlow}
                    style={{ marginTop: 24 }}
                  >
                    Start onboarding
                  </button>
                </section>
              )}

              {step === "service" && (
                <ServicePicker
                  value={service}
                  onBack={() => setStep("welcome")}
                  onSelect={(nextService) => {
                    setService(nextService);
                    setStep("target");
                  }}
                />
              )}

              {step === "target" && service && (
                <TargetPicker
                  serviceLabel={service.label}
                  value={target}
                  onBack={() => setStep("service")}
                  onSelect={(nextTarget) => {
                    setTarget(nextTarget);
                    setStep("confirm");
                  }}
                />
              )}

              {step === "confirm" && service && target && (
                <OnboardingSummary
                  service={service}
                  target={target}
                  routing={routing}
                  ensureProfile={ensureProfile}
                  onBack={() => setStep("target")}
                />
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
