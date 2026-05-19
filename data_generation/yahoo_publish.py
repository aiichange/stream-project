import argparse
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
import yfinance as yf
from google.cloud import pubsub_v1

load_dotenv()

DEFAULT_TICKERS = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
]

SECTOR_MAP = {
    "AAPL": "Technology",
    "GOOGL": "Technology",
    "MSFT": "Technology",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "RELIANCE.NS": "Energy",
    "TCS.NS": "Technology",
    "INFY.NS": "Technology",
}

EXCHANGE_MAP = {
    "AAPL": "NASDAQ",
    "GOOGL": "NASDAQ",
    "MSFT": "NASDAQ",
    "AMZN": "NASDAQ",
    "TSLA": "NASDAQ",
    "RELIANCE.NS": "NSE",
    "TCS.NS": "NSE",
    "INFY.NS": "NSE",
}


def build_message(symbol, fast_info):
    return {
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "price": float(getattr(fast_info, "last_price", None) or 0.0),
        "open": float(getattr(fast_info, "open", None) or 0.0),
        "high": float(getattr(fast_info, "day_high", None) or 0.0),
        "low": float(getattr(fast_info, "day_low", None) or 0.0),
        "volume": int(getattr(fast_info, "last_volume", None) or 0),
        "sector": SECTOR_MAP.get(symbol, "Unknown"),
        "exchange": EXCHANGE_MAP.get(symbol, "UNKNOWN"),
        "ingestion_time": datetime.utcnow().isoformat() + "Z",
    }


def publish_stock_prices(project_id, topic_name, interval_seconds, tickers):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    while True:
        print(f"Publishing stock quotes for {len(tickers)} symbols to {topic_path}...")
        for symbol in tickers:
            try:
                fast_info = yf.Ticker(symbol).fast_info
                msg = build_message(symbol, fast_info)
                payload = json.dumps(msg).encode("utf-8")
                publisher.publish(topic_path, payload)
                print(f"Published {symbol}: price={msg['price']} open={msg['open']} high={msg['high']} low={msg['low']}", flush=True)
            except Exception as e:
                print(f"Error fetching {symbol}: {e}", flush=True)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish Yahoo Finance quotes to Pub/Sub")
    parser.add_argument("--project", default=None, help="GCP project ID")
    parser.add_argument("--topic", default=None, help="Pub/Sub topic name")
    parser.add_argument("--interval", type=int, default=None, help="Seconds between publish batches")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_TICKERS, help="List of ticker symbols")
    args = parser.parse_args()

    project_id = args.project or os.getenv("PROJECT_ID")
    topic_name = args.topic or os.getenv("PUBSUB_TOPIC", "stock-prices-topic")
    interval = args.interval or int(os.getenv("PUBLISH_INTERVAL", "60"))

    if not project_id:
        parser.error("--project or PROJECT_ID environment variable is required")

    publish_stock_prices(project_id, topic_name, interval, args.symbols)
