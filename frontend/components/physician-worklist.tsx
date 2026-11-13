"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { PhysicianWorklistItem } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";
import { Icon } from "./icon";

export function PhysicianWorklist() {
  const [items, setItems] = useState<PhysicianWorklistItem[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback((nextQuery: string) => {
    const session = getSession(); if (!session) return;
    void api.worklist(session.accessToken, nextQuery).then(setItems).catch(() => {
      setItems([]); setError("Your patient list could not be refreshed. Please try again.");
    }).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(""); }, [load]);
  const withAlerts = items.filter((item) => item.active_alert_severity);
  const visible = filter === "alerts" ? withAlerts : items;
  return <section className="card" aria-label="Patient worklist">
    <div className="worklist-toolbar">
      <form className="worklist-search" onSubmit={(event) => { event.preventDefault(); setLoading(true); setError(""); load(query); }}>
        <label htmlFor="patient-search">Search your connected patients<input id="patient-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by patient name…" /></label>
        <button className="touch-button primary" type="submit" disabled={loading}><Icon name="search" size={17} /> Search</button>
      </form>
      <label style={{ margin: 0, fontSize: 12 }}>Show<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All connected patients</option><option value="alerts">With active alerts</option></select></label>
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {loading ? <p role="status" className="loading-copy">Loading authorized patient records…</p> : !error && <>
      <div className="worklist-stats">
        <div className="worklist-stat"><span>Connected patients</span><strong>{items.length}</strong><small>In the current search results</small></div>
        <div className="worklist-stat"><span>With active alerts</span><strong>{withAlerts.length}</strong><small>Server-recorded alert status</small></div>
        <div className="worklist-stat"><span>With a recorded reading</span><strong>{items.filter((item) => item.latest_observation_at).length}</strong><small>In the current search results</small></div>
      </div>
      {visible.length ? <div className="table-scroll"><table><caption className="sr-only">Authorized patient worklist with active alert severity and most recent reading</caption><thead><tr><th>Patient</th><th>Active alert</th><th>Most recent accepted reading</th><th><span className="sr-only">Open record</span></th></tr></thead><tbody>{visible.map((item) => <tr key={item.id}>
        <td><div className="patient-cell"><span className="person-avatar" aria-hidden="true">{item.display_name.slice(0, 1)}</span><div><Link className="text-link" href={`/physician/patients/${item.id}`}>{item.display_name}</Link><small>{item.timezone}</small></div></div></td>
        <td><span className={`status-badge ${item.active_alert_severity ?? ""}`}>{item.active_alert_severity ?? "No active alerts"}</span></td>
        <td>{item.latest_observation_at ? <time dateTime={item.latest_observation_at}>{new Date(item.latest_observation_at).toLocaleString()}</time> : <span className="muted">No accepted reading</span>}</td>
        <td><Link className="nav-link" aria-label={`Open record for ${item.display_name}`} href={`/physician/patients/${item.id}`}><Icon name="arrow" size={18} /></Link></td>
      </tr>)}</tbody></table></div> : <div className="empty-state"><Icon name="users" /><h3>{query || filter !== "all" ? "No patients match this view" : "Your care workspace starts here"}</h3><p>{query || filter !== "all" ? "Try another name or select all connected patients." : "Patients can connect with you from their Care team page. Their records appear here after they grant monitoring consent."}</p></div>}
    </>}
    <p className="muted worklist-footer"><Icon name="shield" size={14} /> Only active relationships with monitoring consent are shown. Alert severity is a stored demo fact, not clinical advice.</p>
  </section>;
}
