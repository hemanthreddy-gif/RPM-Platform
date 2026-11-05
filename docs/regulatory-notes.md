# India regulatory research notes

Reviewed 2026-11-05. This is a research checklist for a synthetic educational prototype, not legal
advice, a classification decision or a claim of compliance. Application depends on actual intended
use, entities, data and current law. Obtain qualified legal and regulatory advice before any
real-patient or clinical use. There is no real-patient deployment or clinician approval here.

| Topic | Source and potential requirement | Existing design / open work |
| --- | --- | --- |
| Medical device software | [CDSCO medical-device software guidance](https://www.cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf) and [Medical Devices Rules](https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Medical-Devices-Rules) describe the regulatory framework. Intended purpose and risk matter. | The demo disclaims medical use and rules are unreviewed. No determination of classification, licence, safety effectiveness or regulatory status has been made; obtain a formal assessment before changing intended use. |
| Digital personal data | The [DPDP Act](https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf) and [2025 Rules](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf) have phased commencement. Applicability and obligations must be checked against the actual processing and current commencement notices. | Synthetic data only; access checks and audit are implemented. No completed legal basis, data-subject rights, retention, breach-response or processor assessment is claimed. |
| Telemedicine | [Telemedicine Practice Guidelines](https://www.mohfw.gov.in/pdf/Telemedicine.pdf) address care provided by registered medical practitioners, including professional judgment and consultation processes. | Synthetic messaging and comments are not a real teleconsultation service. Practitioner verification, clinical workflows and legal review would be needed for any proposed clinical use. |
| ABDM | [ABDM health data management policy](https://abdm.gov.in/publications/policies_regulations/health_data_management_policy) addresses the ecosystem and data handling. | Purpose-specific demo consent and a limited FHIR subset exist; ABDM integration, onboarding, consent artefacts and conformance have not been assessed or implemented. |
| Cyber incidents | [CERT-In directions and FAQs](https://cert-in.org.in/Directions70B.jsp) include incident-reporting and other operational requirements for covered entities and incidents. | Local logs and security tests do not establish compliance. Determine applicability, incident ownership, reporting procedures, log retention and timing with qualified advice before operation. |

No document in this repository is an authorization to process real health data, deploy a medical
device or advertise clinical effectiveness. See [release readiness](deployment-readiness.md).
