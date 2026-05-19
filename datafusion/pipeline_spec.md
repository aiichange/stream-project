# Cloud Data Fusion Pipeline Specification

> **Status: Superseded**
> The Cloud Data Fusion Wrangler ETL described in this file has been replaced by
> `data_generation/etl_clean.py` — a Python script that performs the same cleaning
> (drop rows missing `factor_date`, `region`, or `sector`) and outputs the cleaned
> CSV to GCS. The Data Fusion instance is still provisioned by Terraform but is not
> used in the active pipeline.
>
> See [etl_clean.py](../data_generation/etl_clean.py) for the active ETL implementation.

---

## Original specification (reference only)

### Pipeline name

`stock_market_factors_etl`

### Stages

1. **GCS Source**
   - Plugin: Google Cloud Storage
   - Path: `gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv`
   - Format: CSV
   - Header row: true

2. **Wrangler / Transform**
   - Clean missing values.
   - Ensure numeric fields are cast to `FLOAT` or `INT`.
   - Ensure `factor_date` is cast to `DATE`.
   - Optionally normalize `weather_score`, `news_sentiment`, and `demand_index`.

3. **GCS Sink**
   - Plugin: Google Cloud Storage
   - Output path: `gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv`
   - Format: CSV
   - Header row: true

### Why it was replaced

CDAP Wrangler v4.11.1 (the version in the provisioned Data Fusion instance) cannot handle
nullable union types in the Avro schema (`["null","string"]`). The Wrangler transform accepted
the pipeline definition but produced empty output — zero rows written — regardless of null-handling
directives added. After multiple attempts, the ETL was replaced with `etl_clean.py` which
processes 113 raw rows to 100 clean rows reliably without any Data Fusion dependency.
