#!/usr/bin/env python3
"""Actualiza de forma controlada lab04 Terraform para adjuntar el ALB a ECS.
Ejecutar desde cualquier directorio: python 05-gateway-lb-proxy/scripts/integrate_lab05.py
No aplica cambios en AWS ni toca terraform.tfvars/terraform.tfstate.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
p = repo / "04-serverless-docker/terraform/main.tf"
source = p.read_text(encoding="utf-8")

pairs = [
    (
        'resource "aws_vpc_security_group_ingress_rule" "ecs_http" {\n  count             = var.enable_ecs ? 1 : 0',
        'resource "aws_vpc_security_group_ingress_rule" "ecs_http" {\n  count             = var.enable_ecs && !var.enable_lab05_alb ? 1 : 0',
    ),
    (
        '  desired_count   = 1\n  launch_type     = "FARGATE"',
        '  desired_count   = var.enable_lab05_alb ? 2 : 1\n  launch_type     = "FARGATE"',
    ),
    (
        '  depends_on = [aws_route_table_association.public]',
        '  depends_on = [aws_route_table_association.public, module.lab05, aws_vpc_security_group_ingress_rule.ecs_from_alb]',
    ),
]

updated = source
for before, after in pairs:
    if after in updated:
        print('Ya aplicado:', after.split('\n')[0])
        continue
    if updated.count(before) != 1:
        raise SystemExit(f'No se encontró una coincidencia única en {p}: {before!r}\nNo se modificó el archivo.')
    updated = updated.replace(before, after)

marker = '  depends_on = [aws_route_table_association.public, module.lab05, aws_vpc_security_group_ingress_rule.ecs_from_alb]'
inject = """  dynamic "load_balancer" {
    for_each = var.enable_lab05 && var.enable_lab05_alb ? [1] : []
    content {
      target_group_arn = module.lab05[0].target_group_arn
      container_name   = "api"
      container_port   = 8080
    }
  }

"""
if inject not in updated:
    if updated.count(marker) != 1:
        raise SystemExit('No se encontró el punto de inserción del ALB. No se modificó el archivo.')
    updated = updated.replace(marker, inject + marker)

if updated == source:
    print('Integración ya aplicada, sin cambios.')
else:
    p.write_text(updated, encoding="utf-8")
    print('Actualización aplicada a:', p)
print('Siguiente: terraform fmt -recursive && terraform init && terraform validate')
