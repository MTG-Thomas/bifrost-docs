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
    E2E Smoke / Full E2E
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

#### E2E Smoke Tests
- Runs the smoke-labeled Playwright specs against built images
- Non-blocking while fixture drift is stabilized
- Intended to become deploy-blocking once reliable

#### Full E2E Tests
- Runs the broader Playwright/Docker Compose test suite
- Remains non-blocking while historical fixture drift is resolved

#### Security Scanning
- Trivy vulnerability scanner on images
- Results uploaded to GitHub Security tab
- Repository scan runs on PRs and `main`; image scans run after CI image build
- Fixed HIGH/CRITICAL image vulnerabilities fail the security job

### 2. SonarQube (`.github/workflows/sonar.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual trigger (`workflow_dispatch`)

The workflow uses `sonar-project.properties` and is ready for SonarCloud by default. It skips cleanly until `SONAR_TOKEN` is added as a repository secret. Set repository variable `SONAR_HOST_URL` only if using a non-default SonarQube server URL.

### 3. CD - Deploy Test VM (`.github/workflows/cd.yml`)

**Triggers:**
- Successful CI completion on `main`
- Manual trigger with optional commit SHA/ref

Manual deploys expect that CI has already published the matching short-SHA images.

**Environments:**

#### Bifrost Docs Dev (Automatic)
- Connects the GitHub-hosted runner to NetBird
- Deploys over SSH to `bifrost-docs-dev`
- Uses the CI-published short-SHA GHCR image tags, not mutable `latest`
- Uses an isolated checkout at `/home/thomas/deploy/bifrost-docs-main`
- Preserves the VM's existing `.env` and Garage config from `/home/thomas/workspace/bifrost-docs`
- Runs Docker Compose with `docker-compose.yml`, `docker-compose.test-vm.yml`, and `docker-compose.ssl.yml`
- Uses Compose project `bifrost-docs-dev` to upgrade the existing test VM stack and reuse its data volumes
- Uses GitHub Environment `bifrost-docs-dev`
- Verifies `https://dev.docs.midtowntg.com/health`

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

#### For Test VM Deployment
- `NETBIRD_SETUP_KEY`: Setup key that lets the GitHub runner join the NetBird network
- `TEST_VM_SSH_KEY`: Private key authorized for `thomas@100.103.235.51`

Store deployment credentials as `bifrost-docs-dev` environment secrets when possible. Repository-level secrets remain compatible with the workflow during bootstrap. The workflow uses the built-in `GITHUB_TOKEN` for temporary GHCR pulls during the deploy job.

#### For SonarQube
- `SONAR_TOKEN`: SonarCloud/SonarQube token for project analysis

Optional repository variable:
- `SONAR_HOST_URL`: SonarQube server URL; defaults to `https://sonarcloud.io`

### Docker Compose Override for GHCR

To use the CI-built images in production:

```yaml
# docker-compose.test-vm.yml
services:
  api:
    image: ${BIFROST_DOCS_API_IMAGE}
    
  client:
    image: ${BIFROST_DOCS_CLIENT_IMAGE}
    
  worker:
    image: ${BIFROST_DOCS_API_IMAGE}
```

Deploy:
```bash
export BIFROST_DOCS_API_IMAGE=ghcr.io/mtg-thomas/bifrost-docs-api:<short-sha>
export BIFROST_DOCS_CLIENT_IMAGE=ghcr.io/mtg-thomas/bifrost-docs-client:<short-sha>
docker compose -p bifrost-docs-dev -f docker-compose.yml -f docker-compose.test-vm.yml -f docker-compose.ssl.yml pull
docker compose -p bifrost-docs-dev -f docker-compose.yml -f docker-compose.test-vm.yml -f docker-compose.ssl.yml up -d
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
- [x] Manual rollback runbook for redeploying a known-good image tag
- [ ] Blue/green deployments
- [ ] Automated database backup before migration
- [ ] Integration with Sentry for error tracking
