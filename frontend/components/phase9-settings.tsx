"use client";

import { useState } from "react";
import { api } from "../lib/api/client";
import { getSession } from "../lib/auth/session";
import type { Device } from "../lib/api/generated";
import { Icon } from "./icon";

export function Phase9Settings() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState(""); const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false); const [loaded, setLoaded] = useState(false);
  const session = getSession();
  const refreshDevices = async () => {
    if (!session) return;
    setBusy(true); setError("");
    try { const me = await api.me(session.accessToken); setDevices(await api.devices(me.id, session.accessToken)); setLoaded(true); }
    catch { setError("Devices could not be loaded. Please try again."); }
    finally { setBusy(false); }
  };
  if (!session) return null;
  const pair = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    setBusy(true); setError(""); setToken("");
    try {
      const paired = await api.pairDevice(form.get("kind") as "glucose_meter" | "blood_pressure_monitor", String(form.get("vendor")), String(form.get("serial") || "") || undefined, session.accessToken);
      setToken(paired.pairing_token); await refreshDevices();
    } catch { setError("Device pairing failed. Please check the details and try again."); }
    finally { setBusy(false); }
  };
  return <div className="record-grid">
    <section className="card"><div className="record-section-heading"><span><Icon name="activity" /></span><div><h2>Paired synthetic devices</h2><p>View device status and the last recorded sync.</p></div></div><button className="touch-button" style={{ marginTop: 20 }} type="button" disabled={busy} onClick={() => void refreshDevices()}>{busy ? "Loading…" : "Refresh devices"}</button>
      {loaded && (devices.length ? <ul className="mt-4 space-y-4">{devices.map((device) => <li key={device.id} className="alert-record"><strong>{device.vendor}</strong><p>{device.kind.replaceAll("_", " ")} · {device.status}</p><p>Last sync: {device.last_sync_at ? new Date(device.last_sync_at).toLocaleString() : "No sync yet"}</p></li>)}</ul> : <div className="empty-state"><Icon name="activity" /><h3>No paired devices yet</h3><p>Use the form to register a synthetic demo device.</p></div>)}
      <p className="history-chart-note">Device data can arrive late. Sync times indicate receipt, not clinical review.</p>
    </section>
    <section className="card"><h2>Pair a demo device</h2><p className="muted">Use fictional device details. Pairing creates a token for the development simulator.</p><form onSubmit={(event) => void pair(event)}><fieldset disabled={busy}><label>Device type<select name="kind"><option value="glucose_meter">Glucose meter</option><option value="blood_pressure_monitor">Blood pressure monitor</option></select></label><label>Device vendor<input name="vendor" required maxLength={100} placeholder="e.g. Synthetic Demo Devices" /></label><label>Serial number <span className="field-hint">Optional</span><input name="serial" maxLength={100} placeholder="Demo serial number" /></label><button className="workspace-primary" type="submit">Pair device <Icon name="plus" size={17} /></button></fieldset></form>{token && <div className="success-notice" role="status"><strong>Device paired</strong><p>Copy this token now. It is shown only once.</p><code style={{ overflowWrap: "anywhere", fontSize: 11 }}>{token}</code></div>}{error && <p className="form-error" role="alert">{error}</p>}</section>
  </div>;
}
