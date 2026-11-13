"use client";

import { useEffect, useState } from "react";
import { AppShell } from "../../../../components/app-shell";
import { PageHeading } from "../../../../components/page-heading";
import { Icon } from "../../../../components/icon";
import { api } from "../../../../lib/api/client";
import type { Medication } from "../../../../lib/api/generated";
import { getSession } from "../../../../lib/auth/session";

function MedicationRecords() {
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => {
    const session = getSession(); if (!session) return;
    let cancelled = false;
    void api.me(session.accessToken).then((profile) => api.medications(profile.id, session.accessToken)).then((result) => { if (!cancelled) setMedications(result); }).catch(() => { if (!cancelled) setError("Medication records could not be loaded. Please return to this page to try again."); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);
  if (loading) return <p className="card" role="status">Loading your medication records…</p>;
  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!medications.length) return <section className="card empty-state"><Icon name="pill" /><h2>No current medication records</h2><p>Physician-authored synthetic medication records will appear here when available. This app does not generate medication instructions.</p></section>;
  return <div className="record-grid">{medications.map((medication) => <article key={medication.id}><div className="medication-header"><span><Icon name="pill" /></span><div><h2>{medication.name}</h2><p>{medication.frequency}</p></div></div><dl className="medication-facts"><div><dt>Recorded dose</dt><dd>{medication.dose ?? "Not recorded"}</dd></div><div><dt>Timezone</dt><dd>{medication.timezone}</dd></div><div><dt>Schedule</dt><dd>{medication.schedule_times.length ? medication.schedule_times.join(", ") : "Not recorded"}</dd></div><div><dt>Source</dt><dd>Physician-authored demo record</dd></div></dl>{medication.instructions && <p className="medication-instructions"><strong>Recorded instructions</strong><br/>{medication.instructions}</p>}</article>)}</div>;
}
export default function MedicationsPage() { return <AppShell role="patient"><PageHeading eyebrow="PHYSICIAN-AUTHORED RECORDS" title="Medications" description="View the medication details and schedules recorded for your synthetic profile." /><MedicationRecords /><p className="history-chart-note">Medication instructions are authored by a physician. This app does not change doses or generate medication advice. A missing patient report is never treated as a missed dose.</p></AppShell>; }
