output "instance_id" {
  value       = aws_instance.migration.id
  description = "Instancia EC2 de destino"
}

output "instance_public_ip" {
  value       = aws_instance.migration.public_ip
  description = "IP publica temporal de la instancia de migracion"
}

output "ssh_command" {
  value       = "ssh -i ~/.ssh/cloudlab-liftshift ubuntu@${aws_instance.migration.public_ip}"
  description = "Ejemplo de SSH si importaste la clave generada localmente"
}

output "health_url" {
  value       = "http://${aws_instance.migration.public_ip}:8080/health"
  description = "Endpoint que solo respondera despues de migrar e iniciar la aplicacion"
}
