"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { api, ApiError } from "../lib/api/client";
import type { PatientProfile, ProfileUpdate } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

export function PatientProfileEditor() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [photo, setPhoto] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const session = getSession(); if (!session) return;
    let cancelled = false; let imageUrl = "";
    void api.me(session.accessToken).then(async (result) => {
      if (cancelled) return;
      setProfile(result);
      if (result.has_profile_picture) {
        try {
          const blob = await api.patientPicture(result.id, session.accessToken);
          if (cancelled) return;
          imageUrl = URL.createObjectURL(blob); setPhoto(imageUrl);
        } catch { if (!cancelled) setError("Your profile loaded, but the photo could not be loaded."); }
      }
    }).catch(() => { if (!cancelled) setError("Your profile could not be loaded. Please try again."); });
    return () => { cancelled = true; if (imageUrl) URL.revokeObjectURL(imageUrl); };
  }, [revision]);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const session = getSession(); if (!session || !profile) return;
    const form = new FormData(event.currentTarget);
    const numberOrNull = (name: string) => form.get(name) ? Number(form.get(name)) : null;
    const payload: ProfileUpdate = {
      display_name: String(form.get("display_name")).trim(), date_of_birth: String(form.get("date_of_birth")) || null,
      gender: String(form.get("gender")) || null, phone: String(form.get("phone")).trim() || null,
      height_cm: numberOrNull("height_cm"), weight_kg: numberOrNull("weight_kg"),
      timezone: String(form.get("timezone")).trim(), has_hypertension: profile.has_hypertension,
    };
    setBusy(true); setError(""); setNotice("");
    try { setProfile(await api.updateProfile(payload, session.accessToken)); setNotice("Profile saved. Connected physicians can see your updated details."); }
    catch (failure) { setError(failure instanceof ApiError && failure.status === 422 ? "Check your details, including date of birth, phone number and timezone, then try again." : "Profile could not be saved. Your changes are still here; please try again."); }
    finally { setBusy(false); }
  }

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; const session = getSession(); if (!file || !session) return;
    setError(""); setNotice("");
    if (!["image/jpeg", "image/png"].includes(file.type) || file.size > 2 * 1024 * 1024) {
      setError("Choose a JPEG or PNG image smaller than 2 MB."); event.target.value = ""; return;
    }
    setBusy(true);
    try { await api.uploadProfilePicture(file, session.accessToken); setRevision((value) => value + 1); setNotice("Profile photo saved privately."); }
    catch { setError("The photo could not be saved. Choose a valid JPEG or PNG smaller than 2 MB and retry."); }
    finally { setBusy(false); event.target.value = ""; }
  }

  return <>
    <div className="patient-heading"><div><p className="workspace-kicker">YOUR DETAILS</p><h1>Personal profile</h1><p>A familiar face and the essentials, all in one place.</p></div><Link className="workspace-secondary" href="/patient/care-team">Manage your care team →</Link></div>
    {error && <div role="alert" className="form-error">{error} {!profile && <button type="button" onClick={() => { setError(""); setRevision((value) => value + 1); }}>Try again</button>}</div>}
    {notice && <p role="status" className="success-notice">{notice}</p>}
    {!profile ? (!error && <p role="status">Loading your profile…</p>) : <div className="profile-layout">
      <aside className="card profile-summary" aria-label="Profile summary"><div className="profile-photo">{photo ? <Image src={photo} alt="Your profile" width={112} height={112} unoptimized /> : <span aria-hidden="true">{profile.display_name.slice(0, 1).toUpperCase()}</span>}</div><h2>{profile.display_name}</h2><p className="muted">{profile.age == null ? "Add your personal details below" : `${profile.age} years old`}</p><label className="photo-upload-label">Change profile photo<input aria-label="Profile photo" type="file" accept="image/png,image/jpeg" disabled={busy} onChange={(event) => void upload(event)} /></label><p className="field-hint">JPEG or PNG · up to 2 MB.<br/>Use a fictional image for this demo.</p><div className="profile-privacy"><strong>Shared with your permission</strong><p>Your profile and photo are private. Only physicians you connect with can view them while your monitoring consent is active.</p></div></aside>
      <form className="card profile-form" onSubmit={(event) => void save(event)}><fieldset disabled={busy}><legend>Personal information</legend><p className="muted">Use fictional details only. Optional fields can be left empty.</p><div className="form-grid">
        <label className="form-span">Full name<input name="display_name" required maxLength={100} defaultValue={profile.display_name} autoComplete="name" /></label>
        <label>Date of birth<input name="date_of_birth" type="date" min="1900-01-01" max={new Date().toLocaleDateString("en-CA")} defaultValue={profile.date_of_birth ?? ""} /><span className="field-hint">Your age is calculated from this date.</span></label>
        <label>Gender<select aria-label="Gender" name="gender" defaultValue={profile.gender ?? ""}><option value="">Prefer not to say</option><option value="female">Female</option><option value="male">Male</option><option value="non_binary">Non-binary</option><option value="other">Self-described / other</option></select></label>
        <label>Phone number<input name="phone" type="tel" autoComplete="tel" maxLength={24} placeholder="Fictional contact number" defaultValue={profile.phone ?? ""} /></label>
        <label>Timezone<input name="timezone" required list="profile-timezones" defaultValue={profile.timezone} /><datalist id="profile-timezones"><option value="Asia/Kolkata"/><option value="UTC"/><option value="Europe/London"/><option value="America/New_York"/><option value="America/Los_Angeles"/></datalist><span className="field-hint">For example, Asia/Kolkata or UTC.</span></label>
      </div><div className="form-section-heading"><h2>Body measurements</h2><p className="muted">Self-reported profile details. No health score or diagnosis is calculated.</p></div><div className="form-grid"><label>Height (cm)<input name="height_cm" type="number" min="1" max="300" step="0.1" placeholder="e.g. 170" defaultValue={profile.height_cm ?? ""} /></label><label>Weight (kg)<input name="weight_kg" type="number" min="1" max="700" step="0.1" placeholder="e.g. 70" defaultValue={profile.weight_kg ?? ""} /></label></div>
      <div className="form-actions"><button className="workspace-primary" type="submit">{busy ? "Saving…" : "Save profile"}</button><span className="field-hint">You can update these details anytime.</span></div></fieldset></form>
    </div>}
  </>;
}
