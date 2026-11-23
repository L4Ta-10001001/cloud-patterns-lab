locals {
  repositories = {
    client  = "${var.project_prefix}-retry-client"
    backend = "${var.project_prefix}-retry-backend"
  }
}

resource "aws_ecr_repository" "this" {
  for_each = local.repositories

  name                 = each.value
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Lab     = "02-retry"
    Service = each.key
  }
}
