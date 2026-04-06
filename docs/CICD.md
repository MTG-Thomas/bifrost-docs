# CI/CD Pipeline

Bifrost Docs uses GitHub Actions for continuous integration and deployment.

## Overview

```
Push to main/PR
       │
       ▼
┌─────────────────┐
│  CI - Test &    │
│   Build         │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
Backend    Frontend
Checks     Checks
    │         │
    └────┬────┘
         │
    Build Images
         │
    Push to GHCR
         │
    E2E Tests
         │
    Security Scan
         │
         ▼
┌─────────────────┐
│  CD - Deploy    │
│                 │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Staging   Production
 (auto)    (manual)
```

## Workflows

### 1. CI - Test & Build (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual trigger (`workflow_dispatch`)

**Jobs:**

#### Backend Checks
- **Linting**: Ruff linter and formatter
- **Type Checking**: Pyright
- **Unit Tests**: pytest with coverage
- **Database**: Uses PostgreSQL and Redis services

#### Frontend Checks
- **TypeScript**: `tsc` compiler check
- **Linting**: ESLint
- **Build**: Production bundle build

#### Build & Push
- Builds Docker images for API and Client
- Pushes to GitHub Container Registry (GHCR)
- Tags: `latest`, branch name, short SHA

#### E2E Tests
- Runs Playwright tests against built images
- Uses Docker Compose test configuration

#### Security Scanning
- Trivy vulnerability scanner on images
- Results uploaded to GitHub Security tab

### 2. CD - Deploy (`.github/workflows/cd.yml`)

**Triggers:**
- Successful CI completion on `main`
- Manual trigger with environment selection

**Environments:**

#### Staging (Automatic)
- Deploys via SSH to staging server
- Pulls latest images from GHCR
- Runs database migrations
- Verifies deployment with health check

#### Production (Manual)
- Requires manual trigger via GitHub UI
- Deploys to Kubernetes cluster
- Updates image tags in deployments
- Waits for rollout to complete

## Local CI Checks

Run the same checks locally before pushing:

```bash
# Run all checks
./scripts/ci-check.sh

# Run specific checks
./scripts/ci-check.sh backend    # Backend only
./scripts/ci-check.sh frontend   # Frontend only
./scripts/ci-check.sh docker     # Docker build only
./scripts/ci-check.sh e2e        # E2E tests (requires dev env)
```

## Container Registry

Images are published to **GitHub Container Registry (GHCR)**:

```
ghcr.io/mtg-thomas/bifrost-docs-api:latest
ghcr.io/mtg-thomas/bifrost-docs-client:latest
```

### Pulling Images

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull images
docker pull ghcr.io/mtg-thomas/bifrost-docs-api:latest
docker pull ghcr.io/mtg-thomas/bifrost-docs-client:latest
```

## Deployment Configuration

### Required Secrets

For CI/CD to work, add these secrets in GitHub repository settings:

#### For Staging Deployment
- `STAGING_SSH_HOST`: Staging server IP/hostname
- `STAGING_SSH_USER`: SSH username
- `STAGING_SSH_KEY`: SSH private key (pem format)

#### For Production Deployment
- `KUBE_CONFIG`: Base64-encoded kubectl config
- `SLACK_WEBHOOK_URL`: (Optional) Slack notifications

### Docker Compose Override for GHCR

To use the CI-built images in production:

```yaml
# docker-compose.prod.yml
services:
  api:
    image: ghcr.io/mtg-thomas/bifrost-docs-api:latest
    
  client:
    image: ghcr.io/mtg-thomas/bifrost-docs-client:latest
    
  worker:
    image: ghcr.io/mtg-thomas/bifrost-docs-api:latest
```

Deploy:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Workflow Badges

Add to your README.md:

```markdown
![CI](https://github.com/MTG-Thomas/bifrost-docs/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/MTG-Thomas/bifrost-docs/actions/workflows/cd.yml/badge.svg)
```

## Troubleshooting

### CI Fails on Tests

Run tests locally to debug:
```bash
# Backend
cd api
pytest tests/unit -v

# Frontend
cd client
npm run test:e2e
```

### Docker Build Fails

Check Dockerfiles build locally:
```bash
docker build -t test-api ./api
docker build -t test-client ./client
```

### Deployment Fails

1. Check secrets are configured correctly
2. Verify SSH key has correct permissions (600)
3. Ensure server has Docker installed and running
4. Check disk space on target server

## Security Considerations

- **No secrets in code**: All secrets are GitHub Secrets
- **Least privilege**: Workflows use minimal required permissions
- **Image scanning**: Trivy scans for vulnerabilities on every build
- **SARIF uploads**: Security findings visible in GitHub Security tab
- **Non-root containers**: Docker images run as non-root user

## Future Improvements

- [ ] Add performance testing (k6/Locust)
- [ ] Add mutation testing
- [ ] Automated rollback on deployment failure
- [ ] Blue/green deployments
- [ ] Automated database backup before migration
- [ ] Integration with Sentry for error tracking
