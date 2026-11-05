"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "../../../lib/api/client";
import { setSession, type AppRole } from "../../../lib/auth/session";

function LoginForm() {
  const router = useRouter(); const params = useSearchParams();
  const [role, setRole] = useState<"patient" | "physician">(params.get("role") === "physician" ? "physician" : "patient");
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false); const [totp, setTotp] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const result = await api.login(email, password, totp || undefined);
      const data = JSON.parse(atob(result.access_token.split(".")[1])) as { role: AppRole; sub: string; exp: number };
      if (role === "physician" && data.role !== "physician") { await api.logout(result.refresh_token).catch(() => undefined); setMessage("These credentials belong to a patient account. Select Patient to sign in."); return; }
      if (role === "patient" && data.role === "physician") { await api.logout(result.refresh_token).catch(() => undefined); setMessage("These credentials belong to a physician account. Select Physician to sign in."); return; }
      setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, role: data.role, userId: data.sub, expiresAt: data.exp * 1000 });
      router.replace(`/${data.role}`);
    } catch { setMessage("Login was not successful. Check your details and MFA code if required."); } finally { setBusy(false); }
  };
  return <main className="auth-layout"><section className="auth-aside"><Link className="brand" href="/"><span className="brand-mark">✳</span><span>rpm<span className="brand-light"> / platform</span></span></Link><div className="auth-aside-content"><p className="eyebrow light">A LITTLE MORE CLARITY</p><h1>Make space for<br/><em>better context.</em></h1><p>One thoughtful place for the information that connects each part of the picture.</p><div className="aside-detail"><span>✳</span><div><strong>Designed for exploration</strong><br/>A synthetic educational demo</div></div></div><p className="aside-bottom">Demo with synthetic data. Not for medical use.</p></section><section className="auth-main"><div className="auth-mobile-brand"><Link className="brand" href="/"><span className="brand-mark">✳</span> rpm / platform</Link></div><div className="auth-content"><Link className="back-link" href="/">← Back to home</Link><p className="eyebrow"><span/> WELCOME BACK</p><h2>Sign in to your<br/><em>workspace.</em></h2><p className="auth-subtitle">Choose your role to get started.</p><div className="role-switch" aria-label="Select workspace"><button type="button" className={role === "patient" ? "selected" : ""} aria-pressed={role === "patient"} onClick={() => setRole("patient")}>♡ &nbsp; Patient</button><button type="button" className={role === "physician" ? "selected" : ""} aria-pressed={role === "physician"} onClick={() => setRole("physician")}>✳ &nbsp; Physician</button></div><form onSubmit={submit} className="auth-form"><label>Email<input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label><div><label htmlFor="login-password">Password</label><span className="password-input"><input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" /><button className="password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><span aria-hidden="true">◉</span> {showPassword ? "Hide" : "Show"}</button></span></div><label>MFA code (if required)<input inputMode="numeric" autoComplete="one-time-code" value={totp} onChange={(e) => setTotp(e.target.value)} placeholder="6-digit code" /></label><p className="field-hint">Physician and admin accounts require an MFA code.</p><button className="button-dark auth-submit" disabled={busy} type="submit">{busy ? "Signing in…" : "Sign in"}<span>↗</span></button><p role="alert" className="auth-error">{message}</p></form><p className="auth-bottom">{role === "patient" ? <>New to the demo? <Link href="/register">Create a patient account ↗</Link></> : <>Need physician access? <Link href="/physician-access">Create physician account ↗</Link></>}</p><p className="auth-disclaimer">Demo with synthetic data. Not for medical use.</p></div></section></main>;
}

export default function LoginPage() { return <Suspense fallback={<main className="auth-page">Loading sign in…</main>}><LoginForm /></Suspense>; }
