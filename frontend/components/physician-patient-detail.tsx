"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { Alert, Device, Medication, Observation, PatientProfile } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

export function PhysicianPatientDetail({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile>(); const [observations, setObservations] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]); const [medications, setMedications] = useState<Medication[]>([]); const [devices, setDevices] = useState<Device[]>([]); const [message, setMessage] = useState("");
  const load = useCallback(() => { const session = getSession(); if (!session) return; void Promise.all([api.patient(patientId, session.accessToken), api.observations(patientId, session.accessToken), api.alerts(session.accessToken), api.medications(patientId, session.accessToken), api.devices(patientId, session.accessToken)]).then(([nextProfile, nextObservations, nextAlerts, nextMeds, nextDevices]) => { setProfile(nextProfile); setObservations(nextObservations); setAlerts(nextAlerts.filter((alert) => alert.patient_id === patientId)); setMedications(nextMeds); setDevices(nextDevices); }).catch(() => setMessage("This patient record is unavailable without an active relationship and monitoring consent.")); }, [patientId]);
  useEffect(() => { load(); }, [load]);
  const transition = (id: string, action: "acknowledge" | "resolve") => { const session = getSession(); if (!session) return; void api.transitionAlert(id, action, session.accessToken).then(() => { setMessage(`Alert ${action}d.`); load(); }).catch(() => setMessage("The alert status could not be updated.")); };
  return <>
    {message && <p role="status" className="card">{message}</p>}
    <section id="overview" className="card"><h2 className="text-xl font-semibold">Overview</h2><p>{profile ? `${profile.display_name} (${profile.timezone})` : "Loading authorized synthetic patient…"}</p><p className="muted">Data age and manual/device provenance are shown with each reading.</p></section>
    <section id="monitoring" className="card"><h2 className="text-xl font-semibold">Monitoring</h2><p className="muted">Device sync age is informational, not a clinical alert or evidence of review.</p>{devices.map((device) => <p key={device.id} role={!device.last_sync_at ? "status" : undefined}>{device.vendor}: {device.last_sync_at ? `last sync ${new Date(device.last_sync_at).toLocaleString()}` : "No device sync recorded — review data age."}</p>)}<div className="table-scroll"><table><caption className="sr-only">Most recent accepted readings</caption><thead><tr><th>Time</th><th>Reading</th><th>Source</th></tr></thead><tbody>{observations.slice(0, 10).map((observation) => <tr key={observation.id}><td>{new Date(observation.measured_at).toLocaleString()}</td><td>{observation.type}: {observation.value ?? `${observation.components.systolic}/${observation.components.diastolic}`} {observation.unit}</td><td>{observation.source}</td></tr>)}</tbody></table></div></section>
    <section id="medications" className="card"><h2 className="text-xl font-semibold">Medications</h2>{medications.length ? <ul>{medications.map((medication) => <li key={medication.id}>{medication.name}: {medication.frequency}</li>)}</ul> : <p>No current medication record.</p>}<p className="muted">Medication status is self-reported. No medication-change advice is generated.</p></section>
    <section id="alerts" className="card"><h2 className="text-xl font-semibold">Alerts</h2>{alerts.length ? alerts.map((alert) => <div key={alert.id} className="mb-3"><p><strong>{alert.severity}</strong> {alert.rule_code.replaceAll("_", " ")} — {alert.status}</p>{!["acknowledged", "resolved"].includes(alert.status) && <button className="touch-button" onClick={() => transition(alert.id, "acknowledge")}>Acknowledge alert</button>} {alert.status === "acknowledged" && <button className="touch-button" onClick={() => transition(alert.id, "resolve")}>Resolve alert</button>}</div>) : <p>No alerts returned for this authorized patient.</p>}</section>
  </>;
}
