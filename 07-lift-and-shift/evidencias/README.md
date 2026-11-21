# Evidencias — Lab07 (resultados reales)

| Archivo | Evidencia |
|---|---|
| `01-tests.txt` | `python3 -m unittest discover -s tests -v` → `Ran 3 tests`, `OK`. |
| `02-onprem-health.txt` | HTTP 200 en `/health` de la VM Ubuntu on-premise. El host publica el puerto 8080 de la VM en `127.0.0.1:8088` mediante NAT de QEMU. |
| `03-onprem-service.txt` | `legacyapp` en estado `active` y SHA256 del `server.py` original en la VM. |
| `04-terraform-plan.txt` | Plan inicial: 8 recursos nuevos, 0 cambios, 0 destrucciones. |
| `04b-terraform-cidr-fix.txt` | Ajuste de CIDR: la red tiene dos IP de salida (SSH directo `181.199.46.145`, HTTP vía proxy `157.100.142.229`). |
| `05-terraform-apply.txt` | `Apply complete! Resources: 8 added, 0 changed, 0 destroyed.` |
| `06-ec2-instance.png` | Captura real de consola AWS: EC2 → Instances → `i-03175f428ac57d526` (`cloudlab-erik-liftshift-ec2`) en estado `Running`, IP pública `3.235.42.178`, tipo `t3.micro` y VPC `cloudlab-erik-lab07-vpc`. |
| `07-ec2-service.txt` | `legacyapp` en estado `active` en EC2 y SHA256 del archivo migrado. |
| `08-ec2-http.txt` | HTTP 200 en `/health` y `/` desde la IP pública de EC2. |
| `09-sha256-comparison.txt` | Hashes idénticos entre la VM on-premise y EC2. |
| `10-terraform-no-changes.txt` | `terraform plan` final: `No changes. Your infrastructure matches the configuration.` |

No se versionaron `terraform.tfvars`, estados, planes ni claves privadas. La
clave pública sí es importada por Terraform como recurso `aws_key_pair`.
