// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PasswordResetForm from "./PasswordResetForm";
import { createClient } from "@/lib/supabase/client";

const mocks = vi.hoisted(() => ({
  updateUser: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

beforeEach(() => {
  mocks.updateUser.mockResolvedValue({ error: null });
  vi.mocked(createClient).mockReturnValue({
    auth: {
      updateUser: mocks.updateUser,
    },
  } as never);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PasswordResetForm", () => {
  it("updates the password when both fields are valid and matching", async () => {
    render(<PasswordResetForm />);

    fireEvent.change(screen.getByLabelText(/new password/i), {
      target: { value: "CorrectHorse1" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "CorrectHorse1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(mocks.updateUser).toHaveBeenCalledWith({ password: "CorrectHorse1" });
    });
    expect(screen.getByRole("status")).toHaveTextContent("Password updated.");
  });
});
