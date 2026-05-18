# Project Workflow and Setup

This file documents the recommended workflow for setting up and running the Stock Market Intelligence Data Pipeline.

## Prerequisites

- Python 3.11+
- Git
- GitHub CLI (`gh`) if using GitHub from the terminal
- Google Cloud SDK (`gcloud`)
- Terraform 1.3+
- VS Code (recommended)
- Optional: VS Code extensions for Python, Pylance, GitHub, and Cloud Code

## Local environment setup

1. Clone the repository or use the existing project folder.
2. Create a virtual environment:
   - `python -m venv .venv`
3. Activate the virtual environment:
   - PowerShell: `.venv\Scripts\Activate.ps1`
   - CMD: `.venv\Scripts\activate.bat`
   - Bash: `source .venv/bin/activate`
4. Install dependencies:
   - `pip install -r data_generation/requirements.txt`
   - `pip install -r dataflow/requirements.txt`

## Environment variables

1. Copy `.env.example` to `.env`.
2. Customize values in `.env` as needed.
3. `.env` is ignored by Git and is safe for local secrets or configuration.

## Git and GitHub workflow

1. Initialize git if needed: `git init`
2. Add files: `git add .`
3. Commit: `git commit -m "Initial project scaffold"`
4. Create or connect a GitHub repo: `gh repo create <repo-name> --public --source=. --remote=origin --push`
5. Create and push a development branch:
   - `git checkout -b develop`
   - `git push -u origin develop`

## Branch strategy

- `develop` is the main development branch.
- `master` is the release branch for stable code.
- Work in feature branches off `develop` and open PRs into `develop`.
- Merge `develop` into `master` after review and validation.

## CI/CD

- GitHub Actions workflows are defined in `.github/workflows/python-ci.yml`, `.github/workflows/terraform-pr.yml`, and `.github/workflows/gcp-deploy.yml`.
- `python-ci.yml` validates Python code and runs Terraform init/validate, formatting, and a Checkov scan.
- `terraform-pr.yml` validates Terraform configuration on pull requests targeting `develop` and `master`.

## Continuous Deployment

- `gcp-deploy.yml` deploys infrastructure from `master`.
- It runs on pushes to `master` and supports manual workflow dispatch.
- The workflow authenticates with GitHub secrets and a GCP service account, then runs Terraform validate, plan, and apply.
- Recommended flow:
  1. Develop and test in feature branches off `develop`.
  2. Merge feature branches into `develop`.
  3. Run PR validation with `terraform-pr.yml`.
  4. Merge `develop` into `master`.
  5. Deploy from `master` with GitHub Actions.

## GitHub Secrets for deployment

- `GCP_PROJECT` — GCP project ID
- `GCP_SERVICE_ACCOUNT_KEY` — JSON service account credentials
- `GCP_REGION` — optional region for workflows

## Remote Terraform state (recommended)

- The repository now includes a GCS backend config in `infra/terraform/backend.tf`.
- The backend bucket is `stock-intel-terraform-state-asia-south1` and state is stored under `terraform/state`.
- Create the bucket before the first `terraform init` with:
  - `gsutil mb -l asia-south1 gs://stock-intel-terraform-state-asia-south1`
- Then run `terraform init` in `infra/terraform` to migrate local state to the remote backend.
- This enables shared Terraform state and safer team collaboration.

## Environment approval

- `gcp-deploy.yml` is configured to use the `production` environment.
- Enable environment protection in GitHub to require manual approval before deployment.

## GCP CLI setup and authentication

1. Install Google Cloud SDK.
2. Authenticate with Google Cloud:
   - `gcloud auth login`
   - `gcloud auth application-default login`
3. Set the active project and region:
   - `gcloud config set project ga4bigquery-431504`
   - `gcloud config set compute/region asia-south1`
4. Enable required APIs if not already enabled:
   - `gcloud services enable pubsub.googleapis.com bigquery.googleapis.com storage.googleapis.com dataflow.googleapis.com datafusion.googleapis.com compute.googleapis.com`

## Terraform deployment

1. Navigate to the infra folder: `cd infra/terraform`
2. Initialize Terraform: `terraform init`
3. Apply infrastructure changes: `terraform apply`

## Data generation and ETL flow

1. Generate synthetic batch data and upload to Cloud Storage:
   - `python data_generation/synthetic_batch_generator.py --project ga4bigquery-431504 --bucket stock-intel-batch-landing-asia-south1 --upload`
2. Create and run the Cloud Data Fusion pipeline to transform the batch CSV.
3. Run the Dataflow batch pipeline using the cleaned output CSV.
4. Start the streaming publisher and Dataflow streaming pipeline.

## Development notes

- Use `README.md` for high-level architecture and quick start.
- Use `development.md` for process notes and current status.
- Use `CONTRIBUTING.md` for contribution guidelines.
