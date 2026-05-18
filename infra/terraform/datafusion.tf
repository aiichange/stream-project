resource "google_data_fusion_instance" "etl_instance" {
  name   = var.data_fusion_instance_name
  project = var.project_id
  region = var.region
  type   = "BASIC"
  network = "default"
}
