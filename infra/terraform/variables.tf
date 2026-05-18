variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "ga4bigquery-431504"
}

variable "region" {
  description = "GCP region for managed services"
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "GCP zone used by the provider"
  type        = string
  default     = "asia-south1-a"
}

variable "dataset_id" {
  description = "BigQuery dataset for stock intelligence"
  type        = string
  default     = "stock_intelligence"
}

variable "batch_bucket_name" {
  description = "Cloud Storage bucket for batch landing and ETL output"
  type        = string
  default     = "stock-intel-batch-landing-asia-south1"
}

variable "pubsub_topic_name" {
  description = "Pub/Sub topic for streaming stock prices"
  type        = string
  default     = "stock-prices-topic"
}

variable "pubsub_subscription_name" {
  description = "Pub/Sub subscription for the streaming pipeline"
  type        = string
  default     = "stock-prices-sub"
}

variable "data_fusion_instance_name" {
  description = "Cloud Data Fusion instance name"
  type        = string
  default     = "stock-intel-data-fusion"
}
