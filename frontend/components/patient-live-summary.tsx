"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { Alert, Medication, Observation, PatientProfile } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { Icon } from "./icon";

export function PatientLiveSummary() {
  const [profile, setProfile] = useState<PatientProfile>();
  const [readings, setReadings] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      const session = getSession(); if (!session) return;
      setLoading(true);
      void api.me(session.accessToken).then(async (me) => {
        const [nextReadings, nextAlerts, nextMedication] = await Promise.all([
          api.observations(me.id, session.accessToken), api.alerts(session.accessToken), api.medications(me.id, session.accessToken),
        ]);
        if (!cancelled) { setProfile(me); setReadings(nextReadings); setAlerts(nextAlerts); setMedications(nextMedication); setError(""); }
      }).catch(() => { if (!cancelled) setError("Your recent activity could not be refreshed. Please try again."); }).finally(() => { if (!cancelled) setLoading(false); });
    };
    refresh(); window.addEventListener("rpm:observations-changed", refresh);
    return () => { cancelled = true; window.removeEventListener("rpm:observations-changed", refresh); };
  }, []);
  if (loading) return <p aria-live="polite" className="card">Refreshing your recent activity…</p>;
  if (error) return <p role="alert" className="form-error">{error}</p>;
  const latest = readings[0];
  const active = alerts.filter((alert) => alert.status !== "resolved");
  return <>
    <section className="card" aria-labelledby="welcome-heading"><span className="summary-icon mint"><Icon name="activity" size={18} /></span><h2 id="welcome-heading">{profile ? `Welcome, ${profile.display_name}` : "Your latest reading"}</h2>
      {latest ? <><div className="summary-value">{latest.value ?? `${latest.components.systolic}/${latest.components.diastolic}`} <small style={{ fontSize: 13, fontWeight: 500 }}>{latest.unit}</small></div><p className="muted">{latest.type.replaceAll("_", " ")} · {latest.source}<br/><time dateTime={latest.measured_at}>{new Date(latest.measured_at).toLocaleString()}</time></p></> : <p className="muted">Your daily record starts with one check-in. Save a reading above to see it here.</p>}
      <Link className="card-foot-link" href="/patient/trends">Explore your history <Icon name="arrow" size={15} /></Link>
    </section>
    <section className="card" aria-labelledby="alerts-heading"><span className="summary-icon blue"><Icon name="bell" size={18} /></span><h2 id="alerts-heading">Active alerts</h2>
      <div className="summary-value">{active.length}</div><p className="muted">{active.length ? "Recorded alerts awaiting resolution. Open your alerts to read their status and guidance." : "No active server-supplied alerts."}</p>
      {active.slice(0, 1).map((alert) => <p key={alert.id}><strong>{alert.severity}:</strong> {alert.guidance}</p>)}
      <Link className="card-foot-link" href="/patient/alerts">Review alerts <Icon name="arrow" size={15} /></Link>
    </section>
    <section className="card" aria-labelledby="medications-heading"><span className="summary-icon lilac"><Icon name="pill" size={18} /></span><h2 id="medications-heading">Medication records</h2>
      {medications.length ? <ul className="mt-3 space-y-2">{medications.slice(0, 3).map((medication) => <li key={medication.id}><strong>{medication.name}</strong><br/><span className="muted">{medication.frequency}</span></li>)}</ul> : <p className="muted">No current synthetic medication records. Physician-authored records will appear here.</p>}
      <Link className="card-foot-link" href="/patient/medications">View medications <Icon name="arrow" size={15} /></Link>
    </section>
  </>;
}
