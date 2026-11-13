/* Typed frontend DTOs aligned with backend schemas. api:generate refreshes the OpenAPI snapshot. */
export type ObservationType = "glucose" | "blood_pressure" | "heart_rate" | "spo2" | "sleep";
export type ObservationCreate = {
  type: ObservationType;
  value?: number;
  unit: string;
  components?: Record<string, number>;
  measured_at: string;
  context?: Record<string, unknown>;
  confirm_unusual?: boolean;
};
export type Alert = { id: string; patient_id: string; rule_code: string; severity: string; status: string; created_at: string; guidance: string };
export type PatientProfile = {
  id: string; display_name: string; timezone: string; has_hypertension: boolean;
  date_of_birth?: string | null; age?: number | null; gender?: string | null; phone?: string | null;
  height_cm?: number | null; weight_kg?: number | null; has_profile_picture?: boolean;
  profile_picture_updated_at?: string | null;
};
export type ProfileUpdate = Pick<PatientProfile, "display_name" | "date_of_birth" | "gender" | "phone" | "height_cm" | "weight_kg" | "timezone" | "has_hypertension">;
export type Physician = { id: string; display_name: string; specialty: string | null };
export type PatientConnection = { id: string; physician_id: string; display_name: string; specialty: string | null; consent_id: string; started_at: string; active: boolean };
export type PhysicianWorklistItem = Pick<PatientProfile, "id" | "display_name" | "timezone" | "has_hypertension"> & { active_alert_severity: string | null; latest_observation_at: string | null };
export type Observation = { id: string; patient_id: string; type: ObservationType; value: number | null; unit: string; components: Record<string, number>; measured_at: string; recorded_at: string; source: string; quality_flag: string | null };
export type Medication = {
  id: string; name: string; dose: string | null; frequency: string; schedule_times: string[];
  timezone: string; instructions: string | null; provenance: "physician_authored_synthetic_record";
};
export type TokenResponse = { access_token: string; refresh_token: string; mfa_required: boolean };
export type MealPhotoComment = { id: string; body: string; created_at: string };
export type MealPhoto = {
  id: string; eaten_at: string; uploaded_at: string; status: string;
  image_content_type: string; image_size_bytes: number; comments: MealPhotoComment[];
};
export type Device = { id: string; kind: string; vendor: string; serial: string | null; status: string; last_sync_at: string | null; last_received_at: string | null };
export type DevicePairing = { id: string; pairing_token: string; status: string };
export type Message = { id: string; sender_id: string; recipient_id: string; body: string; kind: string; sent_at: string; read_at: string | null };
export type MessageThread = { id: string; patient_id: string; physician_id: string; created_at: string; expected_response_notice: string };
