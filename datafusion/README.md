# Cloud Data Fusion ETL for Batch Market Factors

> **Status: Superseded**
> The Cloud Data Fusion Wrangler pipeline described here has been replaced by
> `data_generation/etl_clean.py`. The active ETL flow is:
>
> ```
> synthetic_batch_generator.py  →  GCS (raw CSV)
>           ↓
>     etl_clean.py              →  GCS (cleaned CSV)
>           ↓
>     batch_pipeline.py         →  BigQuery batch_market_factors
> ```
>
> The Data Fusion instance (`stock-intel-data-fusion`) is still provisioned by Terraform
> for reference but is not used in the current pipeline.

---

## Original description (reference only)

### Objective

- Read the raw synthetic batch CSV from Cloud Storage.
- Normalize and clean feature columns.
- Write a cleaned batch file back to Cloud Storage.

### Recommended Data Fusion Pipeline

1. Create a new Data Fusion pipeline in the `stock-intel-data-fusion` instance.
2. Add a **Google Cloud Storage** source plugin.
   - Input path: `gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv`
   - Format: CSV
   - Header row: enabled
3. Add a **Wrangler** or **SQL Transform** plugin.
   - Drop rows with missing `factor_date`, `region`, or `sector`.
   - Cast numeric columns to `FLOAT` or `INT64`.
   - Cast `factor_date` to `DATE`.
4. Add a **Google Cloud Storage** sink plugin.
   - Output path: `gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv`
   - File format: CSV
   - Include header row.
5. Deploy and run the pipeline.

### Why Wrangler was bypassed

CDAP Wrangler v4.11.1 cannot handle nullable union types in the source Avro schema.
The pipeline runs without error but produces empty output (0 rows written).
`data_generation/etl_clean.py` performs the same cleaning in plain Python and is now the
authoritative ETL step.
