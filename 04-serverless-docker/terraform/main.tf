# Reutilizar el rol existente evita intentar crear IAM roles que AWS Academy puede prohibir.
# Requiere que LabRole permita la asuncion por Lambda y ECS Tasks y tenga permisos adecuados.
data "aws_iam_role" "lab" {
  name = var.execution_role_name
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda/lambda_function.py"
  output_path = "${path.module}/lambda-package.zip"
}

resource "aws_lambda_function" "demo" {
  function_name    = "${var.project_prefix}-lambda"
  role             = data.aws_iam_role.lab.arn
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  runtime          = "python3.12"
  handler          = "lambda_function.lambda_handler"
  timeout          = 5
  memory_size      = 128
}

resource "aws_ecr_repository" "api" {
  name         = "${var.project_prefix}-api"
  force_delete = true # Uso exclusivo del laboratorio; destruye imagenes al limpiar.

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecs_cluster" "demo" {
  name = "${var.project_prefix}-cluster"
}

# La red solo se crea al habilitar ECS. Sin NAT Gateway para reducir costos.
data "aws_availability_zones" "available" {
  count = var.enable_ecs ? 1 : 0
  state = "available"
}

resource "aws_vpc" "demo" {
  count                = var.enable_ecs ? 1 : 0
  cidr_block           = "10.77.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project_prefix}-vpc" }
}

resource "aws_internet_gateway" "demo" {
  count  = var.enable_ecs ? 1 : 0
  vpc_id = aws_vpc.demo[0].id
  tags   = { Name = "${var.project_prefix}-igw" }
}

resource "aws_subnet" "public" {
  count                   = var.enable_ecs ? 2 : 0
  vpc_id                  = aws_vpc.demo[0].id
  cidr_block              = "10.77.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available[0].names[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project_prefix}-public-${count.index + 1}" }
}

resource "aws_route_table" "public" {
  count  = var.enable_ecs ? 1 : 0
  vpc_id = aws_vpc.demo[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.demo[0].id
  }
  tags = { Name = "${var.project_prefix}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = var.enable_ecs ? 2 : 0
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_security_group" "ecs" {
  count       = var.enable_ecs ? 1 : 0
  name_prefix = "${var.project_prefix}-ecs-"
  description = "Acceso limitado al puerto 8080 desde la IP del estudiante"
  vpc_id      = aws_vpc.demo[0].id
}

resource "aws_vpc_security_group_ingress_rule" "ecs_http" {
  count             = var.enable_ecs && !var.enable_lab05_alb ? 1 : 0
  security_group_id = aws_security_group.ecs[0].id
  cidr_ipv4         = var.allowed_cidr
  from_port         = 8080
  to_port           = 8080
  ip_protocol       = "tcp"
  description       = "HTTP de prueba solo desde IP autorizada"
}

resource "aws_vpc_security_group_egress_rule" "ecs_outbound" {
  count             = var.enable_ecs ? 1 : 0
  security_group_id = aws_security_group.ecs[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Salida para descargar imagen de ECR y enviar registros"
}

resource "aws_cloudwatch_log_group" "ecs" {
  count             = var.enable_ecs ? 1 : 0
  name              = "/ecs/${var.project_prefix}-api"
  retention_in_days = 3
}

resource "aws_ecs_task_definition" "api" {
  count                    = var.enable_ecs ? 1 : 0
  family                   = "${var.project_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = data.aws_iam_role.lab.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    essential = true
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs[0].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  count           = var.enable_ecs ? 1 : 0
  name            = "${var.project_prefix}-api"
  cluster         = aws_ecs_cluster.demo.id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = coalesce(var.desired_count, var.enable_lab05_alb ? 2 : 1)
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs[0].id]
    assign_public_ip = true # Solo laboratorio; mas adelante se usara ALB.
  }

  dynamic "load_balancer" {
    for_each = var.enable_lab05 && var.enable_lab05_alb ? [1] : []
    content {
      target_group_arn = module.lab05[0].target_group_arn
      container_name   = "api"
      container_port   = 8080
    }
  }

  depends_on = [aws_route_table_association.public, module.lab05, aws_vpc_security_group_ingress_rule.ecs_from_alb]
}
