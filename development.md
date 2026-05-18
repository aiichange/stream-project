# Stock Market Intelligence Data Pipeline — Development Notes

## Purpose

Build a production-oriented GCP data engineering solution that combines:
- near-real-time stock price ingestion from Yahoo Finance,
- streaming processing through Pub/Sub and Dataflow,
- batch environmental, economic, sentiment, and risk feature generation,
- batch ETL via Cloud Data Fusion,
- unified storage and analytics in BigQuery.

The goal is to analyze how external factors such as weather, crude oil price, USD-INR rate, inflation, interest rate, AQI, news sentiment, social sentiment, geo-risk, supply chain risk, and demand index influence stock price movement across sectors.

## Architecture

1. **Streaming ingestion**
   - `data_generation/yahoo_publish.py` pulls Yahoo Finance quotes and publishes JSON messages to Pub/Sub.
   - `infra/terraform/pubsub.tf` defines a Pub/Sub topic and subscription.

2. **Streaming processing**
   - `dataflow/streaming_pipeline.py` implements an Apache Beam streaming job to read from Pub/Sub and write to BigQuery.
   - `infra/terraform/bigquery.tf` defines the `stream_stock_prices` table.

3. **Batch dataset generation**
   - `data_generation/synthetic_batch_generator.py` creates a synthetic CSV with at least 100 rows of environmental, economic, sentiment, and risk variables.
   - Generated data is uploaded to Cloud Storage for ETL.

4. **Batch ETL**
   - `infra/terraform/datafusion.tf` provisions a Cloud Data Fusion instance.
   - `datafusion/README.md` and `datafusion/pipeline_spec.md` describe the ETL pipeline from raw CSV in Cloud Storage to cleaned CSV output.

5. **Batch processing**
   - `dataflow/batch_pipeline.py` processes the cleaned batch CSV and writes it to BigQuery.
   - `infra/terraform/bigquery.tf` defines the `batch_market_factors` table.

6. **Analytics and joining**
   - A BigQuery view `stock_factor_analysis_view` is defined in Terraform to join streaming stock data and batch factor data by sector and date.

## Work executed so far

- Scaffolded the project in `c:\Users\er_si\Desktop\Google_ALL\stream-project`
- Created Terraform infrastructure definitions for:
  - GCP services enabling: Pub/Sub, Storage, BigQuery, Dataflow, Data Fusion, Compute, IAM
  - Pub/Sub topic and subscription
  - Cloud Storage bucket for batch data
  - BigQuery dataset and tables
  - Cloud Data Fusion instance
  - service account and IAM role bindings
- Implemented Python components for:
  - near-real-time Yahoo Finance Pub/Sub publishing
  - synthetic batch feature generation and Cloud Storage upload
- Implemented Apache Beam Dataflow pipelines for:
  - streaming stock data ingestion into BigQuery
  - batch CSV ingestion into BigQuery
- Added Data Fusion ETL guidance and pipeline specification
- Validated Python script syntax
- Added `.gitignore` for Python and Terraform artifacts

## Purpose of this work

- Establish a production-style GCP data pipeline with clear separation between streaming and batch paths.
- Enable analysis of market movements by enriching stock prices with external factor data.
- Use Terraform for infrastructure-as-code and Python/Beam for reproducible pipeline logic.
- Document the architecture and deployment process for future implementation and review.

## Next steps

1. Deploy GCP infrastructure:
   - `cd infra/terraform`
   - `terraform init`
   - `terraform apply`

2. Generate and upload the synthetic batch dataset:
   - `python data_generation/synthetic_batch_generator.py --project ga4bigquery-431504 --bucket stock-intel-batch-landing-asia-south1 --upload`

3. Build and run the Data Fusion ETL pipeline:
   - Follow `datafusion/README.md` and `datafusion/pipeline_spec.md`
   - Produce cleaned output at `gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv`

4. Execute the Dataflow batch job:
   - `python dataflow/batch_pipeline.py --project ga4bigquery-431504 --region asia-south1 --input gs://stock-intel-batch-landing-asia-south1/batch/etl/market_factors_cleaned.csv --output_project ga4bigquery-431504 --output_dataset stock_intelligence --output_table batch_market_factors --temp_location gs://stock-intel-batch-landing-asia-south1/temp --staging_location gs://stock-intel-batch-landing-asia-south1/staging`

5. Start the streaming pipeline:
   - `python data_generation/yahoo_publish.py --project ga4bigquery-431504 --topic stock-prices-topic --interval 60`
   - `python dataflow/streaming_pipeline.py --project ga4bigquery-431504 --region asia-south1 --input_topic projects/ga4bigquery-431504/topics/stock-prices-topic --output_project ga4bigquery-431504 --output_dataset stock_intelligence --output_table stream_stock_prices --temp_location gs://stock-intel-batch-landing-asia-south1/temp --staging_location gs://stock-intel-batch-landing-asia-south1/staging`

6. Validate analytics in BigQuery using the view:
   - `stock_intelligence.stock_factor_analysis_view`

## Project files summary

- `infra/terraform/` — infrastructure as code
- `data_generation/` — source and batch data generation
- `dataflow/` — streaming and batch Apache Beam pipelines
- `datafusion/` — ETL guidance and spec
- `README.md` — project overview and quick start
- `development.md` — development process and next steps
