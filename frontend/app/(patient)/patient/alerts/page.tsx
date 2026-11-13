import { AppShell } from "../../../../components/app-shell";
import { PatientAlertList } from "../../../../components/patient-alert-list";
import { PageHeading } from "../../../../components/page-heading";
export default function AlertsPage() { return <AppShell role="patient"><PageHeading eyebrow="RECORDED NOTIFICATIONS" title="Your alerts" description="View demo alerts and their current status, exactly as returned by the server." /><PatientAlertList /></AppShell>; }
