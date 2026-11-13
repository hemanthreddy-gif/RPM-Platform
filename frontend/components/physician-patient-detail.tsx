"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { api } from "../lib/api/client";
import type { Alert, Device, Medication, Message, Observation, PatientProfile } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { Icon } from "./icon";

function PhysicianMessages({ patientId }: { patientId: string }) {
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const session = getSession();
  async function open() {
    if (!session) return;
    setBusy(true); setError(""); setNotice(""); setMessages([]); setThreadId("");
    try {
      const physician = await api.physicianMe(session.accessToken);
      const thread = await api.createThread(patientId, physician.id, session.accessToken);
      const items = await api.messages(thread.id, session.accessToken);
      await api.markThreadRead(thread.id, session.accessToken);
      setThreadId(thread.id); setMessages(items);
    } catch { setError("Messages are unavailable. An active patient relationship and monitoring consent are required."); }
    finally { setBusy(false); }
  }
  async function send(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !threadId || !body.trim()) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await api.sendMessage(threadId, body.trim(), "message", session.accessToken);
      setMessages((previous) => [...previous, result]); setBody(""); setNotice("Message sent.");
    } catch { setMessages([]); setThreadId(""); setError("The message could not be sent. Your text is preserved. Reopen the conversation to check current access."); }
    finally { setBusy(false); }
  }
  return <section id="messages" className="card care-messages"><div className="workspace-section-head"><div><p className="workspace-kicker">PATIENT CONVERSATION</p><h2>Messages</h2><p>Non-urgent communication only. Messages are not monitored in real time.</p></div><button className="touch-button" type="button" disabled={busy} onClick={() => void open()}>{busy ? "Loading…" : threadId ? "Refresh messages" : "Open conversation"}</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="success-notice" role="status">{notice}</p>}
    {threadId && <><div className="message-list" aria-label="Patient conversation">{messages.length ? messages.map((message) => <article key={message.id} className={`message-bubble ${message.sender_id === session?.userId ? "message-own" : ""}`}><strong>{message.sender_id === session?.userId ? "You" : "Patient"}</strong><p>{message.body}</p><time dateTime={message.sent_at}>{new Date(message.sent_at).toLocaleString()}</time></article>) : <p className="muted">No messages yet. Start a non-urgent conversation below.</p>}</div><form onSubmit={(event) => void send(event)}><label>Message to patient<textarea rows={3} maxLength={2000} value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write a message using synthetic details…" required /></label><button className="workspace-primary" disabled={busy || !body.trim()} type="submit">{busy ? "Sending…" : "Send message"}</button></form></>}
  </section>;
}

export function PhysicianPatientDetail({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile>();
  const [observations, setObservations] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [photo, setPhoto] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState("");
  const load = useCallback(() => {
    const session = getSession(); if (!session) return;
    void Promise.all([
      api.patient(patientId, session.accessToken), api.observations(patientId, session.accessToken),
      api.alerts(session.accessToken), api.medications(patientId, session.accessToken), api.devices(patientId, session.accessToken),
    ]).then(([nextProfile, nextObservations, nextAlerts, nextMeds, nextDevices]) => {
      setProfile(nextProfile); setObservations(nextObservations); setAlerts(nextAlerts.filter((alert) => alert.patient_id === patientId)); setMedications(nextMeds); setDevices(nextDevices);
    }).catch(() => {
      setProfile(undefined); setObservations([]); setAlerts([]); setMedications([]); setDevices([]);
      setError("This patient record is unavailable. An active relationship and monitoring consent are required.");
    }).finally(() => setLoading(false));
  }, [patientId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const session = getSession(); if (!session || !profile?.has_profile_picture) return;
    let cancelled = false; let imageUrl = "";
    void api.patientPicture(patientId, session.accessToken).then((blob) => {
      if (!cancelled) { imageUrl = URL.createObjectURL(blob); setPhoto(imageUrl); }
    }).catch(() => { if (!cancelled) setPhoto(""); });
    return () => { cancelled = true; if (imageUrl) URL.revokeObjectURL(imageUrl); };
  }, [patientId, profile?.has_profile_picture, profile?.profile_picture_updated_at]);
  async function transition(id: string, action: "acknowledge" | "resolve") {
    const session = getSession(); if (!session) return;
    setTransitioning(id); setMessage(""); setError("");
    try { await api.transitionAlert(id, action, session.accessToken); setMessage(action === "acknowledge" ? "Alert acknowledged." : "Alert resolved."); setLoading(true); load(); }
    catch { setError("The alert status could not be updated. Refresh the record to check your current access."); }
    finally { setTransitioning(""); }
  }
  if (loading) return <p role="status" className="card">Loading the authorized patient record…</p>;
  if (!profile) return <p role="alert" className="form-error">{error || "Patient record unavailable."}</p>;
  const latestSleep = observations.find((observation) => observation.type === "sleep");
  return <>
    {message && <p role="status" className="success-notice">{message}</p>}{error && <p role="alert" className="form-error">{error}</p>}
    <section id="overview" className="card"><div className="workspace-section-head"><div className="record-profile"><span className="person-avatar">{photo && profile.has_profile_picture ? <Image unoptimized src={photo} alt={`Profile of ${profile.display_name}`} width={68} height={68} /> : profile.display_name.slice(0, 1)}</span><div><p className="workspace-kicker">PATIENT PROFILE</p><h2>{profile.display_name}</h2><p>Patient-entered details · {profile.timezone}</p></div></div><button className="touch-button" type="button" onClick={() => { setLoading(true); setError(""); load(); }}>Refresh record</button></div>
      <dl className="detail-facts"><div><dt>Age</dt><dd>{profile.age == null ? "Not provided" : `${profile.age} years`}</dd></div><div><dt>Gender</dt><dd>{profile.gender ? profile.gender.replaceAll("_", " ") : "Not provided"}</dd></div><div><dt>Phone number</dt><dd>{profile.phone || "Not provided"}</dd></div><div><dt>Date of birth</dt><dd>{profile.date_of_birth || "Not provided"}</dd></div><div><dt>Height · self-reported</dt><dd>{profile.height_cm == null ? "Not provided" : `${profile.height_cm} cm`}</dd></div><div><dt>Weight · self-reported</dt><dd>{profile.weight_kg == null ? "Not provided" : `${profile.weight_kg} kg`}</dd></div><div><dt>Latest sleep · self-reported</dt><dd>{latestSleep ? `${latestSleep.value} h` : "No entry"}</dd></div><div><dt>Sleep recorded at</dt><dd>{latestSleep ? new Date(latestSleep.measured_at).toLocaleString() : "No entry"}</dd></div></dl>
    </section>
    <section id="monitoring" className="card"><div className="record-section-heading"><span><Icon name="activity" /></span><div><h2>Readings & sleep</h2><p>Latest recorded observations, with measurement time and authenticated source.</p></div></div>
      {observations.length ? <div className="table-scroll"><table><caption className="sr-only">Recent readings and sleep records with time, value and provenance</caption><thead><tr><th>Measured</th><th>Parameter</th><th>Recorded value</th><th>Source</th><th>Received</th></tr></thead><tbody>{observations.slice(0, 15).map((observation) => <tr key={observation.id}><td>{new Date(observation.measured_at).toLocaleString()}</td><td>{observation.type.replaceAll("_", " ")}</td><td><strong>{observation.value ?? `${observation.components.systolic}/${observation.components.diastolic}`}</strong> {observation.unit}</td><td><span className="source-badge">{observation.source}</span></td><td>{new Date(observation.recorded_at).toLocaleString()}</td></tr>)}</tbody></table></div> : <div className="empty-state"><Icon name="activity" /><h3>No accepted observations yet</h3><p>Readings and sleep entries will appear after this patient records them.</p></div>}
      <p className="history-chart-note">Showing up to 15 of the latest {observations.length} loaded records. Dates use your browser timezone. Sleep is self-reported duration; no clinical target or alert is inferred.</p>
      {devices.length > 0 && <div className="form-section-heading"><h3>Connected devices</h3>{devices.map((device) => <p className="muted" key={device.id}>{device.vendor} · {device.last_sync_at ? `Last sync ${new Date(device.last_sync_at).toLocaleString()}` : "No sync recorded"}</p>)}<p className="history-chart-note">Sync time indicates data receipt, not physician review.</p></div>}
    </section>
    <section id="medications" className="card"><div className="record-section-heading"><span><Icon name="pill" /></span><div><h2>Medications</h2><p>Current physician-authored synthetic records.</p></div></div>{medications.length ? <div className="record-grid">{medications.map((medication) => <article key={medication.id}><div className="medication-header"><span><Icon name="pill" /></span><div><h3>{medication.name}</h3><p>{medication.frequency}</p></div></div><dl className="medication-facts"><div><dt>Recorded dose</dt><dd>{medication.dose || "Not recorded"}</dd></div><div><dt>Schedule</dt><dd>{medication.schedule_times.join(", ") || "Not recorded"}</dd></div></dl>{medication.instructions && <p className="medication-instructions">{medication.instructions}</p>}</article>)}</div> : <p className="muted">No current medication record.</p>}<p className="history-chart-note">Patient dose reports are self-reported. No medication-change advice is generated.</p></section>
    <section id="alerts" className="card"><div className="record-section-heading"><span><Icon name="bell" /></span><div><h2>Alerts</h2><p>Persisted alert status and server-supplied guidance from synthetic demo rules.</p></div></div>{alerts.length ? alerts.map((alert) => <article key={alert.id} className="alert-record"><div className="alert-record-header"><span className={`status-badge ${alert.severity}`}>{alert.severity}</span><strong>{alert.rule_code.replaceAll("_", " ")}</strong><span className="status-badge">{alert.status}</span></div><p>{alert.guidance}</p><p>Created {new Date(alert.created_at).toLocaleString()}</p>{!["acknowledged", "resolved"].includes(alert.status) && <button className="touch-button" disabled={!!transitioning} onClick={() => void transition(alert.id, "acknowledge")}>{transitioning === alert.id ? "Updating…" : "Acknowledge alert"}</button>}{alert.status === "acknowledged" && <button className="touch-button" disabled={!!transitioning} onClick={() => void transition(alert.id, "resolve")}>{transitioning === alert.id ? "Updating…" : "Resolve alert"}</button>}</article>) : <p className="muted">No alerts returned for this authorized patient.</p>}</section>
    <PhysicianMessages patientId={patientId} />
  </>;
}
