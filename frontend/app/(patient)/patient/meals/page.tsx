import { AppShell } from "../../../../components/app-shell";
import { MealPhotoUpload } from "../../../../components/meal-photo-upload";
import { PatientMealPhotos } from "../../../../components/patient-meal-photos";
import { PageHeading } from "../../../../components/page-heading";

export default function MealPhotosPage() { return <AppShell role="patient"><PageHeading eyebrow="MORE OF YOUR EVERYDAY" title="Meal photos" description="Add a photo to your daily record and see comments from your connected physician." /><MealPhotoUpload /><PatientMealPhotos /></AppShell>; }
