// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import StateMultiselect from "./StateMultiselect";

afterEach(() => {
  cleanup();
});

describe("StateMultiselect", () => {
  it("keeps all states selectable when availability is empty", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<StateMultiselect selected={[]} onChange={onChange} availableAbbrs={[]} />);

    await user.click(screen.getByRole("button", { name: "Select states" }));
    await user.click(screen.getByRole("option", { name: "AZ Arizona" }));

    expect(onChange).toHaveBeenCalledWith(["AZ"]);
  });

  it("includes Puerto Rico in the shared picker", async () => {
    const user = userEvent.setup();

    render(<StateMultiselect selected={[]} onChange={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Select states" }));

    expect(screen.getByRole("option", { name: "PR Puerto Rico" })).toBeEnabled();
  });
});
