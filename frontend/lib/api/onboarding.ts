import type { TokenResponse } from "./generated";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function onboardingRequest<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const response = await fetch(`${baseUrl}/api/v1/auth${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body), cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : "Setup could not be completed. Check your details and try again.");
  }
  return await response.json() as T;
}

export type PhysicianInvitationInput = { email: string; display_name: string; registration_no: string; specialty?: string };
export type PhysicianInvitation = { invitation_token: string; expires_at: string };
export type PhysicianEnrollment = { enrollment_token: string; provisioning_uri: string; expires_at: string };

export const onboarding = {
  invite: (input: PhysicianInvitationInput, authorization: { accessToken?: string; provisioningKey?: string }) =>
    onboardingRequest<PhysicianInvitation>("/physician-invitations", input,
      authorization.accessToken ? { Authorization: `Bearer ${authorization.accessToken}` } : { "X-Provisioning-Key": authorization.provisioningKey ?? "" }),
  start: (invitation_token: string, password: string) =>
    onboardingRequest<PhysicianEnrollment>("/physician-onboarding/start", { invitation_token, password }),
  complete: (enrollment_token: string, code: string) =>
    onboardingRequest<TokenResponse>("/physician-onboarding/complete", { enrollment_token, code }),
};
