# Phase 7 plan — meal-photo review fallback

## Scope decision and safety boundary

The documented Food photo analysis and nutrition module cannot be completed honestly in this
slice: no licensed IFCT 2017 (or alternative Indian) nutrition dataset, recorded licence, or
USDA subset has been supplied. The architecture prohibits inventing values or allowing an AI
provider to generate nutrients. The Phase 7 fallback therefore implements a narrower,
non-nutrition workflow: a patient can upload a meal-plate photo and an authorized physician can
view it and leave a non-clinical comment. It deliberately contains no AI processing, food
identification, nutrient calculation, nutrition goal comparison, suitability label, diagnosis,
or medication advice.

The existing Phase 4–6 quality debt remains open: 64% repository coverage versus the 80% target
and an invalid mutmut run with no usable score. No clinical validation or clinician approval is
claimed by this work.

## Authorized slice

1. Add `nutrition` module migrations that record private photo metadata and append-only
   physician comments, with RLS policies enforcing active monitoring relationships and purpose
   specific consent. Photos stay in the configured S3-compatible store; the database retains
   only opaque keys and cryptographic digests.
2. Add strict JPEG/PNG validation and server-side re-encoding to remove EXIF metadata before
   private upload. Keep storage behind an S3-compatible interface and provide a test fake. Do
   not log images, image URLs, notes, or comments.
3. Add typed, audited APIs for patient upload/list/detail, authorized image retrieval, and
   physician comment creation. The fallback uses monitoring consent because it is a direct
   clinician review workflow; it does not call an external AI provider and therefore does not
   activate `ai_processing`.
4. Add patient capture/upload and authorized physician-gallery/comment UI, with permanent
   synthetic-demo and non-clinical-review language. Ensure images are fetched only with an
   authenticated request and never added to the service-worker cache.
5. Add unit tests for image validation/re-encoding, storage failure handling, and safety copy;
   add opt-in PostgreSQL tests for RLS/access and append-only comments. Run relevant static,
   frontend, and backend checks; record unrun infrastructure-dependent checks precisely.

## Explicitly deferred

- Licensed nutrition-data ingestion and `LICENSES.md` evidence.
- LLM/FakeProvider food identification and all background AI processing.
- Food matching, nutrient arithmetic, nutrient ranges, corrections, confirmation, charts, and
  nutrition-goal/suitability logic.
- Any implication that the photo or a comment is medical, dietary, or clinical advice.

## Completion evidence

The fallback is complete only when the migration is reviewed, authorization and audit paths are
covered, all visible screens preserve the safety disclosure, and the documented Phase 7 nutrition
blocker plus carried quality debt are recorded in `docs/PROGRESS.md`.

## Completion evidence (2026-11-04)

The fallback scope is complete. Migrations `0007_meal_photo_review` and
`0008_meal_photo_comment_grants` were reviewed and applied to the disposable synthetic `rpm` and
`rpm_test` databases. PostgreSQL RLS tests prove an unrelated physician cannot read a meal and
that neither a patient nor a physician can mutate retained photo/comment records. A live
Playwright scenario creates synthetic identities, uploads a synthetic PNG, displays it to the
active related physician, posts a comment, and confirms it is visible to the patient. The actual
nutrition/AI module remains expressly deferred pending licensed data.
