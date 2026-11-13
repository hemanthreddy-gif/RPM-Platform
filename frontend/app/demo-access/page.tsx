import type { Metadata } from "next";
import { Icon } from "../../components/icon";

export const metadata: Metadata = { title: "Restricted demo access | RPM Platform", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function DemoAccessPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return <main className="auth-page"><section className="card" style={{ maxWidth: 480, padding: 32 }}>
    <span className="brand"><span className="brand-mark"><Icon name="activity" size={23} /></span>rpm<span className="brand-light">platform</span></span>
    <p className="workspace-kicker" style={{ marginTop: 30 }}>RESTRICTED RESEARCH PREVIEW</p>
    <h1 style={{ fontSize: 30, fontWeight: 650, letterSpacing: "-.04em", marginTop: 10 }}>A space to explore.</h1>
    <p className="muted" style={{ marginTop: 12 }}>Enter the preview password supplied by the demo operator. Then sign in or create a synthetic patient account.</p>
    <form action="/demo-access/login" method="post" className="auth-form"><label>Preview password<input name="password" type="password" autoComplete="current-password" required maxLength={512} /></label><button className="button-dark auth-submit" type="submit">Open the demo <Icon name="arrow" size={18} /></button></form>
    {error && <p role="alert" className="auth-error">Access could not be confirmed. Check the preview password and try again.</p>}
    <p className="auth-disclaimer">Demo with synthetic data. Not for medical use. Use fictional details only. Access expires after eight hours.</p>
  </section></main>;
}
