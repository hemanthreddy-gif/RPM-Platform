# ADR 008: Private profiles, invited physicians and patient-controlled connections

Accepted for the local synthetic educational prototype, 2026-11-06.

## Decision

Public registration continues to create patients only. A trusted local provisioning operator or
an MFA-authenticated administrator issues a 48-hour, single-use physician invitation. Redemption
creates a 15-minute scoped enrollment session; no user, physician, access token or refresh token
is created until a valid authenticator code confirms MFA. Tokens are stored hashed, the MFA secret
is encrypted, and five invalid codes exhaust enrollment. Row locks serialize redemption. Reissue
invalidates the previous invitation and enrollment. A demo registration number is not credential
verification or clinician approval. ADR 005 still requires OIDC before non-demo use.

Patients can edit their fictional name, birth date, gender, phone, timezone and self-reported
height/weight. Age is calculated from birth date. A JPEG/PNG profile image is limited to 2 MB and
12 million decoded pixels, normalized to a JPEG of at most 512 pixels per side and stripped of
metadata. Its bounded bytes live in the protected patient row, avoiding a public image URL and
keeping the audit and image write atomic. Photo reads require patient access and return no-store.
This small local-demo decision differs from meal photos, which continue to use private S3 storage.

Sleep is an immutable observation in hours (0–24), with the same authenticated provenance,
idempotency, audit and outbox transaction as other records. The UI labels it self-reported sleep
in the preceding 24 hours. It is excluded from clinical rules and target-pattern evaluation; no
sleep score, target, threshold, diagnosis or advice is introduced. Height/weight remain editable
profile context, not clinical observation history.

Patients may select an activated physician and explicitly consent to monitoring. The server
creates a dedicated consent and relationship in one audited transaction. Locking the patient row
prevents duplicate connections on retries. Ending a connection preserves its history, ends the
relationship and revokes that consent when no other active relationship uses it. Legacy trusted
assignments may share a consent; ending one does not revoke the other. Conversations require
their exact participants and their own live relationship/consent,
enforced by both application checks and database policies.

## Consequences and limits

The UI can complete physician setup and patient sharing without exposing role selection in public
registration or requiring patients to paste internal physician identifiers. Local operators still
need the configured provisioning key; it is never embedded in frontend code. No email is sent.
The optional operator form returns a code for the operator to share privately.

Profile updates and all authorized patient-data reads/writes are audited without copying sensitive
payloads into logs. The new CORS methods support browser PATCH and DELETE from the configured
origin only. Automated accessibility checks are engineering evidence, not a WCAG certification.
The app remains synthetic-only, unvalidated and unsuitable for medical or public production use.
