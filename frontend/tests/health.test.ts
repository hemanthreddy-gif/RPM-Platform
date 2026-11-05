import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchBackendHealth } from "../lib/api/health";

describe("server health endpoint", () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

  it("uses the internal address for server-side health while keeping the public URL separate", async () => {
    vi.stubEnv("BACKEND_INTERNAL_URL", "http://backend:8000");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok", ai_provider: "fake" }) });
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchBackendHealth()).resolves.toEqual({ status: "ok", ai_provider: "fake" });
    expect(fetchMock).toHaveBeenCalledWith("http://backend:8000/health", { cache: "no-store" });
  });
});
