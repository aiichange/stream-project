# Stock Market Intelligence Data Pipeline — Development Notes

## Purpose

Build a production-oriented GCP data engineering solution that combines:
- near-real-time stock price ingestion from Yahoo Finance via Pub/Sub
- live market factor ingestion from free public APIs via a second Pub/Sub topic
- streaming processing through Dataflow (Apache Beam)
- batch environmental/economic feature generation and batch ETL
- unified storage and analytics in BigQuery with enriched joined views

The goal is to analyze how external factors (weather, crude oil price, USD-INR rate, inflation, interest rate, AQI, news sentiment, geo-risk) influence stock price movement across sectors.

## Current Architecture (as built)

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

## What Was Built

### 1. Streaming Stock Price Pipeline

- `data_generation/yahoo_publish.py` — publishes live Yahoo Finance quotes to `stock-prices-topic` every 30s
  - Fixed: `fast_info` uses attribute access (`last_price`, `day_high`, `day_low`, `last_volume`) not dict `.get()`
  - Covers 8 tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, RELIANCE.NS, TCS.NS, INFY.NS
- `dataflow/streaming_pipeline.py` — Beam streaming job: reads Pub/Sub → writes `stream_stock_prices` BigQuery table
  - Fixed: `GoogleCloudOptions` view for `project`/`region` assignment (replaced broken `PipelineOptions.project`)

### 2. Live Market Factor Pipeline (new in this session)

- `data_generation/factor_publish.py` — publishes real market factors to `market-factors-topic` every 120s
  - Crude oil (`CL=F`), USD/INR (`USDINR=X`), VIX geo-risk proxy via yfinance
  - Sector sentiment: ETF daily % change × 10, clamped to [-1, 1] (QQQ, XLE, XLF, XLV, XLY, XLB)
  - Weather score and AQI: Open-Meteo API (Mumbai lat=19.076, lon=72.877) — no API key required
  - Inflation rate + interest rate: World Bank API (India CPI `FP.CPI.TOTL.ZG`, lending rate `FR.INR.LEND`) — cached since annual
  - Six sectors published per cycle: Technology, Energy, Financials, Healthcare, Consumer Discretionary, Materials
- `dataflow/factor_pipeline.py` — Beam streaming job: reads Pub/Sub → writes `live_market_factors` BigQuery table

### 3. Batch Market Factor Pipeline

- `data_generation/synthetic_batch_generator.py` — generates 113 rows of synthetic market factor CSV (with 13 dirty rows intentionally)
- `data_generation/etl_clean.py` — Python ETL: reads raw CSV from GCS, drops dirty rows (missing factor_date/region/sector), writes 100 clean rows to GCS
  - Replaces Cloud Data Fusion Wrangler entirely (see Lessons Learned)
- `dataflow/batch_pipeline.py` — Beam batch job: reads cleaned CSV from GCS → writes `batch_market_factors` BigQuery table
  - Fixed: `fieldnames=FIELD_NAMES` passed to `csv.DictReader` (bug: reader was treating first data row as headers)
  - Fixed: `GoogleCloudOptions` for project/region (same as streaming pipeline)

### 4. BigQuery Analytical Views

- `stock_factor_analysis_view` — COALESCE live over batch fallback; LEFT JOINs both factor tables
  - Query: `SELECT * FROM stock_intelligence.stock_factor_analysis_view WHERE price > 0 ORDER BY timestamp DESC`
- `stock_live_factor_view` — INNER JOIN stream prices + live factors only; shows only real-data rows
  - Query: `SELECT * FROM stock_intelligence.stock_live_factor_view WHERE price > 0 ORDER BY timestamp DESC`
  - Both views de-duplicate live factors with `ROW_NUMBER() OVER (PARTITION BY sector, factor_date ORDER BY updated_at DESC)`

### 5. Infrastructure

- `infra/terraform/` — Terraform IaC for all GCP resources
- GCP project: `ga4bigquery-431504`, region: `asia-south1` (Mumbai), worker zone: `asia-south1-b`
- IAM: Dataflow worker SA `687354937520-compute@developer.gserviceaccount.com` has `dataflow.worker`, `bigquery.jobUser`, `bigquery.dataEditor`, `storage.objectAdmin`, `pubsub.editor`

## Lessons Learned

### Cloud Data Fusion Wrangler bypass

CDAP Wrangler v4.11.1 cannot handle nullable union types (`["null","string"]` in Avro schema). The Studio UI accepted the pipeline definition but Wrangler produced empty output CSV — zero rows written. After extensive debugging (schema inspection, null handling directives, output format changes), we replaced the entire Data Fusion ETL stage with `data_generation/etl_clean.py`, a simple Python script that does the same job reliably. The Data Fusion instance is still provisioned by Terraform but is not used in the active pipeline.

### yfinance fast_info attribute access

`yf.Ticker().fast_info` returns a `FastInfo` object, not a dict. Calling `.get("regularMarketPrice")` returns `None` silently. The correct pattern is `getattr(fast_info, "last_price", None)`. This caused `price=0.0` in all early BigQuery rows. Since BigQuery `WRITE_APPEND` keeps old rows, filter with `WHERE price > 0` to exclude pre-fix data.

### Dataflow IAM permissions

The Compute Engine default service account needs explicit roles for Dataflow jobs to run:
- `roles/dataflow.worker` — for Dataflow worker control-plane operations
- `roles/bigquery.jobUser` + `roles/bigquery.dataEditor` — for writing to BigQuery
- `roles/storage.objectAdmin` — for temp/staging bucket access
- `roles/pubsub.editor` — for Pub/Sub subscription creation and reads

### Worker zone exhaustion

`asia-south1-a` frequently hits `ZONE_RESOURCE_POOL_EXHAUSTED`. Always use `--worker_zone asia-south1-b --machine_type e2-standard-2` for all Dataflow jobs.

### Streaming Dataflow jobs never exit

Once submitted, a Dataflow streaming job runs indefinitely in GCP. The local Python process that submits it can be Ctrl+C'd safely — the cloud job continues. To stop it: `gcloud dataflow jobs cancel JOB_ID --region=asia-south1 --project=ga4bigquery-431504`.

### Two Pub/Sub subscriptions per topic

When `ReadFromPubSub(topic=...)` is used in Beam (topic-based, not subscription-based), Dataflow auto-creates a subscription named `<topic>.subscription-<random-id>`. The manually pre-created `stock-prices-sub` subscription is separate and still exists. Both subscriptions receive independent message copies — the Dataflow-created one feeds the pipeline.

### Windows encoding on Windows terminals

Python source files with Unicode characters (`→`, `°C`, `≈`) cause `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows terminals using cp1252 encoding. Replace with ASCII equivalents (`->`, `C`, `~`) in all print statements.

## Production Deployment Strategy (to implement)

### Phase 1 — Visualization (Looker Studio)
Connect `stock_factor_analysis_view` and `stock_live_factor_view` directly to Looker Studio (formerly Data Studio). Free, no infrastructure needed. Charts for price trends, factor correlations, sector breakdowns.

### Phase 2 — Publisher Automation (Cloud Run)
Move `yahoo_publish.py` and `factor_publish.py` to containerized Cloud Run jobs on a schedule. Eliminates the need for a local machine to stay running.

### Phase 3 — Batch Scheduling (Cloud Workflows or Cloud Scheduler)
Automate the daily batch cycle: `synthetic_batch_generator.py` → `etl_clean.py` → `batch_pipeline.py` triggered by Cloud Scheduler via Cloud Workflows or a Cloud Run job.

### Phase 4 — Custom Dashboard (Cloud Run + React + FastAPI)
REST API (FastAPI on Cloud Run) querying BigQuery views. React frontend with Recharts/Chart.js for live stock + factor charts. Authenticate with Firebase Auth or IAP.

### Phase 5 — Alerting (Cloud Monitoring)
Alert policies on Dataflow job failures, Pub/Sub message backlog, BigQuery row count anomalies. PagerDuty or email notification channels.

## Project files summary

| Path | Purpose |
|---|---|
| `infra/terraform/` | Terraform IaC for all GCP resources |
| `data_generation/synthetic_batch_generator.py` | Generates synthetic batch CSV with dirty rows |
| `data_generation/etl_clean.py` | Python ETL: cleans raw CSV, writes to GCS (replaces Data Fusion) |
| `data_generation/yahoo_publish.py` | Publishes live stock prices to Pub/Sub via yfinance |
| `data_generation/factor_publish.py` | Publishes live market factors (crude oil, FX, weather, AQI, macro) |
| `dataflow/batch_pipeline.py` | Apache Beam batch job: GCS CSV → BigQuery |
| `dataflow/streaming_pipeline.py` | Apache Beam streaming: Pub/Sub stock prices → BigQuery |
| `dataflow/factor_pipeline.py` | Apache Beam streaming: Pub/Sub market factors → BigQuery |
| `datafusion/` | Cloud Data Fusion reference (superseded by etl_clean.py) |
| `README.md` | Project overview, architecture, quick start commands |
| `WORKFLOW.md` | Local setup, run commands, stop commands |
| `development.md` | Architecture decisions, what was built, lessons learned |
| `process-github.md` | GitHub branch strategy, PR workflow, CI/CD |
| `production-setup-report.md` | CI/CD pipeline details and production deployment strategy |
