# Release readiness — synthetic demo only

The repository is **not ready for a public deployment**. The existing `docker-compose.yml` is a
local development stack with development defaults and localhost-bound ports. The separate
`backend/Dockerfile.demo` and `frontend/Dockerfile.demo` are unverified image candidates, not a
complete deployment. The frontend candidate requires a browser-reachable `NEXT_PUBLIC_API_BASE_URL`
at build time. No TLS proxy, production Compose, deploy script, public credentials, or hosted
service is provided.

Before enabling any public synthetic demo, implement and verify all of the following together:

- Restricted synthetic patient and physician accounts; no public administration or privilege
  provisioning; isolated tenant access and no real data. Test direct API access, not only UI.
- A reset that is independently scoped to the demo database and object store, requires an explicit
  demo environment, has concurrency/rate limits and audit evidence, and cannot reset other data.
  Test failure, concurrency, rollback and incorrect-environment paths before scheduling it.
- Disable external messaging and any unsafe administrative actions, enforce fake AI or a
  verified global spend cap, enforce uploads and abuse limits, and verify authorization and audit.
- Supply environment-managed secrets, HTTPS, private service networking, persistent backups,
  recovery and operational controls. Review SeaweedFS configuration and pin an appropriate image.
- Resolve or explicitly renew the [release-gate exception](security-exceptions.md), obtain actual
  remote CI and ZAP evidence, rerun the full suite and E2E, address the failed default build,
  overall coverage target and valid mutmut/survivor review. Verify no secrets in Git history.
- Complete or accurately disclose outstanding Phase 11 usability and external reviewer work;
  retain synthetic demo disclaimers and `requires_clinician_approval`.

A synthetic local development deployment is running on localhost. Public deployment requires the
safety paths and checks above. Phase 12 remains incomplete; no public deployment has occurred.
