import { AppShell } from "../../../../components/app-shell";
import { MealPhotoUpload } from "../../../../components/meal-photo-upload";
import { PatientMealPhotos } from "../../../../components/patient-meal-photos";

export default function MealPhotosPage() { return <AppShell role="patient"><h1 className="text-2xl font-bold">Meal photos</h1><MealPhotoUpload /><PatientMealPhotos /></AppShell>; }
