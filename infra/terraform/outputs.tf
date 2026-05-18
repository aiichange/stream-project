output "pubsub_topic_name" {
  value = google_pubsub_topic.stock_prices.name
}

output "pubsub_subscription_name" {
  value = google_pubsub_subscription.stock_prices_sub.name
}

output "batch_bucket_name" {
  value = google_storage_bucket.batch_landing.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.stock_intelligence.dataset_id
}

output "data_fusion_instance" {
  value = google_data_fusion_instance.etl_instance.name
}
