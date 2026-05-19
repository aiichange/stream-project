# Project Workflow and Setup

This file documents how to set up, run, and stop the Stock Market Intelligence Data Pipeline locally.

## Prerequisites

- Python 3.11+
- Git
- GitHub CLI (`gh`) if using GitHub from the terminal
- Google Cloud SDK (`gcloud`)
- Terraform 1.3+
- VS Code (recommended)

## Local environment setup

```powershell
# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
gcloud config set project ga4bigquery-431504

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r data_generation/requirements.txt
pip install -r dataflow/requirements.txt
```

## Running the full pipeline (4 terminals)

### Terminal 1 — Submit Dataflow streaming pipeline (stock prices)

```powershell
python dataflow/streaming_pipeline.py `
  --project ga4bigquery-431504 --region asia-south1 `
  --input_topic projects/ga4bigquery-431504/topics/stock-prices-topic `
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence `
  --output_table stream_stock_prices `
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp `
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging `
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2 `
  --job_name "stream-stock-prices-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

This submits the job to GCP Dataflow and exits. The streaming job continues running in the cloud.

### Terminal 2 — Submit Dataflow factor pipeline (live market factors)

```powershell
python dataflow/factor_pipeline.py `
  --project ga4bigquery-431504 --region asia-south1 `
  --input_topic projects/ga4bigquery-431504/topics/market-factors-topic `
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence `
  --output_table live_market_factors `
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp `
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging `
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2 `
  --job_name "factor-pipeline-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### Terminal 3 — Start stock price publisher

```powershell
python data_generation/yahoo_publish.py `
  --project ga4bigquery-431504 --topic stock-prices-topic --interval 30
```

Publishes live Yahoo Finance quotes for 8 tickers every 30 seconds. Ctrl+C to stop.

### Terminal 4 — Start market factor publisher

```powershell
python data_generation/factor_publish.py `
  --project ga4bigquery-431504 --topic market-factors-topic --interval 120
```

Publishes live market factors (crude oil, FX, weather, AQI, inflation, interest) for 6 sectors every 120 seconds. Ctrl+C to stop.

## Running the batch pipeline (one-time or daily)

```powershell
# Step 1: Generate and upload raw CSV (113 rows with 13 dirty rows)
python data_generation/synthetic_batch_generator.py `
  --project ga4bigquery-431504 `
  --bucket stock-intel-batch-landing-asia-south1 --upload --dirty

# Step 2: Clean the CSV (drops dirty rows, outputs 100 clean rows to GCS)
python data_generation/etl_clean.py `
  --project ga4bigquery-431504 `
  --input gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv `
  --output gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv

# Step 3: Load into BigQuery via Dataflow batch job
python dataflow/batch_pipeline.py `
  --project ga4bigquery-431504 --region asia-south1 `
  --input gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv `
  --output_project ga4bigquery-431504 --output_dataset stock_intelligence `
  --output_table batch_market_factors `
  --temp_location gs://stock-intel-batch-landing-asia-south1/temp `
  --staging_location gs://stock-intel-batch-landing-asia-south1/staging `
  --runner DataflowRunner --worker_zone asia-south1-b --machine_type e2-standard-2
```

## Stopping everything

```powershell
# Publishers (Terminal 3 and 4): Ctrl+C in each terminal

# List active Dataflow jobs
gcloud dataflow jobs list --region=asia-south1 --project=ga4bigquery-431504

# Cancel a specific streaming job
gcloud dataflow jobs cancel JOB_ID --region=asia-south1 --project=ga4bigquery-431504
```

Note: Dataflow streaming jobs run indefinitely in GCP even after the local Python submit process exits. Always cancel them explicitly.

## Querying results in BigQuery

```sql
-- Live enriched view (real factor data only, INNER JOIN)
SELECT * FROM `ga4bigquery-431504.stock_intelligence.stock_live_factor_view`
WHERE price > 0 ORDER BY timestamp DESC LIMIT 50;

-- Full analysis view (live factors preferred, batch as fallback, LEFT JOINs)
SELECT * FROM `ga4bigquery-431504.stock_intelligence.stock_factor_analysis_view`
WHERE price > 0 ORDER BY timestamp DESC LIMIT 50;

-- Raw streaming stock prices
SELECT * FROM `ga4bigquery-431504.stock_intelligence.stream_stock_prices`
WHERE price > 0 ORDER BY timestamp DESC LIMIT 50;

-- Raw live market factors
SELECT * FROM `ga4bigquery-431504.stock_intelligence.live_market_factors`
ORDER BY updated_at DESC LIMIT 50;
```

## Pub/Sub topics

| Topic | Publisher | Dataflow consumer |
|---|---|---|
| `stock-prices-topic` | `yahoo_publish.py` | `streaming_pipeline.py` |
| `market-factors-topic` | `factor_publish.py` | `factor_pipeline.py` |

## BigQuery tables and views

| Name | Type | Contents |
|---|---|---|
| `stream_stock_prices` | Table | Live stock price ticks |
| `live_market_factors` | Table | Live market factors from real APIs |
| `batch_market_factors` | Table | Batch synthetic market factors (cleaned) |
| `stock_factor_analysis_view` | View | stream + live (preferred) + batch (fallback) |
| `stock_live_factor_view` | View | stream + live only (no batch fallback) |

## Git and GitHub workflow

```powershell
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/<short-description>

# After making changes
git add <specific-files>
git commit -m "your message"
git push -u origin feature/<short-description>
# Open PR into develop on GitHub
```

## Environment variables

`yahoo_publish.py` optionally reads `PROJECT_ID`, `PUBSUB_TOPIC`, and `PUBLISH_INTERVAL` from a `.env` file (via `python-dotenv`). Command-line arguments take precedence. All other scripts use only command-line arguments.

## GCP configuration reference

| Setting | Value |
|---|---|
| Project | `ga4bigquery-431504` |
| Region | `asia-south1` (Mumbai) |
| Worker zone | `asia-south1-b` |
| Machine type | `e2-standard-2` |
| BigQuery dataset | `stock_intelligence` |
| GCS bucket | `stock-intel-batch-landing-asia-south1` |
| Pub/Sub topics | `stock-prices-topic`, `market-factors-topic` |
