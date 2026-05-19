import argparse
import csv
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

SECTORS = [
    "Technology",
    "Financials",
    "Energy",
    "Consumer Discretionary",
    "Healthcare",
    "Industrials",
]

REGIONS = ["India", "United States", "Europe", "Asia Pacific"]

FIELD_NAMES = [
    "factor_date",
    "region",
    "sector",
    "weather_score",
    "crude_oil_price",
    "usd_inr_rate",
    "inflation_rate",
    "interest_rate",
    "aqi",
    "news_sentiment",
    "social_sentiment",
    "geo_risk",
    "supply_chain_risk",
    "demand_index",
    "batch_id",
]


def create_row(base_date, region, sector):
    return {
        "factor_date": base_date.strftime("%Y-%m-%d"),
        "region": region,
        "sector": sector,
        "weather_score": round(random.uniform(30.0, 95.0), 2),
        "crude_oil_price": round(random.uniform(60.0, 120.0), 2),
        "usd_inr_rate": round(random.uniform(70.0, 83.0), 2),
        "inflation_rate": round(random.uniform(3.5, 9.0), 2),
        "interest_rate": round(random.uniform(3.0, 8.0), 2),
        "aqi": random.randint(25, 250),
        "news_sentiment": round(random.uniform(-1.0, 1.0), 3),
        "social_sentiment": round(random.uniform(-1.0, 1.0), 3),
        "geo_risk": round(random.uniform(0.0, 1.0), 3),
        "supply_chain_risk": round(random.uniform(0.0, 1.0), 3),
        "demand_index": round(random.uniform(20.0, 120.0), 2),
        "batch_id": str(uuid.uuid4()),
    }


def create_dirty_rows(base_date):
    """Return 13 intentionally bad rows to test Wrangler filter-rows-on.

    Categories (all trigger filter-rows-on empty-or-null-columns):
    - 5 rows: empty factor_date  → dropped by Wrangler
    - 5 rows: empty region       → dropped by Wrangler
    - 3 rows: empty sector       → dropped by Wrangler

    Note: non-numeric type-cast errors cause hard Spark task failure in CDAP
    Wrangler (NumberFormatException is not routed to error port by default).
    Those require a #pragma on-error send-to-error directive to handle gracefully.
    """
    dirty = []
    region = random.choice(REGIONS)
    sector = random.choice(SECTORS)

    # empty factor_date
    for _ in range(5):
        row = create_row(base_date, random.choice(REGIONS), random.choice(SECTORS))
        row["factor_date"] = ""
        dirty.append(row)

    # empty region
    for _ in range(5):
        row = create_row(base_date, region, random.choice(SECTORS))
        row["region"] = ""
        dirty.append(row)

    # empty sector
    for _ in range(3):
        row = create_row(base_date, random.choice(REGIONS), sector)
        row["sector"] = ""
        dirty.append(row)

    random.shuffle(dirty)
    return dirty


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(rows)


def upload_to_gcs(project_id, bucket_name, source_file, destination_path):
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_filename(source_file)
    print(f"Uploaded {source_file} to gs://{bucket_name}/{destination_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic batch market factor data")
    parser.add_argument("--project", default=None, help="GCP project ID")
    parser.add_argument("--bucket", default=None, help="Cloud Storage bucket name")
    parser.add_argument("--rows", type=int, default=100, help="Number of synthetic rows")
    parser.add_argument("--output", default="batch_market_factors.csv", help="Local CSV output path")
    parser.add_argument("--upload", action="store_true", help="Upload the generated CSV to Cloud Storage")
    parser.add_argument("--destination", default=None, help="Destination path in GCS")
    parser.add_argument("--dirty", action="store_true", help="Append ~15 intentionally bad rows to test Wrangler")
    args = parser.parse_args()

    project_id = args.project or os.getenv("PROJECT_ID")
    bucket = args.bucket or os.getenv("BATCH_BUCKET")
    destination = args.destination or os.getenv("BATCH_INPUT_PATH", "batch/input/batch_market_factors.csv")

    if not project_id:
        parser.error("--project or PROJECT_ID environment variable is required")
    if not bucket:
        parser.error("--bucket or BATCH_BUCKET environment variable is required")

    base_date = datetime.now(timezone.utc).date() - timedelta(days=10)
    rows = []
    for index in range(args.rows):
        date = base_date + timedelta(days=index % 30)
        region = random.choice(REGIONS)
        sector = random.choice(SECTORS)
        rows.append(create_row(date, region, sector))

    if args.dirty:
        dirty = create_dirty_rows(base_date)
        rows.extend(dirty)
        random.shuffle(rows)
        print(f"Injected {len(dirty)} dirty rows (5 empty factor_date, 5 empty region, 3 empty sector)")

    write_csv(args.output, rows)
    print(f"Generated {len(rows)} total rows into {args.output}")

    if args.upload:
        upload_to_gcs(project_id, bucket, args.output, destination)
