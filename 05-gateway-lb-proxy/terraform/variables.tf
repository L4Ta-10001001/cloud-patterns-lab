variable "project_prefix" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "allowed_cidr" { type = string }
variable "lambda_arn" { type = string }
variable "lambda_invoke_arn" { type = string }
variable "create_alb" { type = bool }
