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

variable "vpc_name" {
  description = "Tag Name de la VPC existente que se reutiliza (no se administra aqui)."
  type        = string
  default     = "cloudlab-erik-vpc"
}

variable "ecs_cluster_name" {
  description = "Cluster ECS existente que se reutiliza (no se administra aqui)."
  type        = string
  default     = "cloudlab-erik-cluster"
}

variable "execution_role_name" {
  description = "Rol IAM existente; en AWS Academy se llama LabRole."
  type        = string
  default     = "LabRole"
}

variable "image_tag" {
  description = "Etiqueta de las imagenes publicadas en ECR."
  type        = string
  default     = "v1"
}
