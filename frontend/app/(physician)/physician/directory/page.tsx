import { AppShell } from "../../../../components/app-shell";
import { PhysicianWorklist } from "../../../../components/physician-worklist";
export default function DirectoryPage() { return <AppShell role="physician"><h1 className="text-2xl font-bold">Patient directory</h1><PhysicianWorklist /></AppShell>; }
