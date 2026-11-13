import Link from "next/link";
import { AppShell } from "../../../components/app-shell";
import { ObservationForm } from "../../../components/observation-form";
import { PatientLiveSummary } from "../../../components/patient-live-summary";
import { Icon } from "../../../components/icon";
import { PageHeading } from "../../../components/page-heading";

export default function PatientHome() {
  return <AppShell role="patient">
    <PageHeading eyebrow="YOUR PERSONAL OVERVIEW" title="Your monitoring home" description="A little more clarity, one check-in at a time." action={<Link className="workspace-secondary" href="/patient/trends"><Icon name="chart" size={17} /> View your history</Link>} />
    <section className="welcome-panel"><div><h2>Everyday details. A fuller picture.</h2><p>Keep your profile up to date, bring your readings together and decide who can see your information.</p></div><Link className="workspace-secondary" href="/patient/profile">Set up your profile <Icon name="arrow" size={17} /></Link></section>
    <div className="overview-shortcuts">
      <Link href="/patient/care-team"><span className="shortcut-icon mint"><Icon name="users" /></span><div><strong>Your care team</strong><small>Connect with your consent</small></div><Icon name="arrow" /></Link>
      <Link href="/patient/meals"><span className="shortcut-icon lilac"><Icon name="meal" /></span><div><strong>Meal journal</strong><small>Add context to your day</small></div><Icon name="arrow" /></Link>
      <Link href="/patient/alerts"><span className="shortcut-icon blue"><Icon name="bell" /></span><div><strong>Your alerts</strong><small>Review recorded alert status</small></div><Icon name="arrow" /></Link>
    </div>
    <ObservationForm />
    <section className="patient-overview"><div className="workspace-section-head"><div><p className="workspace-kicker">AT A GLANCE</p><h2>Your recent activity</h2><p>Records from your account, with their sources and timestamps.</p></div></div><div className="summary-grid"><PatientLiveSummary /></div></section>
  </AppShell>;
}
