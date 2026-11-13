"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState, useSyncExternalStore } from "react";
import { replayQueuedObservations } from "../lib/offline/queue";
import { accessTokenExpired, clearSession, getSession, setSession, type AppRole, type AuthSession } from "../lib/auth/session";
import { api } from "../lib/api/client";
import { Icon, type IconName } from "./icon";

const links: Record<AppRole, { href: string; label: string; icon: IconName }[]> = {
  patient: [
    { href: "/patient", label: "Overview", icon: "home" },
    { href: "/patient/log", label: "Log readings & sleep", icon: "plus" },
    { href: "/patient/trends", label: "History & trends", icon: "chart" },
    { href: "/patient/meals", label: "Meal photos", icon: "meal" },
    { href: "/patient/medications", label: "Medications", icon: "pill" },
    { href: "/patient/alerts", label: "Alerts", icon: "bell" },
    { href: "/patient/care-team", label: "Care team", icon: "users" },
    { href: "/patient/profile", label: "My profile", icon: "user" },
    { href: "/patient/settings", label: "Settings & devices", icon: "settings" },
  ],
  physician: [{ href: "/physician", label: "Overview", icon: "home" }, { href: "/physician/directory", label: "Patient directory", icon: "users" }],
  admin: [{ href: "/admin", label: "Administration", icon: "shield" }],
};

const subscribeToHydration = () => () => undefined;
const clientHydrationSnapshot = () => true;
const serverHydrationSnapshot = () => false;

export function AppShell({ role, children }: { role: AppRole; children: ReactNode }) {
  const hydrated = useSyncExternalStore(subscribeToHydration, clientHydrationSnapshot, serverHydrationSnapshot);
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
        if (count) { setSyncNotice((previous) => `Synced ${count} queued reading(s). ${previous}`.trim()); window.dispatchEvent(new Event("rpm:observations-changed")); }
      } catch { setSyncNotice((previous) => `${previous} Some queued readings could not be synced; they remain saved for retry. Alerts may not have been evaluated.`.trim()); }
    };
    void replay(); window.addEventListener("online", replay);
    return () => window.removeEventListener("online", replay);
  }, [role, router, session]);
  if (!hydrated || !session || session.role !== role || accessTokenExpired(session)) return <main className="session-loading" aria-live="polite"><Icon name="shield" size={32} />Checking your session…</main>;
  const currentPage = links[role].find((link) => link.href === pathname)?.label ?? "Patient record";
  return <div className={`workspace workspace-${role}`}>
    <aside className="workspace-sidebar" aria-label="Workspace navigation">
      <a className="skip-link" href="#content">Skip to content</a>
      <Link href={`/${role}`} className="workspace-brand"><span><Icon name="activity" size={23} /></span>rpm<small>platform</small></Link>
      <div className="workspace-role"><span><Icon name={role === "patient" ? "heart" : "shield"} /></span><div><strong>{role === "patient" ? "Personal workspace" : role === "physician" ? "Physician workspace" : "Administration"}</strong><small>Synthetic research demo</small></div></div>
      <p className="sidebar-label">{role === "patient" ? "YOUR HEALTH RECORDS" : "CARE WORKSPACE"}</p>
      <nav aria-label="Primary">{links[role].map((link) => <Link key={link.href} className={pathname === link.href ? "workspace-link active" : "workspace-link"} aria-current={pathname === link.href ? "page" : undefined} href={link.href}><Icon name={link.icon} /><span>{link.label}</span>{pathname === link.href && <i />}</Link>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><Icon name="shield" /><p>Private by design.<br/><span>Shared with your consent.</span></p></div><button onClick={async () => { const current = getSession(); if (current) await api.logout(current.refreshToken, current.accessToken).catch(() => undefined); clearSession(); router.replace("/login"); }}><Icon name="logout" /> Log out</button></div>
    </aside>
    <div className="workspace-content">
      <header className="workspace-topbar"><div className="workspace-breadcrumb"><span>{role === "patient" ? "My workspace" : role === "physician" ? "Care workspace" : "Administration"}</span><span aria-hidden="true">/</span><strong>{currentPage}</strong></div><div><span className="topbar-status"><Icon name="shield" size={15} /> Synthetic demo</span><Link href={role === "patient" ? "/patient/profile" : `/${role}`} className="workspace-avatar" aria-label={role === "patient" ? "My profile" : role === "physician" ? "Dr workspace overview" : "Admin workspace overview"}>{role === "patient" ? <Icon name="user" size={19} /> : role === "physician" ? "Dr" : "A"}</Link></div></header>
      <aside aria-label="Demo safety notice" className="safety-notice"><Icon name="shield" size={15} /><span><strong>Demo with synthetic data. Not for medical use.</strong> <span>This app is not an emergency service and does not provide real-time clinician supervision.</span></span></aside>
      <main id="content" className="workspace-main">{syncNotice && <p role="status" className="workspace-sync">{syncNotice}</p>}{children}</main>
      <footer className="workspace-footer">RPM Platform <span>Educational research prototype · Synthetic data only</span></footer>
    </div>
  </div>;
}
