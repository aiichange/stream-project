resource "google_data_fusion_instance" "etl_instance" {
  #checkov:skip=CKV_GCP_87:Private Data Fusion requires VPC peering setup outside this pipeline's scope
  name    = var.data_fusion_instance_name
  project = var.project_id
  region  = var.region
  type    = "BASIC"

  options = {
    enableStackdriverLogging    = "true"
    enableStackdriverMonitoring = "true"
  }
}
