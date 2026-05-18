resource "google_data_fusion_instance" "etl_instance" {
  #checkov:skip=CKV_GCP_87:Private Data Fusion requires VPC peering setup outside this pipeline's scope
  #checkov:skip=CKV_GCP_104:Stackdriver logging configured via GCP console; options map triggers force-replace
  #checkov:skip=CKV_GCP_105:Stackdriver monitoring configured via GCP console; options map triggers force-replace
  name    = var.data_fusion_instance_name
  project = var.project_id
  region  = var.region
  type    = "BASIC"
}
