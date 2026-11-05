import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearQueue, enqueueObservation, listQueuedObservations, replayQueuedObservations } from "../lib/offline/queue";

const payload = { type: "glucose" as const, value: 50, unit: "mg/dL", measured_at: "2026-11-04T00:00:00Z", context: {} };

describe("identity-bound offline observation queue", () => {
  beforeEach(async () => { await clearQueue("synthetic-patient-a"); await clearQueue("synthetic-patient-b"); });

  it("replays each accepted item once with its original idempotency key", async () => {
    const queued = await enqueueObservation("synthetic-patient-a", payload);
    const submit = vi.fn().mockResolvedValue({ id: "server-observation" });
    await expect(replayQueuedObservations("synthetic-patient-a", submit)).resolves.toBe(1);
    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit.mock.calls[0][0].idempotencyKey).toBe(queued.idempotencyKey);
    await expect(listQueuedObservations("synthetic-patient-a")).resolves.toEqual([]);
  });

  it("keeps failed work and never exposes another account's queue", async () => {
    await enqueueObservation("synthetic-patient-a", payload);
    await enqueueObservation("synthetic-patient-b", { ...payload, value: 55 });
    await expect(replayQueuedObservations("synthetic-patient-a", async () => { throw new Error("offline"); })).rejects.toThrow("offline");
    await expect(listQueuedObservations("synthetic-patient-a")).resolves.toHaveLength(1);
    await expect(listQueuedObservations("synthetic-patient-b")).resolves.toHaveLength(1);
  });
});

  it("does not delete readings added during replay", async () => {
    await clearQueue("synthetic-patient-a");
    await enqueueObservation("synthetic-patient-a", payload);
    const submit = vi.fn().mockImplementation(async () => {
      await enqueueObservation("synthetic-patient-a", { ...payload, value: 70 });
    });
    expect(await replayQueuedObservations("synthetic-patient-a", submit)).toBe(1);
    const remaining = await listQueuedObservations("synthetic-patient-a");
    expect(remaining).toHaveLength(1);
    expect(remaining[0].payload.value).toBe(70);
  });
