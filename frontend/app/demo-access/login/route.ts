import { NextResponse } from "next/server";
import { BodyLimitError, boundedBody, DEMO_COOKIE, DEMO_SESSION_SECONDS, DemoLoginLimiter, gatewayJson, hostedDemoConfig, passwordMatches, sameOriginRequest, signDemoSession } from "../../../lib/server/demo-gateway";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const limiter = new DemoLoginLimiter();

export async function POST(request: Request) {
  let configuration;
  try { configuration = hostedDemoConfig(); }
  catch { return gatewayJson("Hosted demo access is not configured.", 503); }
  if (!configuration) return gatewayJson("Preview access is only enabled for hosted demos.", 404);
  if (!sameOriginRequest(request)) return gatewayJson("Same-origin access is required.", 403);
  const address = request.headers.get("x-forwarded-for")?.split(",").at(-1)?.trim() ?? "unknown";
  if (!limiter.allow(address)) return gatewayJson("Too many attempts. Please wait five minutes.", 429);
  if (!request.headers.get("content-type")?.startsWith("application/x-www-form-urlencoded")) return gatewayJson("Unsupported form type.", 415);
  let password: string;
  try {
    const raw = await boundedBody(request, 8192);
    password = new URLSearchParams(new TextDecoder().decode(raw)).get("password") ?? "";
  } catch (failure) { return gatewayJson(failure instanceof BodyLimitError ? "Form too large." : "Invalid form.", failure instanceof BodyLimitError ? 413 : 400); }
  if (!passwordMatches(password, configuration.password)) return new NextResponse(null, { status: 303, headers: { Location: "/demo-access?error=1", "Cache-Control": "no-store" } });
  const response = new NextResponse(null, { status: 303, headers: { Location: "/", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" } });
  response.cookies.set(DEMO_COOKIE, signDemoSession(configuration.sessionSecret), {
    httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: DEMO_SESSION_SECONDS,
  });
  return response;
}
