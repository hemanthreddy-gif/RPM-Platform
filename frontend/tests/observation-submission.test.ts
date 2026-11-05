import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../lib/api/client";
import { submitObservation } from "../lib/api/observation-submission";
import { clearQueue, listQueuedObservations } from "../lib/offline/queue";

const identity = "synthetic-submission-test";
const payload = { type: "glucose" as const, value: 50, unit: "mg/dL", measured_at: "2026-11-04T00:00:00Z", context: {} };

describe("observation submission", () => {
  beforeEach(async () => { await clearQueue(identity); });
  afterEach(() => vi.restoreAllMocks());

  it("retains the sent key when the network response is lost", async () => {
    const send = vi.spyOn(api, "createObservation").mockRejectedValue(new TypeError("network failure"));
    expect(await submitObservation(identity, "token", payload, false)).toContain("Saved for retry");
    const [item] = await listQueuedObservations(identity);
    expect(item.idempotencyKey).toBe(send.mock.calls[0][1]);
    expect(item.payload).toEqual(payload);
  });

  it("does not queue a server validation rejection", async () => {
    vi.spyOn(api, "createObservation").mockRejectedValue(new ApiError(422, "invalid"));
    expect(await submitObservation(identity, "token", payload, false)).toContain("not accepted");
    expect(await listQueuedObservations(identity)).toHaveLength(0);
  });

  it("shows guidance returned by the server", async () => {
    vi.spyOn(api, "createObservation").mockResolvedValue({ alerts: [{ guidance: "Synthetic server notice" }] });
    expect(await submitObservation(identity, "token", payload, false)).toContain("Synthetic server notice");
  });
});
