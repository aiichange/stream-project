import argparse
import csv

import apache_beam as beam
from apache_beam.options.pipeline_options import (
    PipelineOptions, GoogleCloudOptions, StandardOptions,
)
from apache_beam.io.gcp.bigquery import WriteToBigQuery

FIELD_NAMES = [
    "factor_date", "region", "sector", "weather_score", "crude_oil_price",
    "usd_inr_rate", "inflation_rate", "interest_rate", "aqi",
    "news_sentiment", "social_sentiment", "geo_risk", "supply_chain_risk",
    "demand_index", "batch_id",
]


class ParseCsvRow(beam.DoFn):
    def process(self, element):
        row = next(csv.DictReader([element], fieldnames=FIELD_NAMES))
        yield {
            "factor_date": row.get("factor_date"),
            "region": row.get("region"),
            "sector": row.get("sector"),
            "weather_score": float(row.get("weather_score") or 0.0),
            "crude_oil_price": float(row.get("crude_oil_price") or 0.0),
            "usd_inr_rate": float(row.get("usd_inr_rate") or 0.0),
            "inflation_rate": float(row.get("inflation_rate") or 0.0),
            "interest_rate": float(row.get("interest_rate") or 0.0),
            "aqi": int(float(row.get("aqi") or 0)),
            "news_sentiment": float(row.get("news_sentiment") or 0.0),
            "social_sentiment": float(row.get("social_sentiment") or 0.0),
            "geo_risk": float(row.get("geo_risk") or 0.0),
            "supply_chain_risk": float(row.get("supply_chain_risk") or 0.0),
            "demand_index": float(row.get("demand_index") or 0.0),
            "batch_id": row.get("batch_id"),
        }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Dataflow batch pipeline for market factor CSV to BigQuery")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", required=True, help="GCP region")
    parser.add_argument("--input", required=True, help="GCS input file path")
    parser.add_argument("--output_project", required=True, help="BigQuery output project")
    parser.add_argument("--output_dataset", required=True, help="BigQuery dataset")
    parser.add_argument("--output_table", required=True, help="BigQuery table name")
    parser.add_argument("--temp_location", required=True, help="GCS temp location")
    parser.add_argument("--staging_location", required=True, help="GCS staging location")
    args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    gcp_opts = pipeline_options.view_as(GoogleCloudOptions)
    gcp_opts.project = args.project
    gcp_opts.region = args.region
    gcp_opts.temp_location = args.temp_location
    gcp_opts.staging_location = args.staging_location
    pipeline_options.view_as(StandardOptions).runner = "DataflowRunner"

    table_spec = f"{args.output_project}:{args.output_dataset}.{args.output_table}"
    table_schema = {
        "fields": [
            {"name": "factor_date", "type": "DATE", "mode": "REQUIRED"},
            {"name": "region", "type": "STRING", "mode": "REQUIRED"},
            {"name": "sector", "type": "STRING", "mode": "REQUIRED"},
            {"name": "weather_score", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "crude_oil_price", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "usd_inr_rate", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "inflation_rate", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "interest_rate", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "aqi", "type": "INT64", "mode": "NULLABLE"},
            {"name": "news_sentiment", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "social_sentiment", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "geo_risk", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "supply_chain_risk", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "demand_index", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "batch_id", "type": "STRING", "mode": "NULLABLE"},
        ]
    }

    with beam.Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "ReadCsv" >> beam.io.ReadFromText(args.input, skip_header_lines=1)
            | "ParseCsv" >> beam.ParDo(ParseCsvRow())
            | "WriteToBigQuery" >> WriteToBigQuery(
                table_spec,
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    run()
