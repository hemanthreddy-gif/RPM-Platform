import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export const DEMO_COOKIE = "__Host-rpm-demo-access";
export const DEMO_SESSION_SECONDS = 8 * 60 * 60;
export const MAX_PROXY_BODY_BYTES = 9 * 1024 * 1024;
export type HostedDemoConfig = { password: string; sessionSecret: string; backendSecret: string };

export function hostedDemoConfig(env: NodeJS.ProcessEnv = process.env): HostedDemoConfig | null {
  if (env.HOSTED_DEMO !== "true") return null;
  if (!env.DEMO_ACCESS_PASSWORD || env.DEMO_ACCESS_PASSWORD.length < 16 ||
      !env.DEMO_SESSION_SECRET || env.DEMO_SESSION_SECRET.length < 32 ||
      !env.BACKEND_GATEWAY_SECRET || env.BACKEND_GATEWAY_SECRET.length < 32) {
    throw new Error("Hosted demo access is not configured");
  }
  return { password: env.DEMO_ACCESS_PASSWORD, sessionSecret: env.DEMO_SESSION_SECRET, backendSecret: env.BACKEND_GATEWAY_SECRET };
}

export function passwordMatches(candidate: string, password: string): boolean {
  if (candidate.length > 512) return false;
  return timingSafeEqual(createHash("sha256").update(candidate).digest(), createHash("sha256").update(password).digest());
}

export function signDemoSession(secret: string, now = Date.now()): string {
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(now / 1000) + DEMO_SESSION_SECONDS, nonce: randomBytes(16).toString("base64url") })).toString("base64url");
  return `${payload}.${createHmac("sha256", secret).update(payload).digest("base64url")}`;
}

export function verifyDemoSession(value: string | undefined, secret: string, now = Date.now()): boolean {
  if (!value || value.length > 512) return false;
  const parts = value.split(".");
  if (parts.length !== 2 || !parts.every((part) => /^[A-Za-z0-9_-]+$/.test(part))) return false;
  const signature = createHmac("sha256", secret).update(parts[0]).digest();
  const actual = Buffer.from(parts[1], "base64url");
  if (signature.length !== actual.length || !timingSafeEqual(signature, actual)) return false;
  try {
    const payload = JSON.parse(Buffer.from(parts[0], "base64url").toString("utf8")) as { exp?: unknown; nonce?: unknown };
    const current = Math.floor(now / 1000);
    return typeof payload.exp === "number" && Number.isInteger(payload.exp) &&
      payload.exp > current && payload.exp <= current + DEMO_SESSION_SECONDS &&
      typeof payload.nonce === "string" && /^[A-Za-z0-9_-]{22}$/.test(payload.nonce);
  } catch { return false; }
}

export function cookieValue(request: Request, name = DEMO_COOKIE): string | undefined {
  const prefix = `${name}=`;
  return request.headers.get("cookie")?.split(";").map((part) => part.trim()).find((part) => part.startsWith(prefix))?.slice(prefix.length);
}

export function normalizedPath(pathname: string): string | null {
  let path = pathname;
  try { for (let step = 0; step < 3 && path.includes("%"); step++) path = decodeURIComponent(path); }
  catch { return null; }
  if (!path.startsWith("/") || path.includes("%") || path.includes("\\") || [...path].some((character) => character.charCodeAt(0) <= 32) || path.includes("//") || path.split("/").some((part) => part === "." || part === "..")) return null;
  return path;
}

export function blockedHostedPath(pathname: string): boolean {
  const path = normalizedPath(pathname);
  if (!path) return true;
  return ["/admin", "/api/v1/admin", "/api/v1/auth/provision", "/api/v1/auth/physician-invitations"]
    .some((blocked) => path === blocked || path.startsWith(`${blocked}/`));
}

export function publicGatewayPath(pathname: string): boolean {
  return ["/health", "/demo-access", "/demo-access/login", "/favicon.ico", "/sw.js", "/manifest.webmanifest"].includes(pathname) || pathname.startsWith("/_next/static/");
}

export function sameOriginRequest(request: Request): boolean {
  if (request.headers.get("sec-fetch-site") === "cross-site") return false;
  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    const parsed = new URL(origin);
    const expectedHost = request.headers.get("host") ?? new URL(request.url).host;
    return parsed.protocol === "https:" && parsed.host === expectedHost && !parsed.username && !parsed.password;
  } catch { return false; }
}

export class BodyLimitError extends Error {}
export async function boundedBody(request: Request, maxBytes = MAX_PROXY_BODY_BYTES): Promise<Uint8Array | undefined> {
  const length = request.headers.get("content-length");
  if (length && (!/^\d+$/.test(length) || Number(length) > maxBytes)) throw new BodyLimitError("Request body too large");
  if (!request.body) return undefined;
  const reader = request.body.getReader(); const chunks: Uint8Array[] = []; let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) { await reader.cancel(); throw new BodyLimitError("Request body too large"); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const body = new Uint8Array(total); let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body;
}

export function backendTarget(requestUrl: string, configuredUrl: string | undefined): URL {
  if (!configuredUrl) throw new Error("Backend is not configured");
  const upstream = new URL(configuredUrl);
  if (!["http:", "https:"].includes(upstream.protocol) || upstream.username || upstream.password || upstream.search || upstream.hash || upstream.pathname !== "/") throw new Error("Invalid backend origin");
  const incoming = new URL(requestUrl);
  const path = normalizedPath(incoming.pathname);
  if (!path?.startsWith("/api/")) throw new Error("Invalid API path");
  return new URL(`${path}${incoming.search}`, upstream.origin);
}

export function gatewayJson(detail: string, status: number): Response {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}

// Per-process throttling supplements the shared preview password. It is deliberately bounded
// and fails closed at capacity; this is not a distributed abuse-control service.
export class DemoLoginLimiter {
  private entries = new Map<string, { count: number; until: number }>();
  private total = { count: 0, until: 0 };
  allow(key: string, now = Date.now()): boolean {
    for (const [entry, bucket] of this.entries) if (bucket.until <= now) this.entries.delete(entry);
    if (this.total.until <= now) this.total = { count: 0, until: now + 300_000 };
    if (++this.total.count > 200) return false;
    const bucket = this.entries.get(key) ?? { count: 0, until: now + 300_000 };
    if (!this.entries.has(key) && this.entries.size >= 1000) return false;
    bucket.count++; this.entries.set(key, bucket);
    return bucket.count <= 10;
  }
}
