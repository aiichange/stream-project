# Production CI/CD and Deployment Report

## Summary

This report documents the production-grade CI/CD improvements and the deployment roadmap for the Stock Market Intelligence Data Pipeline.

## CI/CD Workflows

### `python-ci.yml`

Triggered on pushes and PRs to `develop` and `master`.

- Install Python dependencies
- Python syntax validation (`py_compile`)
- Terraform init and validate
- Terraform format check
- Checkov security scan on Terraform configuration

### `terraform-pr.yml`

Triggered on pull requests to `develop` and `master`.

- Terraform init
- Terraform validate
- Terraform format check
- Checkov policy scanning

### `gcp-deploy.yml`

Triggered on pushes to `master` and manual dispatch.

- GCP authentication via `google-github-actions/auth@v2` using `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT`
- Terraform init
- Terraform validate and format check
- Terraform plan (saved as `tfplan`)
- Terraform apply (from saved plan)

## Deployment Flow

1. Develop in `feature/*` branches off `develop`
2. Open PR into `develop` — CI and Terraform PR validation run
3. Merge `develop` into `master` after review
4. `gcp-deploy.yml` automatically applies Terraform changes to GCP

## GitHub Secrets Required

| Secret | Description |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Federation provider |
| `GCP_SERVICE_ACCOUNT` | GCP service account email for deployment |

## Infrastructure Deployed (Terraform)

- Pub/Sub topics: `stock-prices-topic`, `market-factors-topic`
- Pub/Sub subscription: `stock-prices-sub`
- GCS bucket: `stock-intel-batch-landing-asia-south1` (with temp/, staging/, batch/ structure)
- BigQuery dataset: `stock_intelligence` with tables `stream_stock_prices`, `batch_market_factors`, `live_market_factors`
- BigQuery views: `stock_factor_analysis_view`, `stock_live_factor_view`
- Cloud Data Fusion instance: `stock-intel-data-fusion` (provisioned, not active)
- IAM bindings for Dataflow worker service account

## Production Deployment Strategy (to implement)

The current setup runs publishers (`yahoo_publish.py`, `factor_publish.py`) and submits Dataflow jobs manually from a local machine. The following phases move this to a fully managed production system.

### Phase 1 — Visualization (Looker Studio)

Connect `stock_factor_analysis_view` and `stock_live_factor_view` directly to Looker Studio (formerly Data Studio). Free, zero infrastructure.

- Charts: price trends over time, sector factor correlation heatmaps, AQI vs. stock movement
- Share dashboard link with stakeholders
- No code required — drag-and-drop in Looker Studio UI

### Phase 2 — Publisher Automation (Cloud Run Jobs)

Package `yahoo_publish.py` and `factor_publish.py` as Docker containers on Cloud Run Jobs triggered by Cloud Scheduler.

```
Cloud Scheduler (every 30s / 120s)
  → Cloud Run Job (yahoo_publish / factor_publish)
    → Pub/Sub topic
      → Dataflow streaming pipeline (already running)
        → BigQuery
```

- Eliminates the need for a local machine to stay running
- Each Cloud Run Job is stateless and auto-scales to zero between runs
- Dockerfile per publisher in `data_generation/`

### Phase 3 — Batch Scheduling (Cloud Workflows)

Automate the daily batch cycle using Cloud Workflows:

```
Cloud Scheduler (daily 02:00 IST)
  → Cloud Workflows
    → Cloud Run Job: synthetic_batch_generator.py (upload to GCS)
    → Cloud Run Job: etl_clean.py (GCS raw → GCS clean)
    → Cloud Run Job: batch_pipeline.py --runner DataflowRunner (submit batch Dataflow job)
    → Wait for Dataflow job completion
    → Notify via Cloud Monitoring
```

### Phase 4 — Custom Dashboard (Cloud Run + FastAPI + React)

REST API layer on Cloud Run querying BigQuery views. React frontend with live charts.

```
React (SPA hosted on Cloud Run or Firebase Hosting)
  → FastAPI (Cloud Run, min-instances=1)
    → BigQuery views
```

- Authentication: Firebase Auth or Identity-Aware Proxy (IAP)
- Charts: Recharts or Chart.js for price + factor time series
- Auto-refresh every 30s matching publisher interval

### Phase 5 — Alerting (Cloud Monitoring)

Alert policies on:
- Dataflow job failure or drain
- Pub/Sub message backlog > threshold
- BigQuery row count anomalies (no new rows in N minutes)
- Cloud Run job failure

Notification channels: email, PagerDuty, or Slack webhook.

## Files Added or Updated in This Session

| File | Change |
|---|---|
| `data_generation/yahoo_publish.py` | Fixed `fast_info` attribute access bug (price was 0.0) |
| `data_generation/factor_publish.py` | New — live market factor publisher (real APIs) |
| `data_generation/etl_clean.py` | New — Python ETL replacing Cloud Data Fusion Wrangler |
| `dataflow/batch_pipeline.py` | Fixed CSV fieldnames and GoogleCloudOptions bugs |
| `dataflow/streaming_pipeline.py` | Fixed GoogleCloudOptions bug |
| `dataflow/factor_pipeline.py` | New — Dataflow streaming pipeline for live market factors |
| `datafusion/pipeline_spec.md` | Updated — marked superseded by etl_clean.py |
| `datafusion/README.md` | Updated — marked superseded by etl_clean.py |
| `README.md` | Rewritten — reflects full current architecture |
| `WORKFLOW.md` | Rewritten — all 4 pipeline run/stop commands |
| `development.md` | Rewritten — what was built and lessons learned |
| `production-setup-report.md` | Updated — production deployment phases added |
| `process-github.md` | Updated — reflects current file set |
