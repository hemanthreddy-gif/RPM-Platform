"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { Alert, Medication, Observation, PatientProfile } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

function age(value?: string): string {
  if (!value) return "No accepted reading yet";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  return minutes < 60 ? `${minutes} minutes ago` : `${Math.floor(minutes / 60)} hours ago`;
}

export function PatientLiveSummary() {
  const [profile, setProfile] = useState<PatientProfile>(); const [readings, setReadings] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]); const [medications, setMedications] = useState<Medication[]>([]); const [error, setError] = useState("");
  useEffect(() => {
    const session = getSession(); if (!session) return;
    void api.me(session.accessToken).then(async (me) => {
      setProfile(me);
      const [nextReadings, nextAlerts, nextMedication] = await Promise.all([
        api.observations(me.id, session.accessToken), api.alerts(session.accessToken), api.medications(me.id, session.accessToken),
      ]);
      setReadings(nextReadings); setAlerts(nextAlerts); setMedications(nextMedication);
    }).catch(() => setError("Live synthetic-demo data could not be refreshed. Check your connection and sign in again."));
  }, []);
  const latest = readings[0]; const active = alerts.filter((alert) => !["acknowledged", "resolved"].includes(alert.status));
  return <>
    {error && <p role="alert" className="card">{error}</p>}
    <section className="card" aria-labelledby="welcome-heading"><h2 id="welcome-heading" className="text-xl font-semibold">{profile ? `Welcome, ${profile.display_name}` : "Loading your secure summary…"}</h2>
      <p className="muted">Data source: secure server refresh. Reading age: {age(latest?.measured_at)}.</p>
      {latest && <p><strong>Latest reading:</strong> {latest.type.replace("_", " ")} — {latest.value ?? `${latest.components.systolic}/${latest.components.diastolic}`} {latest.unit} ({latest.source}).</p>}
    </section>
    <section className="card" aria-labelledby="alerts-heading"><h2 id="alerts-heading" className="text-xl font-semibold">Active alerts</h2>
      {active.length ? <ul>{active.map((alert) => <li key={alert.id}><strong>{alert.severity}</strong>: {alert.guidance} ({alert.status})</li>)}</ul> : <p className="muted">No active server-supplied alerts.</p>}
      <p className="muted">This is not an emergency service. Do not wait for this app in an emergency.</p>
    </section>
    <section className="card" aria-labelledby="medications-heading"><h2 id="medications-heading" className="text-xl font-semibold">Today’s medications</h2>
      {medications.length ? <ul>{medications.map((medication) => <li key={medication.id}>{medication.name} — {medication.frequency}</li>)}</ul> : <p className="muted">No current synthetic medication record is available.</p>}
      <p className="muted">Medication reports are self-reported. A missing report is not treated as a missed dose.</p>
    </section>
  </>;
}
