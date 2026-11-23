data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_role" "execution" {
  name = var.execution_role_name
}

data "aws_iam_role" "task" {
  name = var.task_role_name
}

data "aws_vpc" "default" {
  count   = var.vpc_id == "" ? 1 : 0
  default = true
}

data "aws_vpc" "selected" {
  id = var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id
}

data "aws_subnets" "default" {
  count = length(var.subnet_ids) == 0 ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

data "aws_ecs_cluster" "existing" {
  count        = var.ecs_cluster_name != "" ? 1 : 0
  cluster_name = var.ecs_cluster_name
}

resource "aws_ecs_cluster" "this" {
  count = var.ecs_cluster_name == "" ? 1 : 0

  name = "${var.project_prefix}-retry-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = local.common_tags
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region

  client_repository  = "${var.project_prefix}-retry-client"
  backend_repository = "${var.project_prefix}-retry-backend"

  client_image  = var.client_image != "" ? var.client_image : "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${local.client_repository}:${var.image_tag}"
  backend_image = var.backend_image != "" ? var.backend_image : "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${local.backend_repository}:${var.image_tag}"

  cluster_name = var.ecs_cluster_name != "" ? data.aws_ecs_cluster.existing[0].cluster_name : aws_ecs_cluster.this[0].name

  subnet_ids = length(var.subnet_ids) > 0 ? var.subnet_ids : data.aws_subnets.default[0].ids

  client_log_group  = "/ecs/${var.project_prefix}-retry-client"
  backend_log_group = "/ecs/${var.project_prefix}-retry-backend"

  common_tags = {
    Lab     = "02-retry"
    Project = var.project_prefix
  }
}

resource "aws_cloudwatch_log_group" "client" {
  name              = local.client_log_group
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = local.backend_log_group
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_security_group" "client" {
  name        = "${var.project_prefix}-retry-client-sg"
  description = "Acceso HTTP al cliente Retry"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description = "Cliente HTTP desde la IP autorizada"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    description = "Salida a internet y al backend interno"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = "${var.project_prefix}-retry"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = data.aws_iam_role.execution.arn
  task_role_arn            = data.aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = local.backend_image
      essential = true
      portMappings = [
        {
          containerPort = 8001
          hostPort      = 8001
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "backend"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8001/health\")'"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    },
    {
      name      = "client"
      image     = local.client_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "BACKEND_URL", value = "http://127.0.0.1:8001" },
        { name = "RETRY_MAX_ATTEMPTS", value = "3" },
        { name = "RETRY_INITIAL_WAIT", value = "0.5" },
        { name = "RETRY_MAX_WAIT", value = "2.0" },
        { name = "HTTP_TIMEOUT", value = "2.0" },
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      dependsOn = [
        {
          containerName = "backend"
          condition     = "START"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.client.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "client"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/health\")'"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "this" {
  name             = "${var.project_prefix}-retry-service"
  cluster          = local.cluster_name
  task_definition  = aws_ecs_task_definition.this.arn
  desired_count    = var.desired_count
  launch_type      = "FARGATE"
  platform_version = "LATEST"

  network_configuration {
    subnets          = local.subnet_ids
    security_groups  = [aws_security_group.client.id]
    assign_public_ip = true
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    precondition {
      condition     = length(local.subnet_ids) > 0
      error_message = "No se encontraron subredes publicas en la VPC seleccionada."
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.client,
    aws_cloudwatch_log_group.backend,
  ]

  tags = local.common_tags
}
