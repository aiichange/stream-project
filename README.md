# Stock Market Intelligence Data Pipeline

A production-style GCP data engineering pipeline for near-real-time stock price analysis enriched with live and batch market factor data.

## Architecture

```
PUBLISHERS (local / Cloud Run in production)
├── yahoo_publish.py      → stock-prices-topic     (every 30s)
└── factor_publish.py     → market-factors-topic   (every 120s)

DATAFLOW STREAMING
├── streaming_pipeline.py → stream_stock_prices    (BigQuery)
└── factor_pipeline.py    → live_market_factors    (BigQuery)

DATAFLOW BATCH (run once or daily)
└── batch_pipeline.py     → batch_market_factors   (BigQuery)
      ↑ input: etl_clean.py output from GCS

BIGQUERY ANALYTICAL LAYER
├── stock_factor_analysis_view  — stream + live (preferred) + batch (fallback)
└── stock_live_factor_view      — stream + live only (real data only)
```

## Components

| Path | Purpose |
|---|---|
| `infra/terraform/` | Terraform IaC for all GCP resources |
| `data_generation/synthetic_batch_generator.py` | Generates synthetic batch CSV with dirty rows |
| `data_generation/etl_clean.py` | Python ETL: cleans raw CSV, writes to GCS |
| `data_generation/yahoo_publish.py` | Publishes live stock prices to Pub/Sub via yfinance |
| `data_generation/factor_publish.py` | Publishes live market factors (crude oil, FX, weather, AQI, macro) |
| `dataflow/batch_pipeline.py` | Apache Beam batch job: GCS CSV → BigQuery |
| `dataflow/streaming_pipeline.py` | Apache Beam streaming: Pub/Sub stock prices → BigQuery |
| `dataflow/factor_pipeline.py` | Apache Beam streaming: Pub/Sub market factors → BigQuery |
| `datafusion/` | Cloud Data Fusion ETL reference (superseded by etl_clean.py) |
| `WORKFLOW.md` | Local setup, run commands, stop commands |
| `development.md` | Architecture decisions, what was built, lessons learned |
| `process-github.md` | GitHub branch strategy, PR workflow, CI/CD |
| `production-setup-report.md` | CI/CD pipeline details and GitHub Actions setup |

## GCP Configuration

| Setting | Value |
|---|---|
| Project | `ga4bigquery-431504` |
| Region | `asia-south1` (Mumbai) |
| BigQuery dataset | `stock_intelligence` |
| GCS bucket | `stock-intel-batch-landing-asia-south1` |
| Pub/Sub topics | `stock-prices-topic`, `market-factors-topic` |

## Quick Start

### 1. Prerequisites
```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project ga4bigquery-431504
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r data_generation/requirements.txt
pip install -r dataflow/requirements.txt
```

### 2. Run Batch Pipeline (once or daily)
```powershell
# Generate and upload raw CSV
python data_generation/synthetic_batch_generator.py \
  --project ga4bigquery-431504 \
  --bucket stock-intel-batch-landing-asia-south1 --upload --dirty

# Clean the CSV
python data_generation/etl_clean.py \
  --project ga4bigquery-431504 \
  --input gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv \
  --output gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv

# Load into BigQuery
python dataflow/batch_pipeline.py \
  --project ga4bigquery-431504 --region asia-south1 \
  --input gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv \
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence \
  --output_table batch_market_factors \
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp \
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging \
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2
```

### 3. Run Streaming Pipelines (Terminal 1 — submit to Dataflow)
```powershell
python dataflow/streaming_pipeline.py \
  --project ga4bigquery-431504 --region asia-south1 \
  --input_topic projects/ga4bigquery-431504/topics/stock-prices-topic \
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence \
  --output_table stream_stock_prices \
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp \
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging \
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2 \
  --job_name "stream-stock-prices-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### 4. Run Factor Streaming Pipeline (Terminal 2 — submit to Dataflow)
```powershell
python dataflow/factor_pipeline.py \
  --project ga4bigquery-431504 --region asia-south1 \
  --input_topic projects/ga4bigquery-431504/topics/market-factors-topic \
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence \
  --output_table live_market_factors \
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp \
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging \
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2 \
  --job_name "factor-pipeline-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### 5. Start Publishers (Terminal 3 & 4)
```powershell
# Terminal 3 — stock prices
python data_generation/yahoo_publish.py \
  --project ga4bigquery-431504 --topic stock-prices-topic --interval 30

# Terminal 4 — market factors
python data_generation/factor_publish.py \
  --project ga4bigquery-431504 --topic market-factors-topic --interval 120
```

### 6. Stop Everything
```powershell
# Publishers: Ctrl+C in each terminal

# Dataflow jobs
gcloud dataflow jobs list --region=asia-south1 --project=ga4bigquery-431504
gcloud dataflow jobs cancel JOB_ID --region=asia-south1 --project=ga4bigquery-431504
```

### 7. Query BigQuery Views
```sql
-- Live enriched view (real data only)
SELECT * FROM `ga4bigquery-431504.stock_intelligence.stock_live_factor_view`
WHERE price > 0 ORDER BY timestamp DESC LIMIT 50;

-- Full view (live preferred, batch fallback)
SELECT * FROM `ga4bigquery-431504.stock_intelligence.stock_factor_analysis_view`
WHERE price > 0 ORDER BY timestamp DESC LIMIT 50;
```

## Branching Strategy

| Branch | Purpose |
|---|---|
| `master` | Stable, production-ready |
| `develop` | Integration branch for ongoing work |
| `feature/*` | Individual feature branches off `develop` |

## CI/CD

| Workflow | Trigger | Action |
|---|---|---|
| `python-ci.yml` | Push/PR to `develop`, `master` | Lint, syntax check, Terraform validate |
| `terraform-pr.yml` | PR to `develop`, `master` | Terraform plan + Checkov security scan |
| `gcp-deploy.yml` | Push to `master` or manual | Terraform apply to GCP |
