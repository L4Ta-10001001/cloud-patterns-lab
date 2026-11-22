# Laboratorio 05: modulo alojado en su carpeta propia para mantener el repo organizado.
# Mismo estado Terraform de lab04: no modificar los recursos preexistentes a mano.
variable "enable_lab05" {
  type        = bool
  default     = false
  description = "Crea API Gateway conectado a Lambda existente."
}
variable "enable_lab05_alb" {
  type        = bool
  default     = false
  description = "Agrega ALB y reparte las solicitudes entre 2 tareas ECS del servicio existente."
}

module "lab05" {
  count                 = var.enable_lab05 && var.enable_ecs ? 1 : 0
  source                = "../../05-gateway-lb-proxy/terraform"
  project_prefix        = var.project_prefix
  vpc_id                = aws_vpc.demo[0].id
  subnet_ids            = aws_subnet.public[*].id
  ecs_security_group_id = aws_security_group.ecs[0].id
  allowed_cidr          = var.allowed_cidr
  lambda_arn            = aws_lambda_function.demo.arn
  lambda_invoke_arn     = aws_lambda_function.demo.invoke_arn
  create_alb            = var.enable_lab05_alb
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  count                        = var.enable_ecs && var.enable_lab05 && var.enable_lab05_alb ? 1 : 0
  security_group_id            = aws_security_group.ecs[0].id
  referenced_security_group_id = module.lab05[0].alb_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
  description                  = "Puerto de API accesible solo desde ALB"
}

output "lab05_api_gateway_url" {
  value = var.enable_lab05 && var.enable_ecs ? module.lab05[0].api_gateway_url : null
}

output "lab05_alb_dns_name" {
  value = var.enable_lab05 && var.enable_ecs && var.enable_lab05_alb ? module.lab05[0].alb_dns_name : null
}

output "lab05_target_group_arn" {
  value = var.enable_lab05 && var.enable_ecs && var.enable_lab05_alb ? module.lab05[0].target_group_arn : null
}
