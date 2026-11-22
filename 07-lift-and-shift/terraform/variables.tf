variable "aws_region" {
  description = "Region de AWS para el laboratorio"
  type        = string
  default     = "us-east-1"
}

variable "allowed_cidr" {
  description = "IP publica para SSH directo, formato x.x.x.x/32"
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0)) && endswith(var.allowed_cidr, "/32")
    error_message = "allowed_cidr debe ser una IPv4 publica unica en formato x.x.x.x/32."
  }
}

variable "http_allowed_cidr" {
  description = "IP publica de salida del trafico HTTP (puede diferir de SSH si hay proxy). Null = usar allowed_cidr."
  type        = string
  default     = null

  validation {
    condition     = var.http_allowed_cidr == null || (can(cidrhost(var.http_allowed_cidr, 0)) && endswith(var.http_allowed_cidr, "/32"))
    error_message = "http_allowed_cidr debe ser x.x.x.x/32 o null."
  }
}

variable "instance_type" {
  description = "Tipo de EC2 permitido por AWS Academy"
  type        = string
  default     = "t3.micro"
}

variable "create_key_pair" {
  description = "Si es true importa tu clave publica; si es false usa una key pair existente en EC2"
  type        = bool
  default     = true
}

variable "public_key_path" {
  description = "Ruta local a la llave publica SSH; no se sube la clave privada"
  type        = string
  default     = "~/.ssh/cloudlab-liftshift.pub"
}

variable "existing_key_name" {
  description = "Nombre de key pair existente si create_key_pair=false"
  type        = string
  default     = null
}
