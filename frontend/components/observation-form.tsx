"use client";
import { useState } from "react";
import { submitObservation } from "../lib/api/observation-submission";
import type { ObservationCreate, ObservationType } from "../lib/api/generated";
import { getSession } from "../lib/auth/session";

type Field = { type: ObservationType; label: string; icon: string; unit: string; placeholder: string };
const fields: Field[] = [
  { type: "glucose", label: "Glucose", icon: "◈", unit: "mg/dL", placeholder: "e.g. 100" },
  { type: "blood_pressure", label: "Blood pressure", icon: "♡", unit: "mmHg", placeholder: "120" },
  { type: "heart_rate", label: "Heart rate", icon: "⌁", unit: "bpm", placeholder: "e.g. 72" },
  { type: "spo2", label: "Oxygen saturation", icon: "◉", unit: "%", placeholder: "e.g. 98" },
];
const emptyValues = { glucose: "", blood_pressure: "", heart_rate: "", spo2: "" };
export function ObservationForm() {
  const [values, setValues] = useState<Record<ObservationType, string>>(emptyValues);
  const [diastolic, setDiastolic] = useState(""); const [unit, setUnit] = useState("mg/dL");
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const [results, setResults] = useState<Partial<Record<ObservationType, string>>>({});
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const session = getSession();
    if (!session) return setMessage("Your session has ended. Please log in again.");
    const selected = fields.filter((field) => values[field.type].trim() || (field.type === "blood_pressure" && diastolic.trim()));
    if (!selected.length) return setMessage("Enter at least one reading.");
    for (const field of selected) {
      const parts = field.type === "blood_pressure" ? [values[field.type], diastolic] : [values[field.type]];
      if (parts.some((part) => !part.trim() || !Number.isFinite(Number(part)) || Number(part) <= 0)) return setMessage(`Enter a positive number for ${field.label}${field.type === "blood_pressure" ? " (both values)" : ""}.`);
    }
    setBusy(true); setMessage(""); setResults({}); const measuredAt = new Date().toISOString();
    try {
      for (const field of selected) {
        const payload: ObservationCreate = { type: field.type, unit: field.type === "glucose" ? unit : field.unit, measured_at: measuredAt, context: {} };
        if (field.type === "blood_pressure") payload.components = { systolic: Number(values.blood_pressure), diastolic: Number(diastolic) }; else payload.value = Number(values[field.type]);
        const result = await submitObservation(session.userId, session.accessToken, payload, !navigator.onLine);
        setResults((previous) => ({ ...previous, [field.type]: result }));
        if (result.startsWith("Reading submitted.") || result.startsWith("Saved for retry")) {
          setValues((previous) => ({ ...previous, [field.type]: "" }));
          if (field.type === "blood_pressure") setDiastolic("");
        }
      }
      setMessage("Review the result shown for each reading. Readings are saved individually.");
    } finally { setBusy(false); }
  };
  return <section className="readings-section"><div className="workspace-section-head"><div><p className="workspace-kicker">YOUR READINGS</p><h2>Log a reading</h2><p>Enter any readings you want to record, then save them together.</p></div></div><form onSubmit={submit}><fieldset disabled={busy}><div className="reading-grid">{fields.map((field) => <section className="reading-card" key={field.type}><div className="reading-card-head"><span className={`reading-icon reading-${field.type}`}>{field.icon}</span><div><h3>{field.label}</h3><p>Record a reading</p></div></div>{field.type === "blood_pressure" ? <div className="bp-inputs"><label>Systolic<input inputMode="decimal" placeholder={field.placeholder} value={values.blood_pressure} onChange={(event) => setValues({ ...values, blood_pressure: event.target.value })} /></label><label>Diastolic<input inputMode="decimal" placeholder="80" value={diastolic} onChange={(event) => setDiastolic(event.target.value)} /></label></div> : <label>{field.label}<input inputMode="decimal" placeholder={field.placeholder} value={values[field.type]} onChange={(event) => setValues({ ...values, [field.type]: event.target.value })} /></label>}{field.type === "glucose" ? <label>Glucose unit<select value={unit} onChange={(event) => setUnit(event.target.value)}><option>mg/dL</option><option>mmol/L</option></select></label> : <p className="reading-unit">Unit: {field.unit}</p>}{results[field.type] && <p className="reading-status">{results[field.type]}</p>}</section>)}</div></fieldset><button className="workspace-primary readings-submit" disabled={busy} type="submit">{busy ? "Saving readings…" : "Save readings"} <span aria-hidden="true">↗</span></button><div role="status" className="reading-status" aria-live="polite">{message}{Object.entries(results).map(([key, result]) => <p key={key}>{fields.find((field) => field.type === key)?.label}: {result}</p>)}</div></form></section>;
}
