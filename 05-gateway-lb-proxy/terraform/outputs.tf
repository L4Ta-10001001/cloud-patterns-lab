output "api_gateway_url" {
  value = aws_apigatewayv2_api.demo.api_endpoint
}

output "alb_dns_name" {
  value = var.create_alb ? aws_lb.demo[0].dns_name : null
}

output "alb_security_group_id" {
  value = var.create_alb ? aws_security_group.alb[0].id : null
}

output "target_group_arn" {
  value = var.create_alb ? aws_lb_target_group.ecs[0].arn : null
}
