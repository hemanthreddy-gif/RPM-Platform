import { ApiError, api } from "./client";
import type { ObservationCreate } from "./generated";
import { enqueueObservation } from "../offline/queue";

/** Retain one idempotency key when the result of an attempted write is uncertain. */
export async function submitObservation(
  identity: string, token: string, payload: ObservationCreate, offline: boolean,
): Promise<string> {
  const key = crypto.randomUUID();
  if (!offline) {
    try {
      const result = await api.createObservation(payload, key, token);
      const guidance = result.alerts.map((alert) => alert.guidance).join(" ");
      return `Reading submitted.${guidance ? ` ${guidance}` : ""}`;
    } catch (error) {
      if (error instanceof ApiError && error.status >= 400 && error.status < 500 && error.status !== 409) {
        return `Reading was not accepted (HTTP ${error.status}). Check the reading and your session.`;
      }
    }
  }
  try {
    const queued = await enqueueObservation(identity, payload, key);
    return `Saved for retry at ${new Date(queued.queuedAt).toLocaleString()}. The server may not have evaluated alerts; this app is not an emergency service.`;
  } catch {
    return "The reading could not be saved for retry. Its server status may be unknown; check your history before submitting again.";
  }
}
