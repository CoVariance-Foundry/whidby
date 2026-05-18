// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PasswordResetForm from "./PasswordResetForm";
import { createClient } from "@/lib/supabase/client";

const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
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

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mocks.routerPush,
  }),
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
  it("updates the password and redirects back to account settings", async () => {
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
    expect(mocks.routerPush).toHaveBeenCalledWith("/settings?password=updated");
  });
});
