# Evidencias — Laboratorio 07 (resultados reales)

Ejecución realizada el 21 de noviembre de 2026 sobre Arch Linux, una VM Ubuntu
24.04.5 on-premise con QEMU/KVM y una instancia EC2 `t3.micro` en AWS
`us-east-1`. Los archivos siguientes son logs y capturas obtenidos durante esa
ejecución; no se reconstruyeron a posteriori.

| Archivo | Evidencia |
| ------- | --------- |
| `01-tests.txt` | `python3 -m unittest discover -s tests -v` → `Ran 3 tests`, `OK`. |
| `02-onprem-health.txt` | HTTP 200 y `{"status":"ok"}` en `/health` de la VM Ubuntu on-premise. El host publica el puerto 8080 de la VM en `127.0.0.1:8088` mediante NAT de QEMU. |
| `03-onprem-service.txt` | Servicio `legacyapp` en estado `active` y SHA256 del `server.py` original dentro de la VM. |
| `04-terraform-plan.txt` | Plan inicial: `8 to add, 0 to change, 0 to destroy`, solo recursos del lab07. |
| `04b-terraform-cidr-fix.txt` | Ajuste de CIDR: la red tiene dos IP de salida, SSH `181.199.46.145/32` y HTTP `157.100.142.229/32`. Incluye la verificación HTTP final. |
| `05-terraform-apply.txt` | `Apply complete! Resources: 8 added, 0 changed, 0 destroyed.` |
| `06-ec2-instance.png` | Captura real de consola AWS (1366×768) verificada por OCR: EC2 → Instances → `i-03175f428ac57d526` (`cloudlab-erik-liftshift-ec2`) en estado `Running`, IP `3.235.42.178`, tipo `t3.micro`, VPC `cloudlab-erik-lab07-vpc`, IMDSv2 `Required`. |
| `07-ec2-service.txt` | Servicio `legacyapp` en estado `active` en EC2 y SHA256 del archivo migrado. |
| `08-ec2-http.txt` | HTTP 200 en `/health` y `/` desde la IP pública de EC2; `/` devuelve el hostname `ip-10-70-1-122`. |
| `09-sha256-comparison.txt` | Hashes idénticos: `03b47adf2f62b2ebe85bfd0c91899c199dd63243df95d635fa6ac407c1ed8230` en VM y EC2. |
| `10-terraform-no-changes.txt` | `terraform plan` final antes de limpiar: `No changes. Your infrastructure matches the configuration.` |
| `11-terraform-destroy.txt` | Control de costos: `Apply complete! Resources: 0 added, 0 changed, 8 destroyed.` Instancia `terminated`, state del lab07 vacío. No se tocó el estado de los labs 04/05. |

## Cómo se verificó

- Los tres tests se ejecutaron desde la raíz del repositorio con
  `python3 -m unittest discover -s 07-lift-and-shift/tests -v`.
- La respuesta HTTP se comprobó con `curl -i` tanto en `127.0.0.1:8088`
  (VM on-premise) como en `http://3.235.42.178:8080` (EC2).
- `server.py` se extrajo de `/opt/legacyapp/server.py` **de la VM**, se envió
  por SCP a EC2 y se comparó el SHA256 en ambos destinos con `sha256sum`.
- La captura de consola se revisó con OCR para confirmar el ID de instancia,
  el nombre, el estado `Running` y la IP pública visibles en la imagen.

## Seguridad de las evidencias

No se versionaron `terraform.tfvars`, `terraform.tfstate`, planes `tfplan`,
claves privadas ni contraseñas. La clave pública sí se registró en AWS como el
recurso `aws_key_pair` administrado por Terraform. La captura de consola solo
muestra datos de la cuenta de laboratorio, sin tokens ni credenciales.

Tras guardar estas evidencias se eliminó la infraestructura del laboratorio 07
y se apagó la VM local; los logs conservan los resultados de cuando ambos
entornos estaban operativos.
