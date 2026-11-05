export type HealthResponse = { status: string; ai_provider: string };

export async function fetchBackendHealth(): Promise<HealthResponse> {
  const baseUrl = process.env.BACKEND_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error("Backend health check failed");
  return (await response.json()) as HealthResponse;
}
