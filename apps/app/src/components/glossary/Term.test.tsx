// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import Term from "@/components/glossary/Term";

afterEach(cleanup);

describe("Term", () => {
  it("renders a glossary term with an accessible info button", () => {
    render(<Term termKey="map_pack" />);

    expect(screen.getByText("Map Pack")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /what is map pack/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("opens on keyboard focus and wires aria-describedby to the tooltip", async () => {
    const user = userEvent.setup();
    render(<Term termKey="keyword_difficulty" label="KD" />);

    await user.tab();

    const button = screen.getByRole("button", { name: /what is keyword difficulty \/ kd/i });
    expect(button).toHaveFocus();
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(button).toHaveAttribute("aria-describedby");
    const tooltipId = button.getAttribute("aria-describedby");
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveAttribute("id", tooltipId);
    expect(tooltip).toHaveStyle({ textTransform: "none" });
    expect(tooltip).toHaveTextContent(/how hard it should be to rank/i);
  });

  it("closes the tooltip with Escape", async () => {
    const user = userEvent.setup();
    render(<Term termKey="feasibility" />);

    await user.tab();
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /what is feasibility/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("keeps Escape from bubbling to parent document handlers while open", async () => {
    const user = userEvent.setup();
    const parentEscapeHandler = vi.fn();
    document.addEventListener("keydown", parentEscapeHandler);
    try {
      render(<Term termKey="feasibility" />);

      await user.tab();
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
      parentEscapeHandler.mockClear();

      await user.keyboard("{Escape}");

      expect(parentEscapeHandler).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener("keydown", parentEscapeHandler);
    }
  });

  it("keeps an already-open hover tooltip visible when pinned by click", async () => {
    const user = userEvent.setup();
    render(<Term termKey="lookalike" />);

    const button = screen.getByRole("button", { name: /what is lookalike/i });
    await user.hover(button);
    await waitFor(() => expect(screen.getByRole("tooltip")).toHaveStyle({ opacity: "1" }));

    await user.click(button);

    expect(screen.getByRole("tooltip")).toHaveStyle({ opacity: "1" });
    expect(button).toHaveAttribute("aria-expanded", "true");
  });

  it("uses fallback copy for unknown terms", async () => {
    const user = userEvent.setup();
    render(
      <Term
        termKey="source_confidence"
        label="Source confidence"
        fallbackDefinition="How much evidence supports the current market read."
      />,
    );

    expect(screen.getByText("Source confidence")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /what is source confidence/i }));

    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "How much evidence supports the current market read.",
    );
  });
});
