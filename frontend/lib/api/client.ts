import type { Alert, Device, DevicePairing, MealPhoto, MealPhotoComment, Medication, Message, MessageThread, Observation, ObservationCreate, PatientProfile, PhysicianWorklistItem, TokenResponse } from "./generated";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); }
}

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init: RequestInit = {}, accessToken?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, "The server could not accept the request.");
  return (await response.json().catch(() => undefined)) as T;
}

async function imageRequest(path: string, accessToken: string): Promise<Blob> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store",
  });
  if (!response.ok) throw new Error("Meal photo could not be loaded");
  return response.blob();
}

export const api = {
  register: (email: string, password: string, display_name: string) =>
    request<TokenResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) }),
  login: (email: string, password: string, totp_code?: string) =>
    request<TokenResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password, totp_code }) }),
  refresh: (refresh_token: string) => request<TokenResponse>("/api/v1/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token }) }),
  logout: (refresh_token: string) => request<void>("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }),
  me: (token: string) => request<PatientProfile>("/api/v1/patients/me", {}, token),
  worklist: (token: string, query = "") => request<PhysicianWorklistItem[]>(`/api/v1/physician/patients?query=${encodeURIComponent(query)}`, {}, token),
  patient: (patientId: string, token: string) => request<PatientProfile>(`/api/v1/patients/${patientId}`, {}, token),
  observations: (patientId: string, token: string) => request<Observation[]>(`/api/v1/patients/${patientId}/observations`, {}, token),
  createObservation: (payload: ObservationCreate, idempotencyKey: string, token: string) =>
    request<{ alerts: { guidance: string }[] }>("/api/v1/observations", { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify(payload) }, token),
  alerts: (token: string) => request<Alert[]>("/api/v1/alerts", {}, token),
  medications: (patientId: string, token: string) => request<Medication[]>(`/api/v1/patients/${patientId}/medications`, {}, token),
  reportDose: (doseEventId: string, status: "taken" | "missed" | "skipped", token: string) =>
    request<void>(`/api/v1/dose-events/${doseEventId}/report`, { method: "POST", body: JSON.stringify({ status, reported_at: new Date().toISOString() }) }, token),
  transitionAlert: (id: string, action: "acknowledge" | "resolve", token: string) =>
    request<void>(`/api/v1/alerts/${id}/${action}`, { method: "POST" }, token),
  meals: (patientId: string, token: string) => request<MealPhoto[]>(`/api/v1/patients/${patientId}/meals`, {}, token),
  uploadMeal: async (file: File, eatenAt: string, token: string) => {
    const response = await fetch(`${baseUrl}/api/v1/meals?eaten_at=${encodeURIComponent(eatenAt)}`, {
      method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": file.type },
      body: await file.arrayBuffer(), cache: "no-store",
    });
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Meal photo upload failed");
    return (await response.json()) as MealPhoto;
  },
  mealImage: (mealId: string, token: string) => imageRequest(`/api/v1/meals/${mealId}/image`, token),
  addMealComment: (mealId: string, body: string, token: string) =>
    request<MealPhotoComment>(`/api/v1/meals/${mealId}/comments`, { method: "POST", body: JSON.stringify({ body }) }, token),
  devices: (patientId: string, token: string) => request<Device[]>(`/api/v1/patients/${patientId}/devices`, {}, token),
  pairDevice: (kind: "glucose_meter" | "blood_pressure_monitor", vendor: string, serial: string | undefined, token: string) =>
    request<DevicePairing>("/api/v1/devices", { method: "POST", body: JSON.stringify({ kind, vendor, serial }) }, token),
  createThread: (patientId: string, physicianId: string, token: string) => request<MessageThread>("/api/v1/message-threads", { method: "POST", body: JSON.stringify({ patient_id: patientId, physician_id: physicianId }) }, token),
  messages: (threadId: string, token: string) => request<Message[]>(`/api/v1/message-threads/${threadId}/messages`, {}, token),
  sendMessage: (threadId: string, body: string, kind: "message" | "appointment_request", token: string) => request<Message>(`/api/v1/message-threads/${threadId}/messages`, { method: "POST", body: JSON.stringify({ body, kind }) }, token),
  markThreadRead: (threadId: string, token: string) => request<void>(`/api/v1/message-threads/${threadId}/read`, { method: "POST" }, token),
};
