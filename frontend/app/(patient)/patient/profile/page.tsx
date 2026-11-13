import { AppShell } from "../../../../components/app-shell";
import { PatientProfileEditor } from "../../../../components/patient-profile";

export default function ProfilePage() {
  return <AppShell role="patient"><PatientProfileEditor /></AppShell>;
}
