# Security and reliability release-gate exceptions

No exception below is an approval, a claim of security certification, or permission to use real
patient data. Each must be closed or explicitly renewed before a public-demo release.

| Exception | Owner | Impact | Compensating control | Expiry |
| --- | --- | --- | --- | --- |
| Remote Phase 10 CI has not run for this unpushed worktree. | Demo maintainer | Local scanner evidence cannot establish that the GitHub Actions secret scan or Linux CI execution will pass. | The checked-in workflow runs locked Python audit, production npm audit, Gitleaks, bounded public-endpoint Schemathesis, and a ZAP baseline. Review the actual remote run before any public-demo release. | 2026-12-05 |

## Remote CI update (2026-11-05)

GitHub Actions run [42055119530](https://github.com/hemanthreddy-gif/RPM-Platform/actions/runs/42055119530)
for commit `83b930e` completed the configured dependency, secret, public-endpoint fuzz and ZAP
baseline steps successfully. The exception above was specific to the absence of remote CI evidence
and is closed for that revision. It does not resolve the remaining public-demo controls, coverage,
mutation evidence, or clinical and usability review gaps documented in [progress](PROGRESS.md).
