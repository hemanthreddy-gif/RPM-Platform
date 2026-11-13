import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PatientProfileEditor } from "../components/patient-profile";
import { PatientCareTeam } from "../components/patient-care-team";
import { api } from "../lib/api/client";
import { setSession } from "../lib/auth/session";

const profile = { id: "synthetic-patient", display_name: "Synthetic Patient", timezone: "Asia/Kolkata", has_hypertension: false };
const physician = { id: "synthetic-physician", display_name: "Synthetic Physician", specialty: null };

describe("profile and consent workflows", () => {
  beforeEach(() => setSession({ accessToken: "test", refreshToken: "test", role: "patient", userId: "synthetic", expiresAt: Date.now() + 60_000 }));
  afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); });

  it("keeps edited profile fields when saving fails and permits retry", async () => {
    vi.spyOn(api, "me").mockResolvedValue(profile);
    const update = vi.spyOn(api, "updateProfile").mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ ...profile, display_name: "Synthetic New Name" });
    render(<PatientProfileEditor />);
    const name = await screen.findByLabelText("Full name");
    fireEvent.change(name, { target: { value: "Synthetic New Name" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByRole("alert");
    expect((name as HTMLInputElement).value).toBe("Synthetic New Name");
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(update).toHaveBeenCalledTimes(2));
    expect((await screen.findByRole("status")).textContent).toContain("Profile saved");
  });

  it("requires explicit consent and confirms before revoking access", async () => {
    vi.spyOn(api, "physicians").mockResolvedValue([physician]);
    vi.spyOn(api, "connections").mockResolvedValue([]);
    const connect = vi.spyOn(api, "connectPhysician").mockResolvedValue({ id: "relationship", physician_id: physician.id, display_name: physician.display_name, specialty: null, consent_id: "consent", active: true, started_at: "2026-11-01T00:00:00Z" });
    const disconnect = vi.spyOn(api, "disconnectPhysician").mockResolvedValue(undefined);
    render(<PatientCareTeam />);
    fireEvent.change(await screen.findByLabelText("Choose a physician"), { target: { value: physician.id } });
    const button = screen.getByRole("button", { name: "Connect physician" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(connect).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(button);
    await screen.findByRole("button", { name: "End connection" });
    fireEvent.click(screen.getByRole("button", { name: "End connection" }));
    expect(disconnect).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm end connection" }));
    await waitFor(() => expect(disconnect).toHaveBeenCalledWith("relationship", "test"));
    expect((await screen.findByRole("status")).textContent).toContain("Connection ended");
  });
});
