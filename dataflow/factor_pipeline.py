import argparse
import json

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery


class ParseFactorMessage(beam.DoFn):
    def process(self, element):
        if isinstance(element, bytes):
            element = element.decode("utf-8")
        try:
            r = json.loads(element)
        except json.JSONDecodeError:
            return

        def _f(v):
            return float(v) if v is not None else None

        def _i(v):
            return int(v) if v is not None else None

        yield {
            "factor_date":       r.get("factor_date"),
            "sector":            r.get("sector"),
            "updated_at":        r.get("updated_at"),
            "crude_oil_price":   _f(r.get("crude_oil_price")),
            "usd_inr_rate":      _f(r.get("usd_inr_rate")),
            "weather_score":     _f(r.get("weather_score")),
            "inflation_rate":    _f(r.get("inflation_rate")),
            "interest_rate":     _f(r.get("interest_rate")),
            "aqi":               _i(r.get("aqi")),
            "news_sentiment":    _f(r.get("news_sentiment")),
            "social_sentiment":  _f(r.get("social_sentiment")),
            "geo_risk":          _f(r.get("geo_risk")),
            "supply_chain_risk": _f(r.get("supply_chain_risk")),
            "demand_index":      _f(r.get("demand_index")),
        }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Dataflow streaming pipeline for live market factors")
    parser.add_argument("--project",          required=True)
    parser.add_argument("--region",           required=True)
    parser.add_argument("--input_topic",      required=True)
    parser.add_argument("--output_project",   required=True)
    parser.add_argument("--output_dataset",   required=True)
    parser.add_argument("--output_table",     required=True)
    parser.add_argument("--temp_location",    required=True)
    parser.add_argument("--staging_location", required=True)
    args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).streaming = True
    pipeline_options.view_as(StandardOptions).runner = "DataflowRunner"
    gcp_opts = pipeline_options.view_as(GoogleCloudOptions)
    gcp_opts.project          = args.project
    gcp_opts.region           = args.region
    gcp_opts.temp_location    = args.temp_location
    gcp_opts.staging_location = args.staging_location

    table_spec = f"{args.output_project}:{args.output_dataset}.{args.output_table}"
    table_schema = {
        "fields": [
            {"name": "factor_date",       "type": "DATE",      "mode": "REQUIRED"},
            {"name": "sector",            "type": "STRING",    "mode": "REQUIRED"},
            {"name": "updated_at",        "type": "TIMESTAMP", "mode": "REQUIRED"},
            {"name": "crude_oil_price",   "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "usd_inr_rate",      "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "weather_score",     "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "inflation_rate",    "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "interest_rate",     "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "aqi",               "type": "INT64",     "mode": "NULLABLE"},
            {"name": "news_sentiment",    "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "social_sentiment",  "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "geo_risk",          "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "supply_chain_risk", "type": "FLOAT",     "mode": "NULLABLE"},
            {"name": "demand_index",      "type": "FLOAT",     "mode": "NULLABLE"},
        ]
    }

    with beam.Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "ReadFromPubSub"  >> beam.io.ReadFromPubSub(topic=args.input_topic)
            | "ParseMessage"    >> beam.ParDo(ParseFactorMessage())
            | "WriteToBigQuery" >> WriteToBigQuery(
                table_spec,
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    run()
