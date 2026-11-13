import { AppShell } from "../../../../components/app-shell";
import { PhysicianWorklist } from "../../../../components/physician-worklist";
import { PageHeading } from "../../../../components/page-heading";
export default function DirectoryPage() { return <AppShell role="physician"><PageHeading eyebrow="CONNECTED PATIENTS" title="Patient directory" description="Find the people who have shared their synthetic monitoring records with you." /><PhysicianWorklist /></AppShell>; }
