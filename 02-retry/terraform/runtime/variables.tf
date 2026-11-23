variable "aws_region" {
  description = "Region de AWS Academy."
  type        = string
  default     = "us-east-1"
}

variable "project_prefix" {
  description = "Prefijo para nombrar los recursos del laboratorio."
  type        = string
  default     = "cloudlab-erik"
}

variable "allowed_cidr" {
  description = "IPv4 publica /32 autorizada para llegar al cliente por HTTP."
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && endswith(var.allowed_cidr, "/32")
    error_message = "allowed_cidr debe ser una IPv4 unica en formato x.x.x.x/32."
  }
}

variable "vpc_id" {
  description = "VPC existente. Vacio significa usar la VPC por defecto."
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subredes existentes. Vacio significa usar las subredes publicas de la VPC."
  type        = list(string)
  default     = []
}

variable "ecs_cluster_name" {
  description = "Cluster ECS existente. Vacio significa crear uno nuevo."
  type        = string
  default     = ""
}

variable "execution_role_name" {
  description = "Rol IAM de ejecucion de ECS (LabRole en AWS Academy)."
  type        = string
  default     = "LabRole"
}

variable "task_role_name" {
  description = "Rol IAM de la tarea (LabRole en AWS Academy)."
  type        = string
  default     = "LabRole"
}

variable "image_tag" {
  description = "Tag de las imagenes publicadas en ECR."
  type        = string
  default     = "v1"
}

variable "client_image" {
  description = "URL completa de la imagen del cliente. Vacio usa el repositorio ECR calculado."
  type        = string
  default     = ""
}

variable "backend_image" {
  description = "URL completa de la imagen del backend. Vacio usa el repositorio ECR calculado."
  type        = string
  default     = ""
}

variable "cpu" {
  description = "CPU de la tarea Fargate."
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memoria de la tarea Fargate en MiB."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Numero de tareas Fargate."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "Retencion de los log groups de CloudWatch."
  type        = number
  default     = 3
}
