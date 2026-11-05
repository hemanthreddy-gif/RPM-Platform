"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { Alert } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

export function PatientAlertList() {
  const [alerts, setAlerts] = useState<Alert[]>([]); const [error, setError] = useState("");
  useEffect(() => { const session = getSession(); if (!session) return; void api.alerts(session.accessToken).then(setAlerts).catch(() => setError("Alerts could not be refreshed.")); }, []);
  return <section className="card"><h2 className="text-xl font-semibold">Server-supplied alert status</h2>{error && <p role="alert">{error}</p>}{alerts.length ? <ul>{alerts.map((alert) => <li key={alert.id}><strong>{alert.severity}</strong> — {alert.status}: {alert.guidance}</li>)}</ul> : <p className="muted">No alerts are available.</p>}<p className="muted">This app is not an emergency service. Do not wait for a response from this app in an emergency.</p></section>;
}
