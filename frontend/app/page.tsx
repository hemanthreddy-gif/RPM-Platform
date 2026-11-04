import { fetchBackendHealth } from "../lib/api/health";

export default async function HomePage() {
  let detail = "Backend health is not available yet.";

  try {
    const health = await fetchBackendHealth();
    detail = `Backend status: ${health.status}. AI provider: ${health.ai_provider}.`;
  } catch {
    // The page must still explain its state if the developer has not started the API.
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <p className="rounded bg-amber-100 p-3 text-sm font-semibold text-amber-950">
        Demo with synthetic data. Not for medical use.
      </p>
      <h1 className="mt-8 text-3xl font-bold">RPM Platform</h1>
      <p className="mt-3 text-slate-700">Educational research prototype foundation.</p>
      <p className="mt-6 rounded border border-slate-300 bg-white p-4" role="status">
        {detail}
      </p>
    </main>
  );
}
