"""
Batch ETL: read raw CSV from GCS, drop dirty rows, cast types, write cleaned CSV back.
Replaces the Data Fusion Wrangler step.

Usage:
    python data_generation/etl_clean.py \
        --project ga4bigquery-431504 \
        --input  gs://stock-intel-batch-landing-asia-south1/batch/input/batch_market_factors.csv \
        --output gs://stock-intel-batch-landing-asia-south1/batch/etl-output/market_factors_cleaned.csv
"""

import argparse
import csv
import io
import sys

from google.cloud import storage

NUMERIC_FLOAT = [
    "weather_score", "crude_oil_price", "usd_inr_rate",
    "inflation_rate", "interest_rate",
    "news_sentiment", "social_sentiment",
    "geo_risk", "supply_chain_risk", "demand_index",
]
NUMERIC_INT = ["aqi"]
REQUIRED = ["factor_date", "region", "sector"]


def _parse_gcs(uri):
    assert uri.startswith("gs://"), f"Expected gs:// URI, got: {uri}"
    parts = uri[5:].split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def read_gcs_csv(client, uri):
    bucket_name, blob_name = _parse_gcs(uri)
    blob = client.bucket(bucket_name).blob(blob_name)
    content = blob.download_as_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def write_gcs_csv(client, uri, rows, fieldnames):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    bucket_name, blob_name = _parse_gcs(uri)
    client.bucket(bucket_name).blob(blob_name).upload_from_string(
        buf.getvalue(), content_type="text/csv"
    )


def clean(rows):
    kept, dropped = [], 0
    for row in rows:
        # Drop rows missing any required dimension field
        if any(not row.get(f, "").strip() for f in REQUIRED):
            dropped += 1
            continue

        # Cast numeric fields; skip row if cast fails
        try:
            for f in NUMERIC_FLOAT:
                row[f] = float(row[f])
            for f in NUMERIC_INT:
                row[f] = int(float(row[f]))
        except (ValueError, TypeError):
            dropped += 1
            continue

        kept.append(row)

    return kept, dropped


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--input",   required=True, help="gs:// URI of raw CSV")
    parser.add_argument("--output",  required=True, help="gs:// URI for cleaned CSV")
    args = parser.parse_args()

    client = storage.Client(project=args.project)

    print(f"Reading  {args.input}")
    rows = read_gcs_csv(client, args.input)
    print(f"Input rows: {len(rows)}")

    cleaned, dropped = clean(rows)
    print(f"Kept: {len(cleaned)}  Dropped (dirty): {dropped}")

    if not cleaned:
        print("ERROR: no rows survived cleaning — aborting write.", file=sys.stderr)
        sys.exit(1)

    fieldnames = list(rows[0].keys())
    write_gcs_csv(client, args.output, cleaned, fieldnames)
    print(f"Written  {args.output}")
    print("ETL complete.")
