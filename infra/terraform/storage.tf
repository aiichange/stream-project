resource "google_storage_bucket" "batch_landing" {
  #checkov:skip=CKV_GCP_62:Access logging requires a separate log bucket; not required for this internal pipeline
  name                        = var.batch_bucket_name
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }
}
