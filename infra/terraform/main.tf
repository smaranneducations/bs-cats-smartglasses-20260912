terraform {
  required_version = ">= 1.8.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "GCP project id from .env"
}

variable "region" {
  type        = string
  description = "GCP region for Cloud Run and supporting services"
  default     = "us-central1"
}

variable "service_name_prefix" {
  type        = string
  description = "Resource prefix for services"
  default     = "smart-glasses"
}

output "service_name_prefix" {
  value       = var.service_name_prefix
  description = "Used by deploy scripts as a simple marker."
}
