"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "../../../../components/app-shell";
import { PageHeading } from "../../../../components/page-heading";
import { Icon } from "../../../../components/icon";
import { api } from "../../../../lib/api/client";
import type { Observation, ObservationType } from "../../../../lib/api/generated";
import { getSession } from "../../../../lib/auth/session";

const names: Record<ObservationType, string> = { glucose: "Glucose", blood_pressure: "Blood pressure", heart_rate: "Heart rate", spo2: "Oxygen saturation", sleep: "Sleep duration" };

function HistoryContent() {
  const [readings, setReadings] = useState<Observation[]>([]);
  const [type, setType] = useState<ObservationType>("glucose");
  const [days, setDays] = useState("30");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshedAt, setRefreshedAt] = useState(0);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const session = getSession(); if (!session) return;
    let cancelled = false;
    void api.me(session.accessToken).then((profile) => api.observations(profile.id, session.accessToken)).then((result) => {
      if (!cancelled) { setReadings(result); setRefreshedAt(Date.now()); setError(""); }
    }).catch(() => { if (!cancelled) setError("Reading history could not be loaded. Please refresh to try again."); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [revision]);
  const filtered = readings.filter((record) => record.type === type && (days === "all" || new Date(record.measured_at).getTime() >= refreshedAt - Number(days) * 86_400_000));
  const chart = [...filtered].reverse().map((record) => ({ time: new Date(record.measured_at).getTime(), value: Number(record.value), systolic: Number(record.components.systolic), diastolic: Number(record.components.diastolic) }));
  const unit = filtered[0]?.unit ?? "";
  return <section className="card">
    <div className="history-controls"><label>Reading type<select value={type} onChange={(event) => setType(event.target.value as ObservationType)}>{Object.entries(names).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label><label>Time range<select value={days} onChange={(event) => setDays(event.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="all">Loaded history</option></select></label><button className="touch-button" aria-pressed={view === "table"} onClick={() => setView(view === "chart" ? "table" : "chart")}>{view === "chart" ? "Table view" : "Chart view"}</button><button className="touch-button" disabled={loading} onClick={() => { setLoading(true); setRevision((value) => value + 1); }}>Refresh</button></div>
    {loading ? <p className="loading-copy" role="status">Loading your recorded history…</p> : error ? <p className="form-error" role="alert">{error}</p> : !filtered.length ? <div className="empty-state"><Icon name={type === "sleep" ? "moon" : "chart"} /><h3>No {names[type].toLowerCase()} records in this view</h3><p>Choose another time range or save a new entry from Log readings & sleep.</p></div> : <>
      <div className="workspace-section-head" style={{ marginTop: 28 }}><div><h2>{names[type]} history</h2><p>{filtered.length} recorded {filtered.length === 1 ? "entry" : "entries"} · {unit} · Latest: {new Date(filtered[0].measured_at).toLocaleString()}</p></div></div>
      {view === "chart" ? <><div className="history-chart" role="img" aria-label={`${names[type]} chart with ${filtered.length} records in ${unit}. Use Table view for individual values, timestamps and sources.`}><ResponsiveContainer width="100%" height="100%"><LineChart data={chart} margin={{ top: 15, right: 15, left: -15, bottom: 10 }}><CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#e3e9df" /><XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} tickFormatter={(value: number) => new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" })} fontSize={10} tickLine={false} axisLine={false} /><YAxis domain={["auto", "auto"]} fontSize={10} tickLine={false} axisLine={false} /><Tooltip labelFormatter={(value) => new Date(Number(value)).toLocaleString()} formatter={(value, name) => [`${value} ${unit}`, name]} />{type === "blood_pressure" ? <><Line dataKey="systolic" name="Systolic" stroke="#286f59" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} /><Line dataKey="diastolic" name="Diastolic" stroke="#7d6198" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} isAnimationActive={false} /></> : <Line dataKey="value" name={names[type]} stroke={type === "sleep" ? "#7d6198" : "#286f59"} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />}</LineChart></ResponsiveContainer></div>{type === "blood_pressure" && <p className="history-chart-note">Solid line: systolic · Dashed line: diastolic. Both values use mmHg.</p>}</> : <div className="table-scroll"><table><caption className="sr-only">{names[type]} records with measurement time and source</caption><thead><tr><th>Measured</th><th>Value</th><th>Source</th><th>Received</th></tr></thead><tbody>{filtered.map((record) => <tr key={record.id}><td>{new Date(record.measured_at).toLocaleString()}</td><td>{record.value ?? `${record.components.systolic}/${record.components.diastolic}`} {record.unit}</td><td><span className="source-badge">{record.source}</span></td><td>{new Date(record.recorded_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
    </>}
    <p className="history-chart-note">This view uses the latest {readings.length} records returned by the server, up to 50. Dates are shown in your browser timezone. Lines connect recorded entries and do not imply continuous measurement. No target range or clinical interpretation is inferred.{type === "sleep" ? " Sleep entries are self-reported hours." : ""}</p>
  </section>;
}
export default function TrendsPage() { return <AppShell role="patient"><PageHeading eyebrow="YOUR RECORD, OVER TIME" title="History & trends" description="Explore your readings and sleep with a chart or a detailed table. Every entry retains its source and time." /><HistoryContent /></AppShell>; }
