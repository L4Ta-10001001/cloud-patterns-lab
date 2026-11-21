# Application Load Balancer opcional (fase B del laboratorio 05).
# La tarea ECS NO queda abierta a Internet; recibe solicitudes del SG del ALB.
resource "aws_security_group" "alb" {
  count       = var.create_alb ? 1 : 0
  name_prefix = "${var.project_prefix}-alb-"
  description = "ALB HTTP restringido a la IP autorizada del laboratorio"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  count             = var.create_alb ? 1 : 0
  security_group_id = aws_security_group.alb[0].id
  cidr_ipv4         = var.allowed_cidr
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  description       = "HTTP solo desde CIDR autorizado"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  count                        = var.create_alb ? 1 : 0
  security_group_id            = aws_security_group.alb[0].id
  referenced_security_group_id = var.ecs_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
  description                  = "Solo hacia tareas ECS"
}

resource "aws_lb" "demo" {
  count              = var.create_alb ? 1 : 0
  name               = "${var.project_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = var.subnet_ids
  idle_timeout       = 30
}

resource "aws_lb_target_group" "ecs" {
  count       = var.create_alb ? 1 : 0
  name        = "${var.project_prefix}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip" # Obligatorio para ECS Fargate awsvpc.

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "http" {
  count             = var.create_alb ? 1 : 0
  load_balancer_arn = aws_lb.demo[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs[0].arn
  }
}
