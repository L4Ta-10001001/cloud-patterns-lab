output "lambda_function_name" {
  value       = aws_lambda_function.demo.function_name
  description = "Nombre para aws lambda invoke"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "Destino del docker push"
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.demo.name
}

output "ecs_service_name" {
  value = var.enable_ecs ? aws_ecs_service.api[0].name : null
}

output "vpc_id" {
  value = var.enable_ecs ? aws_vpc.demo[0].id : null
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}
