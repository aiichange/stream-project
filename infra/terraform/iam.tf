resource "google_service_account" "pipeline_sa" {
  account_id   = "stock-intel-sa"
  display_name = "Stock Market Intelligence Pipeline Service Account"
}

locals {
  required_roles = [
    "roles/pubsub.editor",
    "roles/dataflow.worker",
    "roles/bigquery.dataEditor",
    "roles/storage.admin",
    "roles/datafusion.admin",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/resourcemanager.projectIamAdmin"
  ]
}

resource "google_project_iam_member" "pipeline_roles" {
  #checkov:skip=CKV_GCP_49:roles/iam.serviceAccountUser is required for Dataflow to impersonate the pipeline SA
  #checkov:skip=CKV_GCP_41:roles/iam.serviceAccountUser is required for Dataflow job submission
  for_each = toset(local.required_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
