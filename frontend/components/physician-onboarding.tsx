"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { onboarding, type PhysicianEnrollment, type PhysicianInvitation } from "../lib/api/onboarding";
import { getSession, setSession } from "../lib/auth/session";

export function PhysicianOnboarding() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [code, setCode] = useState("");
  const [enrollment, setEnrollment] = useState<PhysicianEnrollment | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const secret = enrollment ? new URL(enrollment.provisioning_uri).searchParams.get("secret") : null;

  async function start(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { setEnrollment(await onboarding.start(token.trim(), password)); setPassword(""); setToken(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to start setup."); }
    finally { setBusy(false); }
  }

  async function complete(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!enrollment) return; setBusy(true); setMessage("");
    try {
      const result = await onboarding.complete(enrollment.enrollment_token, code);
      const claims = JSON.parse(atob(result.access_token.split(".")[1])) as { role: string; sub: string; exp: number; mfa: boolean };
      if (claims.role !== "physician" || !claims.mfa) throw new Error("Physician setup was not confirmed. Contact the demo administrator.");
      setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, userId: claims.sub, role: "physician", expiresAt: claims.exp * 1000 });
      setEnrollment(null); setCode(""); router.replace("/physician");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to confirm setup."); }
    finally { setBusy(false); }
  }

  return <div>
    <ol className="onboarding-steps" aria-label="Account setup progress">
      <li aria-current={!enrollment ? "step" : undefined}><span>01</span> Invitation</li>
      <li aria-current={enrollment ? "step" : undefined}><span>02</span> Authenticator</li>
      <li><span>03</span> Your workspace</li>
    </ol>
    {!enrollment ? <form className="auth-form" onSubmit={start}>
      <p className="auth-subtitle">Use the invitation issued by your demo administrator to create your physician account.</p>
      <label htmlFor="physician-invitation">Invitation code</label>
      <input id="physician-invitation" autoComplete="off" required minLength={20} maxLength={256} value={token} onChange={(event) => setToken(event.target.value)} placeholder="Paste your invitation code" />
      <label htmlFor="physician-password">Create a password</label>
      <span className="password-input"><input id="physician-password" type={showPassword ? "text" : "password"} autoComplete="new-password" required minLength={12} maxLength={256} value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby="password-help" /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}>{showPassword ? "Hide" : "Show"}</button></span>
      <p id="password-help" className="field-hint">Use at least 12 characters. Password managers and paste are supported.</p>
      <button className="button-dark auth-submit" type="submit" disabled={busy}>{busy ? "Preparing your account…" : "Continue to secure setup"}<span aria-hidden="true">↗</span></button>
    </form> : <form className="auth-form" onSubmit={complete}>
      <h2 className="text-xl font-semibold">Connect your authenticator</h2>
      <p className="auth-subtitle">Add a time-based account in your authenticator app. Use the setup key below, then enter the current six-digit code. Setup expires in 15 minutes.</p>
      <div className="access-callout">
        <strong>RPM Platform (synthetic demo)</strong>
        <button className="text-link" type="button" onClick={() => setShowSecret(!showSecret)}>{showSecret ? "Hide setup key" : "Show setup key"}</button>
        {showSecret && <><label htmlFor="mfa-setup-key">Authenticator setup key</label><input id="mfa-setup-key" readOnly value={secret ?? ""} autoComplete="off" /><p className="field-hint">Keep this key private. Choose “time based” in your authenticator.</p></>}
      </div>
      <label htmlFor="physician-code">Authenticator code</label>
      <input id="physician-code" inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value)} placeholder="000000" />
      <button className="button-dark auth-submit" type="submit" disabled={busy}>{busy ? "Verifying your code…" : "Verify & open workspace"}<span aria-hidden="true">↗</span></button>
      <p className="field-hint">Your physician access activates only after verification. If setup expires, request a new invitation.</p>
    </form>}
    {message && <p role="alert" className="auth-error">{message}</p>}
    <p className="auth-bottom">Already set up? <Link href="/login?role=physician">Sign in to your workspace</Link></p>
  </div>;
}

export function PhysicianInvitationForm({ trustedOperator = false }: { trustedOperator?: boolean }) {
  const [result, setResult] = useState<PhysicianInvitation | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function invite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); setResult(null); setCopied(false);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const accessToken = getSession()?.accessToken;
      if (!trustedOperator && !accessToken) throw new Error("Sign in as an administrator first.");
      const invitation = await onboarding.invite({
        email: String(data.get("email")), display_name: String(data.get("display_name")),
        registration_no: String(data.get("registration_no")), specialty: String(data.get("specialty")) || undefined,
      }, trustedOperator ? { provisioningKey: String(data.get("provisioning_key")) } : { accessToken });
      setResult(invitation); form.reset();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Invitation could not be created."); }
    finally { setBusy(false); }
  }

  return <section className="invitation-panel">
    <h2 className="text-xl font-semibold">Invite a physician</h2>
    <p className="muted">Create access for a fictional physician in this local demo. This does not verify a medical registration or approve clinical use.</p>
    <form className="auth-form" onSubmit={invite}>
      <label>Physician name<input name="display_name" autoComplete="off" required maxLength={200} placeholder="Dr. Demo Taylor" /></label>
      <label>Physician email<input name="email" type="email" autoComplete="off" required placeholder="physician@example.test" /></label>
      <label>Demo registration number<input name="registration_no" autoComplete="off" required maxLength={100} placeholder="SYNTHETIC-001" /></label>
      <label>Specialty (optional)<input name="specialty" autoComplete="off" maxLength={100} /></label>
      {trustedOperator && <><label>Trusted provisioning key<input name="provisioning_key" type="password" autoComplete="off" required /></label><p className="field-hint">Available only to the operator managing this local installation. The server verifies the key.</p></>}
      <button className="touch-button primary" disabled={busy} type="submit">{busy ? "Creating invitation…" : "Create physician invitation"}</button>
    </form>
    {message && <p role="alert" className="auth-error">{message}</p>}
    {result && <div className="access-callout" role="status"><strong>Invitation ready</strong><p>Share this code privately with the intended physician. It is valid once and expires {new Date(result.expires_at).toLocaleString()}.</p><label>One-time invitation code<input readOnly value={result.invitation_token} autoComplete="off" /></label><button className="touch-button" type="button" onClick={async () => { try { await navigator.clipboard.writeText(result.invitation_token); setCopied(true); } catch { setMessage("Select and copy the invitation code manually."); } }}>{copied ? "Code copied" : "Copy invitation code"}</button><p><Link className="text-link" href="/physician-access">Open physician account setup</Link></p></div>}
  </section>;
}
