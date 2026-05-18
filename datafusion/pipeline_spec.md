# Cloud Data Fusion Pipeline Specification

This file documents the exact ETL shape for Cloud Data Fusion.

## Pipeline name

`stock_market_factors_etl`

## Stages

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
   - Output path: `gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv`
   - Format: CSV
   - Header row: true

## Output

The resulting clean file should be consumed by the Dataflow batch pipeline at:

`gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv`

## Notes

- Use the Data Fusion UI to validate the schema before running.
- If needed, export the pipeline JSON from the Data Fusion instance for version control.
