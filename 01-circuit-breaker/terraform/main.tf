# Recursos propios del laboratorio 01. La VPC, las subredes y el cluster ECS
# se reutilizan mediante data sources: este estado nunca los destruye.

data "aws_vpc" "lab" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.lab.id]
  }

  filter {
    name   = "tag:Name"
    values = ["${var.project_prefix}-public-*"]
  }
}

data "aws_ecs_cluster" "lab" {
  cluster_name = var.ecs_cluster_name
}

data "aws_iam_role" "lab" {
  name = var.execution_role_name
}

resource "aws_ecr_repository" "client" {
  name                 = "${var.project_prefix}-lab01-client"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_prefix}-lab01-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_cloudwatch_log_group" "client" {
  name              = "/ecs/${var.project_prefix}-lab01-client"
  retention_in_days = 3
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_prefix}-lab01-backend"
  retention_in_days = 3
}

resource "aws_security_group" "lab" {
  name        = "${var.project_prefix}-lab01-sg"
  description = "Acceso HTTP al cliente del laboratorio 01"
  vpc_id      = data.aws_vpc.lab.id

  ingress {
    description = "Cliente Circuit Breaker desde IP autorizada"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    description = "Salida para ECR, CloudWatch y backend local"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_prefix}-lab01-sg"
  }
}

resource "aws_ecs_task_definition" "lab" {
  family                   = "${var.project_prefix}-lab01-circuit-breaker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    },
    {
      name      = "client"
      image     = "${aws_ecr_repository.client.repository_url}:${var.image_tag}"
      essential = true
      dependsOn = [
        {
          containerName = "backend"
          condition     = "START"
        }
      ]
      environment = [
        {
          name  = "BACKEND_URL"
          value = "http://127.0.0.1:8001"
        }
      ]
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.client.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "client"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "lab" {
  name            = "${var.project_prefix}-lab01-circuit-breaker"
  cluster         = data.aws_ecs_cluster.lab.arn
  task_definition = aws_ecs_task_definition.lab.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
    security_groups  = [aws_security_group.lab.id]
    assign_public_ip = true
  }
}
