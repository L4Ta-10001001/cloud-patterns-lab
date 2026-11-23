output "cluster_name" {
  description = "Cluster ECS utilizado por el laboratorio."
  value       = local.cluster_name
}

output "service_name" {
  description = "Nombre del servicio ECS."
  value       = aws_ecs_service.this.name
}

output "task_definition_arn" {
  description = "ARN de la task definition con los dos contenedores."
  value       = aws_ecs_task_definition.this.arn
}

output "security_group_id" {
  description = "Security Group que expone el cliente en el puerto 8000."
  value       = aws_security_group.client.id
}

output "client_log_group" {
  description = "Log group de CloudWatch del cliente."
  value       = aws_cloudwatch_log_group.client.name
}

output "backend_log_group" {
  description = "Log group de CloudWatch del backend."
  value       = aws_cloudwatch_log_group.backend.name
}

output "client_image" {
  description = "Imagen del cliente usada por la task definition."
  value       = local.client_image
}

output "backend_image" {
  description = "Imagen del backend usada por la task definition."
  value       = local.backend_image
}

output "task_lookup_command" {
  description = "Comando para obtener el ARN de la tarea en ejecucion."
  value       = "aws ecs list-tasks --cluster ${local.cluster_name} --service-name ${aws_ecs_service.this.name} --query 'taskArns[0]' --output text"
}
