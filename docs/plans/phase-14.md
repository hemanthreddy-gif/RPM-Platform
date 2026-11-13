# Phase 14: Restricted Railway preview

Authorized 2026-11-06: user selected Railway and connected it, requesting completion and a URL.
Deploy a restricted synthetic research preview; the open-public release gate stays separate.

1. Inspect connected workspace, services, available source transport and existing release gaps.
2. Add a fail-closed HTTPS preview login, signed cookie and same-origin API proxy. Keep backend,
   PostgreSQL, Redis, worker and photos private; block hosted administration/provisioning routes.
3. Enforce hosted configuration and generated secrets. Separate migrations from the RLS runtime
   database login; keep fake AI and synthetic fixture notices. No production or real-patient data.
4. Build/test deployable images and permission boundaries, configure the dedicated Railway project,
   deploy the exact reviewed source and verify UI/API/worker/storage paths on the returned URL.
5. Record commands, service IDs, deployment result and remaining public-release limitations.

Project: 8a26c57f-4501-48da-a0a3-d8948fb9d3f0; environment: a329dd75-a1af-4bb0-8b9b-7079fed6ceb2.
No reset is exposed or scheduled. This preview contains only operator-authorized synthetic data.
No existing deployment or user data is replaced. Existing tsconfig.tsbuildinfo changes are preserved.
