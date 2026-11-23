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

variable "image_tag" {
  description = "Tag de las imagenes que se publicaran en ECR."
  type        = string
  default     = "v1"
}
