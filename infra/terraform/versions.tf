terraform {
  required_version = ">= 1.6.0"
  backend "s3" {
    # Placeholder values for local/CI validate. Real backend values are injected via backend.hcl in workflows.
    bucket                      = "placeholder-bucket"
    key                         = "placeholder/terraform.tfstate"
    region                      = "us-east-1"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    use_path_style              = false
  }

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.68"
    }
  }
}
