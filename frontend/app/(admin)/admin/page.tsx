import { AppShell } from "../../../components/app-shell";
import { PhysicianInvitationForm } from "../../../components/physician-onboarding";
export default function AdminPage() { return <AppShell role="admin"><div className="patient-heading"><div><p className="workspace-kicker">ACCOUNT MANAGEMENT</p><h1>Administration</h1><p>Manage access to the synthetic demo.</p></div></div><section className="card"><p className="font-semibold">Administrators do not have access to clinical or patient data.</p><PhysicianInvitationForm /></section></AppShell>; }
