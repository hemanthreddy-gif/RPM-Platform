# Profile, sleep and connections implementation notes

Authorized slice of the 2026-11-06 interface redesign:

1. Extend the authorized patient DTO with editable fictional demographics, height and weight.
   Store a bounded, metadata-stripped JPEG in the protected patient row for private pictures.
2. Add self-reported sleep hours to immutable observations; never pass sleep to clinical rules,
   generate sleep thresholds, or imply a diagnosis. Preserve transaction and idempotency paths.
3. Let patients discover activated physicians, explicitly grant monitoring consent and establish
   a relationship, view connections and revoke the relationship and its dedicated consent.
4. Verify input boundaries, image processing, audited storage and revocation under PostgreSQL RLS.

Profile measurements are self-reported context, not clinical observations or medication inputs.
Birth date is stored and age is derived; no real patient details belong in this synthetic demo.
Existing original observation history and unrelated changes remain untouched.

Implemented with PostgreSQL regression evidence for profile/image authorization and audit,
sleep transaction/replay, exact conversation participants, revocation and shared legacy consent.
See PROGRESS.md for final verification and remaining repository-wide release gaps.
