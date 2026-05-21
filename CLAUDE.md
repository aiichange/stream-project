# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-grade GCP data engineering pipeline that ingests near-real-time stock prices from Yahoo Finance and enriches them with live market factors (crude oil, FX rates, weather, AQI, macro indicators). Uses Apache Beam on Dataflow for streaming/batch, BigQuery for analytics, and Pub/Sub for message ingestion.

**GCP Project:** `ga4bigquery-431504` | **Region:** `asia-south1` (Mumbai)

## Environment Setup

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows

pip install -r data_generation/requirements.txt
pip install -r dataflow/requirements.txt
cp .env.example .env                # fill in GCP credentials
```

Required `.env` variables: `PROJECT_ID`, `PUBSUB_TOPIC`, `PUBSUB_SUBSCRIPTION`, `GCS_BUCKET`, `BQ_DATASET`, `BQ_TABLE`, `PUBLISH_INTERVAL`, `REGION`.

## Common Commands

**Run publishers (each in a separate terminal):**
```bash
python data_generation/yahoo_publish.py       # stock prices every 30s
python data_generation/factor_publish.py      # market factors every 120s
```

**Submit Dataflow streaming jobs (submits to GCP then exits locally — job keeps running in cloud):**
```bash
python dataflow/streaming_pipeline.py
python dataflow/factor_pipeline.py
```

**Stop a running Dataflow job:**
```bash
gcloud dataflow jobs list --region=asia-south1
gcloud dataflow jobs cancel JOB_ID --region=asia-south1
```

**Run batch pipeline:**
```bash
python data_generation/synthetic_batch_generator.py   # generate + upload CSV to GCS
python data_generation/etl_clean.py                   # clean CSV (replaces Cloud Data Fusion)
python dataflow/batch_pipeline.py                     # load cleaned CSV -> BigQuery
```

**Syntax validation (what CI runs):**
```bash
python -m py_compile data_generation/yahoo_publish.py
python -m py_compile dataflow/streaming_pipeline.py
# repeat for each .py file
```

**Terraform:**
```bash
cd infra/terraform
terraform init
terraform plan -var="project_id=ga4bigquery-431504"
terraform apply -var="project_id=ga4bigquery-431504"
```

## Architecture

```
Publishers (local / Cloud Run in prod)
├── yahoo_publish.py      → stock-prices-topic     (Pub/Sub, every 30s)
└── factor_publish.py     → market-factors-topic   (Pub/Sub, every 120s)

Dataflow Streaming
├── streaming_pipeline.py → stream_stock_prices    (BigQuery table)
└── factor_pipeline.py    → live_market_factors    (BigQuery table)

Dataflow Batch (daily or on-demand)
├── synthetic_batch_generator.py  → GCS (raw CSV, 113 rows, 13 dirty)
├── etl_clean.py                  → GCS (cleaned CSV, 100 rows)
└── batch_pipeline.py             → batch_market_factors (BigQuery table)

BigQuery Analytical Views
├── stock_factor_analysis_view   (stream + live preferred, batch fallback via COALESCE)
└── stock_live_factor_view       (stream + live INNER JOIN, real data only)
```

**Data flow:** Publishers serialize to JSON → Pub/Sub topics → Dataflow Beam pipelines parse and write to BigQuery tables → SQL views join and de-duplicate for analysis.

**De-duplication in views** uses `ROW_NUMBER() OVER (PARTITION BY sector, factor_date ORDER BY updated_at DESC)` to keep the latest record per partition.

## Key Implementation Details

**yfinance `fast_info` usage:** Returns an object, not a dict. Use `getattr(info, 'field', default)` not `info.get('field')`. This caused a production bug — do not revert.

**Dataflow job submission:** Calling `pipeline.run()` submits the job to GCP and returns. The local Python process can exit (Ctrl+C is safe). The job runs indefinitely in the cloud until explicitly cancelled via `gcloud dataflow jobs cancel`.

**Dataflow options pattern:** Use `GoogleCloudOptions` for `project` and `region`, not `PipelineOptions` directly.

**Batch CSV pipeline:** `csv.DictReader` in `batch_pipeline.py` requires `fieldnames=FIELD_NAMES` explicitly — without it, the first data row is treated as headers, silently dropping a row.

**Windows terminal encoding:** Avoid Unicode characters (`→`, `°C`, `≈`) in `print()` statements; use ASCII equivalents. The publishers run locally on Windows before Cloud Run migration.

**ETL replaces Cloud Data Fusion:** `etl_clean.py` is the authoritative ETL step. `datafusion/` contains a reference pipeline config that is no longer used operationally (Cloud Data Fusion Wrangler had a bug with the batch CSV format).

## CI/CD

Three GitHub Actions workflows:

| Workflow | Trigger | Does |
|---|---|---|
| `python-ci.yml` | Push/PR to develop, master | `py_compile` all .py files, Terraform validate + fmt check, Checkov security scan |
| `terraform-pr.yml` | PR to develop, master | Terraform validate, fmt, Checkov |
| `gcp-deploy.yml` | Push to master / manual | GCP auth (Workload Identity), Terraform plan + apply |

**Required GitHub Secrets:** `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`

Checkov skip rules are in `.checkov.yaml` (CSEK encryption, VPC peering, SA user role, storage logging — all intentionally out of scope for this project).

## BigQuery Schema Summary

- **`stream_stock_prices`** — live ticks: `symbol, timestamp, price, open, high, low, volume, sector, exchange, ingestion_time`
- **`live_market_factors`** — live factors: `sector, factor_date, crude_oil, usd_inr, vix, weather_score, aqi, inflation_rate, lending_rate, etf_sentiment, updated_at`
- **`batch_market_factors`** — synthetic batch: same factor columns plus `region`

Table schemas are defined in `infra/terraform/bigquery.tf` — that is the source of truth, not the pipeline code.

## Tickers & Factor Sources

**Stock tickers (8):** `AAPL, GOOGL, MSFT, AMZN, TSLA, RELIANCE.NS, TCS.NS, INFY.NS`

**Live factor APIs:** yfinance (`CL=F` crude oil, `USDINR=X` FX, `^VIX`), Open-Meteo (weather/AQI for Mumbai), World Bank REST API (inflation, lending rate), sector ETFs for sentiment (daily % change clamped to `[-1, 1]`).
