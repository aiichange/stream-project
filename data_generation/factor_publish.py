"""
Publishes real market factors to Pub/Sub every N seconds.

Data sources (all free, no API key required):
  yfinance  CL=F       -> crude oil price
  yfinance  USDINR=X   -> USD/INR exchange rate
  yfinance  ^VIX       -> geo/market risk proxy
  yfinance  sector ETFs -> news_sentiment (daily % change)
  Open-Meteo weather   -> weather_score  (Mumbai: lat=19.076, lon=72.877)
  Open-Meteo air quality -> aqi
  World Bank API       -> inflation_rate (India CPI, annual)
  World Bank API       -> interest_rate  (India lending rate, annual)

Usage:
    python data_generation/factor_publish.py \
        --project ga4bigquery-431504 \
        --topic market-factors-topic \
        --interval 120
"""

import argparse
import json
import time
from datetime import datetime, date, timezone

import requests
import yfinance as yf
from google.cloud import pubsub_v1

# Mumbai coordinates (asia-south1 region context)
MUMBAI_LAT = 19.076
MUMBAI_LON = 72.877

SECTORS = [
    "Technology",
    "Energy",
    "Financials",
    "Healthcare",
    "Consumer Discretionary",
    "Materials",
]

SECTOR_ETF = {
    "Technology":            "QQQ",
    "Energy":                "XLE",
    "Financials":            "XLF",
    "Healthcare":            "XLV",
    "Consumer Discretionary":"XLY",
    "Materials":             "XLB",
}


# ---------------------------------------------------------------------------
# yfinance: crude oil, FX, VIX
# ---------------------------------------------------------------------------

def fetch_yfinance_globals():
    crude_info = yf.Ticker("CL=F").fast_info
    fx_info    = yf.Ticker("USDINR=X").fast_info
    vix_info   = yf.Ticker("^VIX").fast_info

    crude_price = float(getattr(crude_info, "last_price", None) or 0.0)
    usd_inr     = float(getattr(fx_info,    "last_price", None) or 0.0)
    vix         = float(getattr(vix_info,   "last_price", None) or 20.0)

    # VIX 10-80 -> geo_risk 0.0-1.0
    geo_risk = round(min(vix / 80.0, 1.0), 3)
    return crude_price, usd_inr, geo_risk


def fetch_sector_sentiment(etf_symbol):
    """[-1, 1] from ETF daily % change × 10."""
    try:
        fi   = yf.Ticker(etf_symbol).fast_info
        prev = float(getattr(fi, "previous_close", None) or 0.0)
        last = float(getattr(fi, "last_price",     None) or 0.0)
        if prev > 0:
            return round(max(-1.0, min(1.0, (last - prev) / prev * 10)), 3)
    except Exception as exc:
        print(f"  Sentiment error [{etf_symbol}]: {exc}", flush=True)
    return 0.0


# ---------------------------------------------------------------------------
# Open-Meteo: weather_score + aqi  (no API key)
# ---------------------------------------------------------------------------

def fetch_weather_and_aqi():
    """
    weather_score: 0-100 composite (temperature, humidity, wind).
    aqi: 0-500 European AQI from Open-Meteo air-quality endpoint.
    Returns (weather_score, aqi) — both None on failure.
    """
    weather_score = None
    aqi           = None

    # Weather
    try:
        url  = "https://api.open-meteo.com/v1/forecast"
        resp = requests.get(url, params={
            "latitude":  MUMBAI_LAT,
            "longitude": MUMBAI_LON,
            "current":   "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone":  "Asia/Kolkata",
        }, timeout=10)
        resp.raise_for_status()
        cur  = resp.json()["current"]
        temp     = cur.get("temperature_2m", 25)        # C
        humidity = cur.get("relative_humidity_2m", 60)  # %
        wind     = cur.get("wind_speed_10m", 10)        # km/h

        # Score each dimension 0-100; ideal: temp~24C, humidity~50%, wind~5 km/h
        temp_s  = max(0.0, 100 - abs(temp - 24) * 3)
        humid_s = max(0.0, 100 - abs(humidity - 50) * 1.5)
        wind_s  = max(0.0, 100 - wind * 2)
        weather_score = round((temp_s + humid_s + wind_s) / 3, 2)
        print(f"  Weather -> temp={temp}C  humidity={humidity}%  wind={wind}km/h  score={weather_score}", flush=True)
    except Exception as exc:
        print(f"  Weather fetch failed: {exc}", flush=True)

    # AQI
    try:
        url  = "https://air-quality-api.open-meteo.com/v1/air-quality"
        resp = requests.get(url, params={
            "latitude":  MUMBAI_LAT,
            "longitude": MUMBAI_LON,
            "current":   "european_aqi",
            "timezone":  "Asia/Kolkata",
        }, timeout=10)
        resp.raise_for_status()
        aqi_raw = resp.json()["current"].get("european_aqi")
        if aqi_raw is not None:
            aqi = int(aqi_raw)
        print(f"  AQI (European) -> {aqi}", flush=True)
    except Exception as exc:
        print(f"  AQI fetch failed: {exc}", flush=True)

    return weather_score, aqi


# ---------------------------------------------------------------------------
# World Bank: inflation_rate + interest_rate  (no API key, annual data)
# ---------------------------------------------------------------------------

_WB_CACHE = {}   # cache so we don't hammer World Bank every 2 min

def _fetch_world_bank(indicator, country="IN"):
    cache_key = f"{country}_{indicator}"
    if cache_key in _WB_CACHE:
        return _WB_CACHE[cache_key]
    try:
        url  = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
        resp = requests.get(url, params={"format": "json", "mrv": 1, "per_page": 1}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # data[1] is the list of records; data[0] is metadata
        value = data[1][0]["value"] if data and len(data) > 1 and data[1] else None
        if value is not None:
            value = round(float(value), 4)
        _WB_CACHE[cache_key] = value
        return value
    except Exception as exc:
        print(f"  World Bank fetch failed [{indicator}]: {exc}", flush=True)
        return None


def fetch_macro_rates():
    """Returns (inflation_rate, interest_rate) from World Bank (India, latest annual)."""
    inflation = _fetch_world_bank("FP.CPI.TOTL.ZG")   # India CPI inflation %
    interest  = _fetch_world_bank("FR.INR.LEND")       # India lending rate %
    print(f"  World Bank -> inflation={inflation}%  interest={interest}%", flush=True)
    return inflation, interest


# ---------------------------------------------------------------------------
# Message builder + main loop
# ---------------------------------------------------------------------------

def build_message(sector, crude_price, usd_inr, geo_risk, sentiment,
                  weather_score, aqi, inflation_rate, interest_rate):
    return {
        "factor_date":       date.today().isoformat(),
        "sector":            sector,
        "updated_at":        datetime.now(timezone.utc).isoformat(),
        "crude_oil_price":   crude_price    if crude_price  > 0    else None,
        "usd_inr_rate":      usd_inr        if usd_inr      > 0    else None,
        "geo_risk":          geo_risk,
        "news_sentiment":    sentiment,
        "weather_score":     weather_score,
        "aqi":               aqi,
        "inflation_rate":    inflation_rate,
        "interest_rate":     interest_rate,
        # Not available from free APIs — view falls back to batch
        "social_sentiment":  None,
        "supply_chain_risk": None,
        "demand_index":      None,
    }


def publish_factors(project_id, topic_name, interval_seconds):
    publisher  = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    while True:
        ts = datetime.now(timezone.utc).isoformat()
        print(f"\n[{ts}] Fetching all market factors...", flush=True)

        crude_price, usd_inr, geo_risk = fetch_yfinance_globals()
        print(f"  yfinance -> crude=${crude_price:.2f}  USD/INR={usd_inr:.2f}  VIX-risk={geo_risk:.3f}", flush=True)

        weather_score, aqi              = fetch_weather_and_aqi()
        inflation_rate, interest_rate   = fetch_macro_rates()

        for sector in SECTORS:
            etf       = SECTOR_ETF.get(sector, "SPY")
            sentiment = fetch_sector_sentiment(etf)
            msg       = build_message(
                sector, crude_price, usd_inr, geo_risk, sentiment,
                weather_score, aqi, inflation_rate, interest_rate,
            )
            publisher.publish(topic_path, json.dumps(msg).encode("utf-8"))
            print(f"  Published [{sector}] sentiment={sentiment}", flush=True)

        print(f"  Done. Sleeping {interval_seconds}s...", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish live market factors to Pub/Sub")
    parser.add_argument("--project",  required=True)
    parser.add_argument("--topic",    default="market-factors-topic")
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args()

    publish_factors(args.project, args.topic, args.interval)
