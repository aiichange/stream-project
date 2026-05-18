import argparse
import json
import time
from datetime import datetime

import yfinance as yf
from google.cloud import pubsub_v1

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


def build_message(symbol, quote):
    return {
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "price": float(quote.get("regularMarketPrice", 0.0) or 0.0),
        "open": float(quote.get("regularMarketOpen", 0.0) or 0.0),
        "high": float(quote.get("regularMarketDayHigh", 0.0) or 0.0),
        "low": float(quote.get("regularMarketDayLow", 0.0) or 0.0),
        "volume": int(quote.get("regularMarketVolume", 0) or 0),
        "sector": SECTOR_MAP.get(symbol, "Unknown"),
        "exchange": EXCHANGE_MAP.get(symbol, "UNKNOWN"),
        "ingestion_time": datetime.utcnow().isoformat() + "Z",
    }


def publish_stock_prices(project_id, topic_name, interval_seconds, tickers):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    while True:
        print(f"Publishing stock quotes for {len(tickers)} symbols to {topic_path}...")
        quotes = yf.download(tickers, period="1d", interval="1m", progress=False, threads=False)
        latest = {}
        if isinstance(quotes, dict) or hasattr(quotes, "columns"):
            for symbol in tickers:
                ticker = yf.Ticker(symbol)
                quote = ticker.fast_info if hasattr(ticker, "fast_info") else ticker.info
                latest[symbol] = quote
        else:
            # Fallback: get prices individually
            for symbol in tickers:
                ticker = yf.Ticker(symbol)
                latest[symbol] = ticker.fast_info if hasattr(ticker, "fast_info") else ticker.info

        for symbol in tickers:
            quote = latest.get(symbol, {})
            payload = json.dumps(build_message(symbol, quote)).encode("utf-8")
            publisher.publish(topic_path, payload)
            print(f"Published {symbol}: {payload}")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish Yahoo Finance quotes to Pub/Sub")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--topic", default="stock-prices-topic", help="Pub/Sub topic name")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between publish batches")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_TICKERS, help="List of ticker symbols")
    args = parser.parse_args()

    publish_stock_prices(args.project, args.topic, args.interval, args.symbols)
