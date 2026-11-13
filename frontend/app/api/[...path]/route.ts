import { backendTarget, blockedHostedPath, BodyLimitError, boundedBody, cookieValue, gatewayJson, hostedDemoConfig, sameOriginRequest, verifyDemoSession } from "../../../lib/server/demo-gateway";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const REQUEST_HEADERS = ["authorization", "content-type", "accept", "idempotency-key", "x-request-id"];
const RESPONSE_HEADERS = ["content-type", "content-disposition", "retry-after", "x-request-id"];

async function forward(request: Request): Promise<Response> {
  let configuration;
  try { configuration = hostedDemoConfig(); }
  catch { return gatewayJson("Hosted demo access is not configured.", 503); }
  // Direct route invocation independently enforces the gateway; proxy.ts is not the only check.
  if (configuration) {
    if (blockedHostedPath(new URL(request.url).pathname)) return gatewayJson("This operation is unavailable in the hosted preview.", 403);
    if (!verifyDemoSession(cookieValue(request), configuration.sessionSecret)) return gatewayJson("Demo access required.", 401);
    if (!["GET", "HEAD"].includes(request.method) && !sameOriginRequest(request)) return gatewayJson("Same-origin access is required.", 403);
  }
  let target: URL;
  try { target = backendTarget(request.url, process.env.BACKEND_INTERNAL_URL); }
  catch { return gatewayJson("The requested backend route is unavailable.", 503); }
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) { const value = request.headers.get(name); if (value) headers.set(name, value); }
  if (configuration) headers.set("X-Demo-Gateway-Key", configuration.backendSecret);
  let body: Uint8Array | undefined;
  try { if (!["GET", "HEAD"].includes(request.method)) body = await boundedBody(request); }
  catch (failure) { return gatewayJson(failure instanceof BodyLimitError ? "Request body exceeds the 9 MB limit." : "Invalid request body.", failure instanceof BodyLimitError ? 413 : 400); }
  try {
    const result = await fetch(target, {
      method: request.method, headers, body: body as BodyInit | undefined,
      redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(30_000),
    });
    if (result.status >= 300 && result.status < 400) { await result.body?.cancel(); return gatewayJson("Unexpected backend redirect.", 502); }
    const responseHeaders = new Headers({ "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" });
    for (const name of RESPONSE_HEADERS) { const value = result.headers.get(name); if (value) responseHeaders.set(name, value); }
    return new Response(result.body, { status: result.status, headers: responseHeaders });
  } catch { return gatewayJson("The backend is temporarily unavailable.", 502); }
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE, forward as HEAD, forward as OPTIONS };
