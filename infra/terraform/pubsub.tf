resource "google_pubsub_topic" "stock_prices" {
  name = var.pubsub_topic_name
}

resource "google_pubsub_subscription" "stock_prices_sub" {
  name  = var.pubsub_subscription_name
  topic = google_pubsub_topic.stock_prices.name
  ack_deadline_seconds = 30
}
