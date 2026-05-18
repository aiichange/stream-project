# Stock Market Intelligence Data Pipeline

This project implements a production-style Google Cloud data engineering pipeline for near-real-time stock price analysis enriched with batch environmental and market-impact data.

## Architecture

- **Streaming ingestion:** Yahoo Finance price updates are published to Pub/Sub.
- **Streaming processing:** Dataflow (Apache Beam) consumes Pub/Sub and writes stock records to BigQuery.
- **Batch generation:** Python generates a synthetic batch dataset of environmental, economic, sentiment, and risk factors.
- **Batch landing:** Batch CSV is written to Cloud Storage.
- **Batch ETL:** Cloud Data Fusion cleans and normalizes the batch data, writing a transformed CSV back to Cloud Storage.
- **Batch processing:** Dataflow batch job loads transformed batch data into BigQuery.
- **Analytics:** BigQuery joins streaming and batch datasets for sector-based analysis.

## Components

- `infra/terraform/` — Terraform configuration for Pub/Sub, GCS, BigQuery, IAM, and Data Fusion.
- `data_generation/` — Python scripts for synthetic batch data generation and Yahoo Finance Pub/Sub publishing.
- `dataflow/` — Apache Beam streaming and batch pipelines.
- `datafusion/` — Data Fusion ETL guidance for the batch pipeline.
- `CONTRIBUTING.md` — contribution guidelines and repository standards.
- `WORKFLOW.md` — local setup, deployment, and environment workflows.

## GCP Configuration

- Project: `ga4bigquery-431504`
- Region: `asia-south1`
- Preferred dataset: `stock_intelligence`

## Quick Start

1. Install dependencies and authenticate:
   - `gcloud auth login`
   - `gcloud config set project ga4bigquery-431504`
   - `gcloud auth application-default login`

2. Deploy infrastructure:
   - `cd infra/terraform`
   - `terraform init`
   - `terraform apply`

3. Generate batch data and upload to GCS:
   - `python ../data_generation/synthetic_batch_generator.py --project ga4bigquery-431504 --bucket stock-intel-batch-landing-asia-south1 --upload`

4. (Optional) Use a local Python virtual environment and `.env` file:
   - `python -m venv .venv`
   - `./.venv/Scripts/Activate.ps1`
   - `pip install -r ../data_generation/requirements.txt`
   - Copy `.env.example` to `.env` and customize values.

5. Run the Data Fusion ETL pipeline:
   - Follow `datafusion/README.md`

5. Run the Dataflow batch job:
   - `python ../dataflow/batch_pipeline.py --project ga4bigquery-431504 --region asia-south1 --input gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv --output-project ga4bigquery-431504 --output-dataset stock_intelligence --output-table batch_market_factors --temp_location gs://stock-intel-batch-landing-asia-south1/temp`

6. Start the near-real-time publisher and streaming Dataflow job:
   - `python ../data_generation/yahoo_publish.py --project ga4bigquery-431504 --topic stock-prices-topic --interval 60`
   - `python ../dataflow/streaming_pipeline.py --project ga4bigquery-431504 --region asia-south1 --input_topic projects/ga4bigquery-431504/topics/stock-prices-topic --output_project ga4bigquery-431504 --output_dataset stock_intelligence --output_table stream_stock_prices --temp_location gs://stock-intel-batch-landing-asia-south1/temp`

7. Analyze in BigQuery:
   - Use the view `stock_intelligence.stock_factor_analysis_view` for sector-level joins.

## Branching strategy

- Use `develop` for ongoing development and feature work.
- Use `master` for stable production-ready code.
- Create pull requests from `develop` to `master` when the pipeline is ready for release.

## CI/CD

- GitHub Actions workflows are configured in `.github/workflows/python-ci.yml`, `.github/workflows/terraform-pr.yml`, and `.github/workflows/gcp-deploy.yml`.
- `python-ci.yml` validates Python code, installs dependencies, runs Terraform init/validate, checks Terraform formatting, and performs a Checkov policy scan.
- `terraform-pr.yml` runs on pull requests targeting `develop` and `master` and validates Terraform configuration before merge.

## Continuous Deployment

- `gcp-deploy.yml` is the production deployment workflow.
- It runs on pushes to `master` and via manual dispatch.
- It authenticates to GCP using GitHub secrets, initializes Terraform, validates configuration, plans changes, and applies the plan.
- Recommended release flow:
  1. Develop in `develop` and feature branches.
  2. Run PR validation via `terraform-pr.yml`.
  3. Merge `develop` into `master` after review.
  4. Deploy from `master` with GitHub Actions.

## Notes

- The Data Fusion stage is included for batch ETL and produces a clean CSV for Dataflow.
- The streaming and batch datasets are joined by sector and date in the BigQuery view.
- This scaffold is designed for production-style GCP deployment with infrastructure as code and reusable Python pipelines.
