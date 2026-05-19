# GitHub Process for Stock Market Intelligence Data Pipeline

## Overview

This file documents the GitHub workflow, branch strategy, CI/CD process, and role responsibilities.

## Branch strategy

| Branch | Purpose |
|---|---|
| `master` | Stable, production-ready — triggers `gcp-deploy.yml` on push |
| `develop` | Integration branch for ongoing work |
| `feature/*` | Short-lived branches off `develop` |

## Roles

### Admin / main developer

- Manage repository settings and GitHub secrets (`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`)
- Configure branch protection rules on `develop` and `master`
- Review and merge pull requests into `develop` and `master`
- Validate production deployment readiness before merging to `master`

### Developer / non-admin

- Work on `feature/*` branches off `develop`
- Set up `.venv` and run local validations before pushing
- Open pull requests into `develop`
- Ensure all CI checks pass before merge

## Local development workflow

```powershell
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/<short-description>

# Set up local environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r data_generation/requirements.txt
pip install -r dataflow/requirements.txt

# Make changes, then commit
git add <specific-files>
git commit -m "your message"
git push -u origin feature/<short-description>
# Open PR into develop on GitHub
```

## Pull request workflow

- Target branch: `develop`
- Required CI checks: `python-ci`, `terraform-pr`
- Required review: 1 approval
- Do not push directly to `develop` or `master`

## Merge and release workflow

1. Feature branches merge into `develop` after checks pass
2. PR from `develop` into `master` after integration testing
3. `master` push triggers `gcp-deploy.yml` (Terraform apply)

## CI/CD Workflows

### `python-ci.yml`

Runs on pushes and PRs to `develop` and `master`.
- Python dependency install
- Python syntax validation
- Terraform init, validate, format check
- Checkov security scan

### `terraform-pr.yml`

Runs on PRs to `develop` and `master`.
- Terraform init, validate, format check
- Checkov policy scanning

### `gcp-deploy.yml`

Runs on pushes to `master` and manual dispatch.
- GCP auth via Workload Identity Federation (`google-github-actions/auth@v2`)
- Terraform plan + apply

## GitHub Secrets

| Secret | Purpose |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Federation provider for keyless auth |
| `GCP_SERVICE_ACCOUNT` | GCP service account email for Terraform apply |

## Repository file inventory

| Path | Description |
|---|---|
| `infra/terraform/` | Terraform IaC for all GCP resources |
| `data_generation/synthetic_batch_generator.py` | Generates synthetic batch CSV |
| `data_generation/etl_clean.py` | Python ETL: cleans raw CSV for batch pipeline |
| `data_generation/yahoo_publish.py` | Publishes live stock prices to Pub/Sub |
| `data_generation/factor_publish.py` | Publishes live market factors to Pub/Sub |
| `dataflow/batch_pipeline.py` | Beam batch job: GCS -> BigQuery |
| `dataflow/streaming_pipeline.py` | Beam streaming: stock prices Pub/Sub -> BigQuery |
| `dataflow/factor_pipeline.py` | Beam streaming: market factors Pub/Sub -> BigQuery |
| `datafusion/` | Cloud Data Fusion reference (superseded by etl_clean.py) |
| `.github/workflows/python-ci.yml` | CI: lint and syntax check |
| `.github/workflows/terraform-pr.yml` | PR validation: Terraform + Checkov |
| `.github/workflows/gcp-deploy.yml` | CD: Terraform apply to GCP |
| `README.md` | Project overview and quick start |
| `WORKFLOW.md` | Run/stop commands for all pipelines |
| `development.md` | Architecture decisions and lessons learned |
| `production-setup-report.md` | CI/CD details and production deployment phases |
| `process-github.md` | This file — GitHub workflow and branch strategy |

## Branch protection (recommended settings)

- `develop` and `master`: require passing status checks (`python-ci`, `terraform-pr`)
- Require 1 review approval
- Restrict direct pushes to admins only
- `master`: additionally require linear history

## Deployment readiness checklist

- [ ] GitHub secrets configured (`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`)
- [ ] Branch protection enabled on `develop` and `master`
- [ ] All CI checks pass on `develop`
- [ ] Terraform plan reviewed before merging to `master`
- [ ] Dataflow streaming jobs manually verified running in GCP console
- [ ] BigQuery views returning data (`WHERE price > 0`)
