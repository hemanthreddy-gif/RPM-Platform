"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api/client";
import type { PhysicianWorklistItem } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

function age(value: string | null): string { return value ? new Date(value).toLocaleString() : "No accepted reading"; }

export function PhysicianWorklist() {
  const [items, setItems] = useState<PhysicianWorklistItem[]>([]); const [query, setQuery] = useState(""); const [error, setError] = useState("");
  const load = useCallback((nextQuery: string) => { const session = getSession(); if (!session) return; void api.worklist(session.accessToken, nextQuery).then(setItems).catch(() => setError("Authorized worklist could not be refreshed.")); }, []);
  useEffect(() => { load(""); }, [load]); // Initial server refresh only; explicit search avoids repeated clinical-data reads.
  return <section className="card" aria-labelledby="worklist-heading"><h2 id="worklist-heading" className="text-xl font-semibold">Patient worklist</h2>
    <form onSubmit={(event) => { event.preventDefault(); load(query); }}><label htmlFor="patient-search">Search authorized synthetic patients<input id="patient-search" value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="touch-button primary">Search</button></form>
    {error && <p role="alert">{error}</p>}
    <div className="table-scroll"><table><caption className="sr-only">Authorized patient worklist with active alert severity and most recent reading</caption><thead><tr><th>Patient</th><th>Active alert</th><th>Most recent accepted reading</th></tr></thead><tbody>{items.length ? items.map((item) => <tr key={item.id}><td><Link className="text-link" href={`/physician/patients/${item.id}`}>{item.display_name}</Link></td><td>{item.active_alert_severity ?? "None"}</td><td>{age(item.latest_observation_at)}</td></tr>) : <tr><td colSpan={3}>No authorized synthetic patients found.</td></tr>}</tbody></table></div>
    <p className="muted">Only active relationships with monitoring consent are returned. Severity and age are server-supplied facts, not clinical advice.</p>
  </section>;
}
