resource "google_bigquery_dataset" "stock_intelligence" {
  #checkov:skip=CKV_GCP_81:CSEK requires KMS key management outside this pipeline's scope
  dataset_id                  = var.dataset_id
  location                    = var.region
  default_table_expiration_ms = 31536000000
  description                 = "Dataset for streaming stock prices and batch market factors."
}

resource "google_bigquery_table" "stream_stock_prices" {
  #checkov:skip=CKV_GCP_80:CSEK requires KMS key management outside this pipeline's scope
  dataset_id          = google_bigquery_dataset.stock_intelligence.dataset_id
  table_id            = "stream_stock_prices"
  deletion_protection = true
  schema = jsonencode([
    { name = "symbol", type = "STRING", mode = "REQUIRED" },
    { name = "timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "price", type = "FLOAT", mode = "NULLABLE" },
    { name = "open", type = "FLOAT", mode = "NULLABLE" },
    { name = "high", type = "FLOAT", mode = "NULLABLE" },
    { name = "low", type = "FLOAT", mode = "NULLABLE" },
    { name = "volume", type = "INT64", mode = "NULLABLE" },
    { name = "sector", type = "STRING", mode = "NULLABLE" },
    { name = "exchange", type = "STRING", mode = "NULLABLE" },
    { name = "ingestion_time", type = "TIMESTAMP", mode = "NULLABLE" }
  ])
}

resource "google_bigquery_table" "batch_market_factors" {
  #checkov:skip=CKV_GCP_80:CSEK requires KMS key management outside this pipeline's scope
  dataset_id          = google_bigquery_dataset.stock_intelligence.dataset_id
  table_id            = "batch_market_factors"
  deletion_protection = true
  schema = jsonencode([
    { name = "factor_date", type = "DATE", mode = "REQUIRED" },
    { name = "region", type = "STRING", mode = "REQUIRED" },
    { name = "sector", type = "STRING", mode = "REQUIRED" },
    { name = "weather_score", type = "FLOAT", mode = "NULLABLE" },
    { name = "crude_oil_price", type = "FLOAT", mode = "NULLABLE" },
    { name = "usd_inr_rate", type = "FLOAT", mode = "NULLABLE" },
    { name = "inflation_rate", type = "FLOAT", mode = "NULLABLE" },
    { name = "interest_rate", type = "FLOAT", mode = "NULLABLE" },
    { name = "aqi", type = "INT64", mode = "NULLABLE" },
    { name = "news_sentiment", type = "FLOAT", mode = "NULLABLE" },
    { name = "social_sentiment", type = "FLOAT", mode = "NULLABLE" },
    { name = "geo_risk", type = "FLOAT", mode = "NULLABLE" },
    { name = "supply_chain_risk", type = "FLOAT", mode = "NULLABLE" },
    { name = "demand_index", type = "FLOAT", mode = "NULLABLE" },
    { name = "batch_id", type = "STRING", mode = "NULLABLE" }
  ])
}

resource "google_bigquery_table" "stock_factor_analysis_view" {
  #checkov:skip=CKV_GCP_80:CSEK requires KMS key management outside this pipeline's scope
  dataset_id          = google_bigquery_dataset.stock_intelligence.dataset_id
  table_id            = "stock_factor_analysis_view"
  deletion_protection = true
  view {
    query          = <<-SQL
      SELECT
        s.symbol,
        s.timestamp,
        s.price,
        s.open,
        s.high,
        s.low,
        s.volume,
        s.sector,
        f.factor_date,
        f.weather_score,
        f.crude_oil_price,
        f.usd_inr_rate,
        f.inflation_rate,
        f.interest_rate,
        f.aqi,
        f.news_sentiment,
        f.social_sentiment,
        f.geo_risk,
        f.supply_chain_risk,
        f.demand_index
      FROM
        `${var.project_id}.${var.dataset_id}.stream_stock_prices` AS s
      JOIN
        `${var.project_id}.${var.dataset_id}.batch_market_factors` AS f
      ON
        s.sector = f.sector
        AND DATE(s.timestamp) = f.factor_date
    SQL
    use_legacy_sql = false
  }
}
