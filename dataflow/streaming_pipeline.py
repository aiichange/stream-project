import argparse
import json
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery


class ParsePubSubMessage(beam.DoFn):
    def process(self, element):
        if isinstance(element, bytes):
            element = element.decode("utf-8")
        try:
            record = json.loads(element)
        except json.JSONDecodeError:
            return

        yield {
            "symbol": record.get("symbol"),
            "timestamp": record.get("timestamp"),
            "price": float(record.get("price", 0.0) or 0.0),
            "open": float(record.get("open", 0.0) or 0.0),
            "high": float(record.get("high", 0.0) or 0.0),
            "low": float(record.get("low", 0.0) or 0.0),
            "volume": int(record.get("volume", 0) or 0),
            "sector": record.get("sector"),
            "exchange": record.get("exchange"),
            "ingestion_time": record.get("ingestion_time") or datetime.utcnow().isoformat() + "Z",
        }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Dataflow streaming pipeline for stock prices")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", required=True, help="GCP region")
    parser.add_argument("--input_topic", required=True, help="Pub/Sub topic path")
    parser.add_argument("--output_project", required=True, help="BigQuery output project")
    parser.add_argument("--output_dataset", required=True, help="BigQuery output dataset")
    parser.add_argument("--output_table", required=True, help="BigQuery output table")
    parser.add_argument("--temp_location", required=True, help="GCS temp location")
    parser.add_argument("--staging_location", required=True, help="GCS staging location")
    args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).streaming = True
    pipeline_options.view_as(StandardOptions).runner = "DataflowRunner"
    pipeline_options.view_as(PipelineOptions).project = args.project
    pipeline_options.view_as(PipelineOptions).region = args.region
    pipeline_options.view_as(PipelineOptions).temp_location = args.temp_location
    pipeline_options.view_as(PipelineOptions).staging_location = args.staging_location

    table_spec = f"{args.output_project}:{args.output_dataset}.{args.output_table}"
    table_schema = {
        "fields": [
            {"name": "symbol", "type": "STRING", "mode": "REQUIRED"},
            {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
            {"name": "price", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "open", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "high", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "low", "type": "FLOAT", "mode": "NULLABLE"},
            {"name": "volume", "type": "INT64", "mode": "NULLABLE"},
            {"name": "sector", "type": "STRING", "mode": "NULLABLE"},
            {"name": "exchange", "type": "STRING", "mode": "NULLABLE"},
            {"name": "ingestion_time", "type": "TIMESTAMP", "mode": "NULLABLE"},
        ]
    }

    with beam.Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(topic=args.input_topic)
            | "ParseMessage" >> beam.ParDo(ParsePubSubMessage())
            | "WriteToBigQuery" >> WriteToBigQuery(
                table_spec,
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    run()
