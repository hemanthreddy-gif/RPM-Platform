# RPM Platform — initial project description

## Status

Planning record created 2026-11-04. This is an educational research prototype, not a medical
product. It will always display: **“Demo with synthetic data. Not for medical use.”**

## Problem and intended users

People living with diabetes and/or hypertension may record health readings between visits.
Patients need a simple way to record their own readings; physicians need an organized view of
the readings, their source, age, and deterministic alerts. The project will demonstrate those
workflows using only clearly synthetic identities and data.

## Approved scope

- A web application for patients and physicians, with a separate administrative area.
- Recording glucose, blood-pressure, heart-rate, and oxygen-saturation observations, preserving
  their original units, source, and time.
- Deterministic, versioned demo alert rules. They are unverified fixtures, require clinician
  approval, and are never clinical advice.
- Patient-confirmed food-photo estimates and data-grounded draft summaries, both optional and
  safe when AI is unavailable.
- Audit records, role/relationship/consent checks, synthetic-data seeding, and later FHIR R4
  export and a device simulator.

## Essential safety boundaries

- Only the deterministic `clinical_rules` package may create clinical alert decisions. It has no
  network, database, clock, or AI access.
- AI may estimate food names/portions or draft a summary. It never calculates nutrients, creates
  alerts, diagnoses, prescribes, changes medication doses, or predicts outcomes.
- Nutrition calculations come from licensed food data in program code, not from an AI response.
- Observations are immutable; corrections add a new superseding record. Patient-data access is
  authorized and audited.
- The application must remain usable for core recording and alerts with AI switched off.

## Explicit assumptions and open items

1. The source blueprint is unavailable. This description is based only on the approved
   `docs/build-guide.md`; it does not reconstruct or claim the missing blueprint's contents.
2. The initial build target is local Windows development using Docker Desktop, with no deployment
   or real clinical use authorized.
3. The default provider will be `AI_PROVIDER=fake`; no paid AI account, key, or model is needed.
4. The guide's numerical alert fixtures are not clinically reviewed. They remain demo-only and
   `requires_clinician_approval` until qualified review is documented.
5. Indian nutrition data (IFCT 2017) has not been provided or licensed. Phase 7 cannot use it
   until the user supplies lawful data and licence information. Test fixtures will be clearly fake.
6. The repository has not yet been initialized as a Git repository. No remote, branch, CI run,
   commit, or deployment is assumed.

## Out of scope for this preparation

No application code, Docker configuration, database, user account, medical validation, paid AI
integration, external messaging, or deployment has been created.
