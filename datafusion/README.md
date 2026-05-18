# Cloud Data Fusion ETL for Batch Market Factors

This directory describes the Cloud Data Fusion ETL stage used for batch market factor processing.

## Objective

- Read the raw synthetic batch CSV from Cloud Storage.
- Normalize and clean feature columns.
- Write a cleaned batch file back to Cloud Storage.

## Recommended Data Fusion Pipeline

1. Create a new Data Fusion pipeline in the `stock-intel-data-fusion` instance.
2. Add a **Google Cloud Storage** source plugin.
   - Input path: `gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv`
   - Format: CSV
   - Header row: enabled
3. Add a **Wrangler** or **SQL Transform** plugin.
   - Normalize numeric columns.
   - Cast `factor_date` to `DATE`.
   - Ensure `sector` and `region` are populated.
   - Optionally generate derived risk scores.
4. Add a **Google Cloud Storage** sink plugin.
   - Output path: `gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv`
   - File format: CSV
   - Include header row.
5. Deploy and run the pipeline.

## Deployment Notes

- The Data Fusion instance is created in the `asia-south1` region.
- Use the pipeline job output `gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv` as the input for the Dataflow batch job.
- If you prefer automation, Data Fusion REST or CLI can import a pipeline JSON definition.
