variable "aws_region" {
  description = "Region de AWS Academy en la que se desplegaran los recursos."
  type        = string
  default     = "us-east-1"
}

variable "project_prefix" {
  description = "Prefijo unico en la cuenta AWS para evitar colisiones de nombres."
  type        = string
  default     = "cloudlab-erik"
}

variable "execution_role_name" {
  description = "Rol IAM existente; en AWS Academy suele llamarse LabRole."
  type        = string
  default     = "LabRole"
}

variable "enable_ecs" {
  description = "False en el primer despliegue. True solo tras publicar la imagen en ECR."
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "Etiqueta de la imagen Docker subida a ECR."
  type        = string
  default     = "v1"
}

variable "allowed_cidr" {
  description = "IP publica personal /32 autorizada para llamar a la tarea Fargate del laboratorio."
  type        = string
  default     = "127.0.0.1/32"
}
