terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CloudPatternsLab"
      Owner       = "Erik"
      Environment = "AcademicLab"
      ManagedBy   = "Terraform"
      Lab         = "07-LiftAndShift"
    }
  }
}
