import { AppShell } from "../../../../components/app-shell";
import { Phase9Settings } from "../../../../components/phase9-settings";
export default function SettingsPage() { return <AppShell role="patient"><h1 className="text-2xl font-bold">Settings and privacy</h1><section className="card"><h2 className="text-xl font-semibold">Privacy notice</h2><p className="muted">This synthetic educational demo is not for medical use. Consent and profile controls are securely served by the API.</p></section><Phase9Settings /></AppShell>; }
