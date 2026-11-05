import Link from "next/link";
import { AppShell } from "../../../components/app-shell";
import { ObservationForm } from "../../../components/observation-form";
import { PatientLiveSummary } from "../../../components/patient-live-summary";
export default function PatientHome() { return <AppShell role="patient"><div className="patient-heading"><div><p className="workspace-kicker">YOUR PERSONAL OVERVIEW</p><h1>Your monitoring home</h1><p>A little more clarity, one reading at a time.</p></div><Link className="workspace-primary" href="/patient/trends">Explore your trends <span>↗</span></Link></div><ObservationForm /><div className="patient-overview"><div className="workspace-section-head"><div><p className="workspace-kicker">AT A GLANCE</p><h2>Your recent activity</h2><p>Your latest readings, alerts and medications in one place.</p></div></div><div className="summary-grid"><PatientLiveSummary /></div></div></AppShell>; }
