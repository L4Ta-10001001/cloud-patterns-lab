output "client_repository_url" {
  description = "URI del repositorio ECR del cliente."
  value       = aws_ecr_repository.client.repository_url
}

output "backend_repository_url" {
  description = "URI del repositorio ECR del backend."
  value       = aws_ecr_repository.backend.repository_url
}

output "cluster_name" {
  description = "Cluster ECS reutilizado."
  value       = data.aws_ecs_cluster.lab.cluster_name
}

output "service_name" {
  description = "Nombre del servicio ECS del laboratorio."
  value       = aws_ecs_service.lab.name
}

output "task_family" {
  description = "Familia de la task definition."
  value       = aws_ecs_task_definition.lab.family
}

output "security_group_id" {
  description = "Security Group del laboratorio."
  value       = aws_security_group.lab.id
}
