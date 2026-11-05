import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../app/(auth)/login/page";
import { api } from "../lib/api/client";

const navigate = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: navigate }), useSearchParams: () => new URLSearchParams("role=physician") }));

describe("physician sign in", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); navigate.mockClear(); });
  it("can reveal the password and rejects a patient account in the physician flow", async () => {
    const payload = btoa(JSON.stringify({ role: "patient", sub: "synthetic", exp: 9999999999 }));
    vi.spyOn(api, "login").mockResolvedValue({ access_token: `x.${payload}.x`, refresh_token: "synthetic-refresh", mfa_required: false });
    vi.spyOn(api, "logout").mockResolvedValue(undefined);
    render(<LoginPage />);
    const password = screen.getByLabelText("Password", { exact: true }) as HTMLInputElement;
    expect(password.type).toBe("password"); fireEvent.click(screen.getByRole("button", { name: "Show password" })); expect(password.type).toBe("text");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "synthetic@example.com" } });
    fireEvent.change(password, { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: /Sign in/ }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("patient account"));
    expect(navigate).not.toHaveBeenCalled();
  });
});
