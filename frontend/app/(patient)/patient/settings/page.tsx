import { AppShell } from "../../../../components/app-shell";
import { Phase9Settings } from "../../../../components/phase9-settings";
import { PageHeading } from "../../../../components/page-heading";
import { Icon } from "../../../../components/icon";
import Link from "next/link";
export default function SettingsPage() { return <AppShell role="patient"><PageHeading eyebrow="YOUR PREFERENCES & CONNECTIONS" title="Settings & devices" description="Manage your profile, sharing permissions and synthetic device connections." /><div className="settings-links"><Link className="card" href="/patient/profile"><Icon name="user" size={25} /><div><h2>Personal profile</h2><p>Your photo, personal details and body measurements.</p></div><Icon name="arrow" /></Link><Link className="card" href="/patient/care-team"><Icon name="shield" size={25} /><div><h2>Consent & care team</h2><p>Choose your physicians and control their access.</p></div><Icon name="arrow" /></Link></div><Phase9Settings /></AppShell>; }
