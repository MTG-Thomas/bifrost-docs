# Security Policy

## Supported Branches

`main` is the supported branch for security fixes and dependency updates.

## Reporting a Vulnerability

Report suspected vulnerabilities privately to the Midtown Technology Group maintainers. Do not open a public issue or pull request with exploit details, credentials, tokens, customer data, or environment-specific secrets.

Include:

- affected component or path
- observed behavior and impact
- safe reproduction steps, if available
- any relevant logs with secrets removed

## Secrets and Sensitive Data

Never commit credentials, private keys, setup keys, customer data exports, `.env` files, database dumps, or generated production configuration. GitHub Actions secrets and environment secrets are the source of truth for CI/CD credentials.

Rotating a secret is preferred over trying to prove a leaked secret was not used. If a secret may have been exposed, revoke it, replace it, and document the rotation in the related issue or pull request.

## Dependency and Container Policy

Dependabot opens dependency update pull requests for GitHub Actions, the client npm workspace, and the API Python workspace. Human review is required for runtime, deployment, auth, cryptography, database, migration, and infrastructure dependency changes.

Trivy uploads repository findings to GitHub code scanning and blocks fixed HIGH/CRITICAL vulnerabilities in published API and client images. Repository misconfiguration findings are triaged separately before being made blocking.

## Pull Request Expectations

Security-sensitive changes should include:

- CI results
- relevant tests or an explicit test gap
- migration or rollback notes when runtime state changes
- confirmation that no secrets or customer data are included
