output "client_repository_name" {
  description = "Nombre del repositorio ECR del cliente."
  value       = aws_ecr_repository.this["client"].name
}

output "client_repository_url" {
  description = "URL del repositorio ECR del cliente."
  value       = aws_ecr_repository.this["client"].repository_url
}

output "backend_repository_name" {
  description = "Nombre del repositorio ECR del backend."
  value       = aws_ecr_repository.this["backend"].name
}

output "backend_repository_url" {
  description = "URL del repositorio ECR del backend."
  value       = aws_ecr_repository.this["backend"].repository_url
}

output "image_tag" {
  description = "Tag que se debe usar al publicar las imagenes."
  value       = var.image_tag
}
