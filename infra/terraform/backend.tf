terraform {
  backend "gcs" {
    bucket = "stock-intel-terraform-state-asia-south1"
    prefix = "terraform/state"
  }
}
