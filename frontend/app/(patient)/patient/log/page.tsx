import { AppShell } from "../../../../components/app-shell"; import { ObservationForm } from "../../../../components/observation-form";
export default function LogPage() { return <AppShell role="patient"><h1 className="text-2xl font-bold">Log a reading</h1><ObservationForm /></AppShell>; }
