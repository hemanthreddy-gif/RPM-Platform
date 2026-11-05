# Automated walkthrough — synthetic demo

Reviewed 2026-11-05 by code inspection and automated regression tests. This is not a participant
study, SUS score, independent accessibility audit, clinician/faculty review, or approval. No real
users, patients or clinical records were involved. The [human protocol](human-protocol.md) remains
pending for any claim about usability or clinical feedback.

| Task or safety question | Observation | Disposition and evidence |
| --- | --- | --- |
| Log a reading | A network failure after acceptance could cause the client to retry with a different idempotency key. | The same key now follows the queued retry; `frontend/tests/observation-submission.test.ts` exercises a lost response. |
| Sync offline readings | Replay deleted the entire queue, including entries added during replay. | Remove each accepted queued entry individually; `frontend/tests/queue.test.ts` covers concurrent enqueue and failure retention. |
| Understand a server result | Immediate synthetic alert wording from the server was not displayed. | The submission and replay paths surface returned guidance; the submission test checks it. Browser E2E remains unverified in this environment. |
| Enter blood pressure | The UI labelled blood pressure as bpm, and the database required a scalar original value although blood pressure is represented by components. | The UI selects mmHg and a migration permits component-only blood pressure while retaining scalar requirements. Unit and static migration checks are available; PostgreSQL migration and transaction tests remain pending. |
| Enter malformed values | Empty inputs could be sent or queued, and client HTTP rejections were described as connection failures. | Positive finite values are required before submission; a server 4xx rejection is shown as rejected rather than queued. |
| Record meal context | The form silently set glucose meal timing to zero without user input. | Context is empty unless explicitly provided; no meal timing is invented. |
| Meal-photo flow | Photo upload and physician comment screens exist; unstable session object identity could cause repeated fetches. Full workflow and accessibility were not exercised here. | The fetch effect now depends on the token value. Existing photo unit tests cover input and storage boundaries. Browser and PostgreSQL integration evidence requires a configured environment. |

This review does not establish safety, medical efficacy, accessibility conformance or that users
understand the product. All rule fixtures remain synthetic and unreviewed. The deployment and
security gaps in [release readiness](../deployment-readiness.md) remain open.
