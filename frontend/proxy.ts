import { NextRequest, NextResponse } from "next/server";
import { blockedHostedPath, cookieValue, hostedDemoConfig, publicGatewayPath, verifyDemoSession } from "./lib/server/demo-gateway";

export function proxy(request: NextRequest) {
  if (publicGatewayPath(request.nextUrl.pathname)) return NextResponse.next();
  let configuration;
  try { configuration = hostedDemoConfig(); }
  catch { return NextResponse.json({ detail: "Hosted demo access is not configured." }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
  if (!configuration) return NextResponse.next();
  if (blockedHostedPath(request.nextUrl.pathname)) return NextResponse.json({ detail: "This operation is unavailable in the hosted preview." }, { status: 403, headers: { "Cache-Control": "no-store" } });
  if (!verifyDemoSession(cookieValue(request), configuration.sessionSecret)) {
    if (request.nextUrl.pathname.startsWith("/api/")) return NextResponse.json({ detail: "Demo access required. Open /demo-access to continue." }, { status: 401, headers: { "Cache-Control": "no-store" } });
    // A relative redirect deliberately avoids trusting forwarded host headers.
    return new NextResponse(null, { status: 303, headers: { Location: "/demo-access", "Cache-Control": "no-store" } });
  }
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  return response;
}

export const config = { matcher: ["/:path*"] };
