import { describe, expect, it } from "vitest";

import { fetchBackendHealth } from "../lib/api/health";

describe("backend health client", () => {
  it("requests the backend health endpoint", async () => {
    const originalFetch = global.fetch;
    global.fetch = async () => new Response(JSON.stringify({ status: "ok", ai_provider: "fake" }), { status: 200 });

    await expect(fetchBackendHealth()).resolves.toEqual({ status: "ok", ai_provider: "fake" });
    global.fetch = originalFetch;
  });
});
