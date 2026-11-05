import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ObservationForm } from "../components/observation-form";
import { api } from "../lib/api/client";
import { setSession } from "../lib/auth/session";

describe("synthetic observation form", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear(); });
  it("shows all reading fields without selecting a reading type", () => {
    render(<ObservationForm />);
    expect(screen.getByLabelText("Glucose")).toBeTruthy();
    expect(screen.getByLabelText("Systolic")).toBeTruthy();
    expect(screen.getByLabelText("Diastolic")).toBeTruthy();
    expect(screen.getByLabelText("Heart rate")).toBeTruthy();
    expect(screen.getByLabelText("Oxygen saturation")).toBeTruthy();
    expect(screen.queryByLabelText("Reading type")).toBeNull();
  });
  it("saves all entered parameters and reports individual outcomes", async () => {
    setSession({ accessToken: "test", refreshToken: "test", role: "patient", userId: "synthetic", expiresAt: Date.now() + 60_000 });
    const send = vi.spyOn(api, "createObservation").mockResolvedValue({ alerts: [] });
    render(<ObservationForm />);
    fireEvent.change(screen.getByLabelText("Glucose"), { target: { value: "100" } });
    fireEvent.change(screen.getByLabelText("Systolic"), { target: { value: "120" } });
    fireEvent.change(screen.getByLabelText("Diastolic"), { target: { value: "80" } });
    fireEvent.change(screen.getByLabelText("Heart rate"), { target: { value: "72" } });
    fireEvent.change(screen.getByLabelText("Oxygen saturation"), { target: { value: "98" } });
    fireEvent.click(screen.getByRole("button", { name: "Save readings" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(4));
    expect(send.mock.calls.map((call) => call[0].type)).toEqual(["glucose", "blood_pressure", "heart_rate", "spo2"]);
    expect(new Set(send.mock.calls.map((call) => call[1])).size).toBe(4);
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Oxygen saturation: Reading submitted."));
  });
  it("submits component-only blood pressure in mmHg without invented meal context", async () => {
    setSession({ accessToken: "test", refreshToken: "test", role: "patient", userId: "synthetic", expiresAt: Date.now() + 60_000 });
    const send = vi.spyOn(api, "createObservation").mockResolvedValue({ alerts: [{ guidance: "Synthetic guidance" }] });
    render(<ObservationForm />);
    fireEvent.change(screen.getByLabelText("Systolic"), { target: { value: "120" } });
    fireEvent.change(screen.getByLabelText("Diastolic"), { target: { value: "80" } });
    fireEvent.click(screen.getByRole("button", { name: "Save readings" }));
    await waitFor(() => expect(send).toHaveBeenCalledOnce());
    expect(send.mock.calls[0][0]).toMatchObject({ type: "blood_pressure", unit: "mmHg", components: { systolic: 120, diastolic: 80 }, context: {} });
    expect((await screen.findByRole("status")).textContent).toContain("Synthetic guidance");
  });
});
