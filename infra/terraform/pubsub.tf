resource "google_pubsub_topic" "stock_prices" {
  #checkov:skip=CKV_GCP_83:CSEK for Pub/Sub requires KMS key management outside this pipeline's scope
  name    = var.pubsub_topic_name
  project = var.project_id
}

resource "google_pubsub_subscription" "stock_prices_sub" {
  name                       = var.pubsub_subscription_name
  topic                      = google_pubsub_topic.stock_prices.name
  project                    = var.project_id
  ack_deadline_seconds       = 30
  message_retention_duration = "604800s"
}
