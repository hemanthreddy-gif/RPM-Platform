"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { Message, PatientConnection, Physician } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

export function PatientCareTeam() {
  const [physicians, setPhysicians] = useState<Physician[]>([]);
  const [connections, setConnections] = useState<PatientConnection[]>([]);
  const [selected, setSelected] = useState(""); const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0); const [disconnecting, setDisconnecting] = useState("");
  const [thread, setThread] = useState<{ id: string; physicianId: string; name: string } | null>(null);
  const [messages, setMessages] = useState<Message[]>([]); const [body, setBody] = useState("");
  const session = getSession();

  useEffect(() => {
    const current = getSession(); if (!current) return;
    let cancelled = false;
    void Promise.all([api.physicians(current.accessToken), api.connections(current.accessToken)]).then(([directory, related]) => {
      if (!cancelled) { setPhysicians(directory); setConnections(related); setLoading(false); }
    }).catch(() => { if (!cancelled) { setError("Your care team could not be loaded. Please try again."); setLoading(false); } });
    return () => { cancelled = true; };
  }, [revision]);

  async function connect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !selected || !consent) return;
    setBusy(true); setError(""); setNotice("");
    try { const connection = await api.connectPhysician(selected, session.accessToken); setConnections((previous) => [...previous.filter((item) => item.id !== connection.id), connection]); setSelected(""); setConsent(false); setNotice("Physician connected. Your monitoring consent is active."); }
    catch { setError("The connection could not be created. Please try again."); }
    finally { setBusy(false); }
  }

  async function disconnect(connection: PatientConnection) {
    if (!session) return; setBusy(true); setError(""); setNotice("");
    try {
      await api.disconnectPhysician(connection.id, session.accessToken);
      setConnections((previous) => previous.map((item) => item.id === connection.id ? { ...item, active: false } : item));
      if (thread?.physicianId === connection.physician_id) { setThread(null); setMessages([]); setBody(""); }
      setDisconnecting(""); setNotice("Connection ended. This physician no longer has monitoring access through this connection.");
    } catch { setError("The connection could not be ended. Please try again."); }
    finally { setBusy(false); }
  }

  async function openMessages(connection: PatientConnection) {
    if (!session) return; setBusy(true); setError(""); setNotice(""); setMessages([]); setThread(null); setBody("");
    try {
      const profile = await api.me(session.accessToken);
      const result = await api.createThread(profile.id, connection.physician_id, session.accessToken);
      const items = await api.messages(result.id, session.accessToken);
      await api.markThreadRead(result.id, session.accessToken);
      setThread({ id: result.id, physicianId: connection.physician_id, name: connection.display_name }); setMessages(items);
    } catch { setError("Messages could not be opened. Active monitoring consent is required."); }
    finally { setBusy(false); }
  }

  async function send(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !thread || !body.trim()) return;
    setBusy(true); setError(""); setNotice("");
    try { const message = await api.sendMessage(thread.id, body.trim(), "message", session.accessToken); setMessages((previous) => [...previous, message]); setBody(""); setNotice("Message sent. This is not a real-time or emergency channel."); }
    catch { setError("The message could not be sent. Your text is still here; please try again."); }
    finally { setBusy(false); }
  }

  const active = connections.filter((connection) => connection.active);
  const available = physicians.filter((physician) => !active.some((connection) => connection.physician_id === physician.id));
  return <>
    <div className="patient-heading"><div><p className="workspace-kicker">CONNECTED, WITH YOUR CONSENT</p><h1>Your care team</h1><p>Choose who can see your monitoring information. Stay in control of your access settings.</p></div><span className="count-badge">{active.length} active connection{active.length === 1 ? "" : "s"}</span></div>
    {error && <p role="alert" className="form-error">{error} <button type="button" onClick={() => { setError(""); setRevision((value) => value + 1); }}>Refresh care team</button></p>}
    {notice && <p role="status" className="success-notice">{notice}</p>}
    {loading ? <p role="status">Loading your care team…</p> : <div className="care-team-layout"><section className="card"><p className="workspace-kicker">MY CONNECTIONS</p><h2>Physicians in your team</h2>{!active.length && <div className="empty-state"><span aria-hidden="true">＋</span><h3>Start with a connection</h3><p>Connect with a provisioned physician to share your readings, sleep entries, profile and meal photos.</p></div>}<div className="connection-list">{active.map((connection) => <article className="connection-card" key={connection.id}><div className="connection-header"><span className="person-avatar" aria-hidden="true">{connection.display_name.slice(0, 1)}</span><div><h3>{connection.display_name}</h3><p className="muted">{connection.specialty || "Physician"}</p></div><span className="consent-badge">Consent active</span></div><p className="field-hint">Connected {new Date(connection.started_at).toLocaleDateString()}</p><div className="connection-actions"><button className="workspace-secondary" disabled={busy} type="button" onClick={() => void openMessages(connection)}>Open messages</button><button className="text-button" disabled={busy} type="button" onClick={() => setDisconnecting(connection.id)}>End connection</button></div>{disconnecting === connection.id && <div className="confirm-panel"><p>End access for {connection.display_name}? Your saved records remain in your account. This physician will lose access through this connection.</p><button type="button" disabled={busy} onClick={() => void disconnect(connection)}>Confirm end connection</button><button type="button" disabled={busy} onClick={() => setDisconnecting("")}>Keep connection</button></div>}</article>)}</div></section>
      <section className="card connect-form"><p className="workspace-kicker">ADD TO YOUR TEAM</p><h2>Connect a physician</h2><p className="muted">Only physicians who have completed secure account setup appear here.</p>{available.length ? <form onSubmit={(event) => void connect(event)}><fieldset disabled={busy}><label>Choose a physician<select aria-label="Choose a physician" value={selected} onChange={(event) => setSelected(event.target.value)} required><option value="">Select a physician</option>{available.map((physician) => <option key={physician.id} value={physician.id}>{physician.display_name}{physician.specialty ? ` · ${physician.specialty}` : ""}</option>)}</select></label><div className="consent-explainer"><h3>What you are sharing</h3><p>Monitoring access includes your profile and photo, readings and sleep, alerts, medications, meal photos and care-team messages.</p><p>You can end this connection at any time. This does not enroll you in real-time supervision or emergency care.</p></div><label className="checkbox-label"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} required /><span>I consent to sharing my synthetic monitoring information with the selected physician.</span></label><button type="submit" className="workspace-primary" disabled={!selected || !consent || busy}>{busy ? "Connecting…" : "Connect physician"}</button></fieldset></form> : <p className="empty-copy">{physicians.length ? "You are connected to all available physicians." : "No physicians are available yet. A demo administrator can invite a physician to complete account setup."}</p>}</section></div>}
    {thread && <section className="card care-messages"><div className="workspace-section-head"><div><p className="workspace-kicker">PRIVATE CONVERSATION</p><h2>Messages with {thread.name}</h2><p>Messages are not monitored in real time. This is not an emergency channel.</p></div><button type="button" onClick={() => { setThread(null); setMessages([]); }}>Close messages</button></div><div className="message-list" aria-label="Conversation">{messages.length ? messages.map((message) => <article className={`message-bubble ${message.sender_id === session?.userId ? "message-own" : ""}`} key={message.id}><strong>{message.sender_id === session?.userId ? "You" : thread.name}</strong><p>{message.body}</p><time dateTime={message.sent_at}>{new Date(message.sent_at).toLocaleString()}</time></article>) : <p className="muted">No messages yet. Start a conversation below.</p>}</div><form onSubmit={(event) => void send(event)}><label>Your message<textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength={2000} required rows={3} placeholder="Write a non-urgent message using synthetic details…" /></label><button className="workspace-primary" type="submit" disabled={busy || !body.trim()}>{busy ? "Sending…" : "Send message"}</button></form></section>}
  </>;
}
