"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "../../../lib/api/client";
import { setSession } from "../../../lib/auth/session";

export default function RegisterPage() {
  const router = useRouter(); const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false); const [displayName, setDisplayName] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const result = await api.register(email, password, displayName);
      const claims = JSON.parse(atob(result.access_token.split(".")[1])) as { role: string; sub: string; exp: number };
      if (claims.role !== "patient") throw new Error("Unexpected account role");
      setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, role: "patient", userId: claims.sub, expiresAt: claims.exp * 1000 }); router.replace("/patient");
    } catch { setMessage("Account could not be created. Check your details or use a different demo email."); } finally { setBusy(false); }
  };
  return <main className="auth-layout"><section className="auth-aside"><Link className="brand" href="/"><span className="brand-mark">✳</span> rpm / platform</Link><div className="auth-aside-content"><p className="eyebrow light">A PLACE TO BEGIN</p><h1>A clearer picture<br/><em>starts here.</em></h1><p>Explore how thoughtful tracking and shared context can come together.</p><div className="aside-detail"><span>✳</span><div><strong>For the demo, use fictional details.</strong><br/>Please don’t enter real health information.</div></div></div><p className="aside-bottom">Demo with synthetic data. Not for medical use.</p></section><section className="auth-main"><div className="auth-mobile-brand"><Link className="brand" href="/"><span className="brand-mark">✳</span> rpm / platform</Link></div><div className="auth-content"><Link className="back-link" href="/">← Back to home</Link><p className="eyebrow"><span/> PATIENT WORKSPACE</p><h2>Create your<br/><em>demo account.</em></h2><p className="auth-subtitle">Use fictional details to explore the patient experience.</p><form onSubmit={submit} className="auth-form"><label>Fictional display name<input required maxLength={200} value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="e.g. Alex Demo" /></label><label>Demo email<input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><div><label htmlFor="register-password">Password (at least 12 characters)</label><span className="password-input"><input id="register-password" required type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={12} maxLength={256} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Create a password" /><button className="password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><span aria-hidden="true">◉</span> {showPassword ? "Hide" : "Show"}</button></span></div><button className="button-dark auth-submit" disabled={busy} type="submit">{busy ? "Creating account…" : "Create patient account"}<span>↗</span></button><p role="alert" className="auth-error">{message}</p></form><p className="auth-bottom">Already have an account? <Link href="/login">Sign in ↗</Link></p><p className="field-hint">Physician accounts are provisioned separately. <Link className="text-link" href="/physician-access">See access information</Link>.</p><p className="auth-disclaimer">Demo with synthetic data. Not for medical use.</p></div></section></main>;
}
