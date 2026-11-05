"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { replayQueuedObservations } from "../lib/offline/queue";
import { accessTokenExpired, clearSession, getSession, setSession, type AppRole, type AuthSession } from "../lib/auth/session";
import { api } from "../lib/api/client";

const links: Record<AppRole, { href: string; label: string }[]> = {
  patient: [{ href: "/patient", label: "Home" }, { href: "/patient/log", label: "Log reading" }, { href: "/patient/trends", label: "Trends" }, { href: "/patient/meals", label: "Meal photos" }, { href: "/patient/medications", label: "Medications" }, { href: "/patient/alerts", label: "Alerts" }, { href: "/patient/settings", label: "Settings" }],
  physician: [{ href: "/physician", label: "Overview" }, { href: "/physician/directory", label: "Patient directory" }],
  admin: [{ href: "/admin", label: "Administration" }],
};

export function AppShell({ role, children }: { role: AppRole; children: ReactNode }) {
  const [syncNotice, setSyncNotice] = useState(""); const router = useRouter(); const pathname = usePathname(); const [session, setActiveSession] = useState<AuthSession | null>(() => getSession());
  useEffect(() => {
    if (!session || session.role !== role) { router.replace("/login"); return; }
    if (accessTokenExpired(session)) {
      void api.refresh(session.refreshToken).then((tokens) => {
        const claims = JSON.parse(atob(tokens.access_token.split(".")[1])) as { exp: number };
        const refreshed = { ...session, accessToken: tokens.access_token, refreshToken: tokens.refresh_token, expiresAt: claims.exp * 1000 };
        setSession(refreshed); setActiveSession(refreshed);
      }).catch(() => { clearSession(); router.replace("/login"); });
      return;
    }
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js");
    const replay = async () => {
      if (!session || !navigator.onLine) return;
      try {
        const count = await replayQueuedObservations(session.userId, async (item) => {
          const result = await api.createObservation(item.payload, item.idempotencyKey, session.accessToken);
          const guidance = result.alerts.map((alert) => alert.guidance).join(" ");
          if (guidance) setSyncNotice((previous) => `${previous} ${guidance}`.trim());
          return result;
        });
        if (count) setSyncNotice((previous) => `Synced ${count} queued reading(s). ${previous}`.trim());
      } catch { setSyncNotice((previous) => `${previous} Some queued readings could not be synced; they remain saved for retry. Alerts may not have been evaluated.`.trim()); }
    };
    void replay(); window.addEventListener("online", replay);
    return () => window.removeEventListener("online", replay);
  }, [role, router, session]);
  if (!session || session.role !== role) return <main className="p-6" aria-live="polite">Checking your session…</main>;
  return <div className={`workspace workspace-${role}`}><aside className="workspace-sidebar"><Link href={`/${role}`} className="workspace-brand"><span>✳</span> rpm <small>/ platform</small></Link><div className="workspace-role"><span>{role === "patient" ? "♡" : "✳"}</span><div><strong>{role === "patient" ? "My workspace" : role === "physician" ? "Care workspace" : "Administration"}</strong><small>{role === "patient" ? "Patient" : role === "physician" ? "Physician" : "Admin"}</small></div></div><p className="sidebar-label">WORKSPACE</p><nav aria-label="Primary">{links[role].map((link, index) => <Link key={link.href} className={pathname === link.href ? "workspace-link active" : "workspace-link"} href={link.href}><span>{["⌂", "▦", "↗", "▧", "◷", "◎", "⚙"][index]}</span>{link.label}</Link>)}</nav><div className="sidebar-bottom"><p>Your space, all in one place.</p><button onClick={async () => { const current = getSession(); if (current) await api.logout(current.refreshToken).catch(() => undefined); clearSession(); router.replace("/login"); }}>↪ &nbsp; Log out</button></div></aside><div className="workspace-content"><header className="workspace-topbar"><a className="skip-link" href="#content">Skip to content</a><span>{role === "patient" ? "PATIENT WORKSPACE" : role === "physician" ? "PHYSICIAN WORKSPACE" : "ADMIN WORKSPACE"}</span><div><span className="topbar-status"><i/> Connected workspace</span><span className="workspace-avatar">{role === "patient" ? "P" : role === "physician" ? "Dr" : "A"}</span></div></header><aside aria-label="Demo safety notice" className="safety-notice">Demo with synthetic data. Not for medical use. This app is not an emergency service and does not provide real-time clinician supervision.</aside><main id="content" className="workspace-main">{syncNotice && <p role="status" className="workspace-sync">{syncNotice}</p>}{children}</main></div></div>;
}
