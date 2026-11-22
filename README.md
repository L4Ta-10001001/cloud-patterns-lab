# Cloud Architecture and Design Patterns

Trabajo práctico de **Programación Distribuida** — implementaciones simples y
verificables de patrones y servicios cloud sobre AWS, con Terraform como
herramienta de aprovisionamiento.

Repositorio: `git@github.com:L4Ta-10001001/cloud-patterns-lab.git`
Rama de trabajo de Erik: `erik/practicas`

## Objetivo

Investigar y demostrar patrones de arquitectura cloud mediante implementaciones
pequeñas que puedan ejecutarse, probarse y explicarse con evidencia real.
Cada laboratorio incluye descripción, arquitectura, código, instrucciones de
ejecución y resultados (logs, capturas o pruebas).

## Equipo

| Integrante | Laboratorios asignados |
| ---------- | ---------------------- |
| César      | 01, 02, 03, 06, 08     |
| Erik       | 04, 05, 07             |

## Estado de los laboratorios

| # | Laboratorio | Responsable | Estado | Entregable |
| - | ----------- | ----------- | ------ | ---------- |
| 01 | Circuit Breaker | César | bloque de César | — |
| 02 | Retry | César | bloque de César | — |
| 03 | Timeout | César | bloque de César | — |
| 04 | Serverless y Docker | Erik | **Completo (7/7)** | [README](04-serverless-docker/README.md) · [evidencias](04-serverless-docker/evidencias/README.md) |
| 05 | API Gateway, ALB y Reverse Proxy | Erik | **Completo (5/5)** | [README](05-gateway-lb-proxy/README.md) · [evidencias](05-gateway-lb-proxy/evidencias/README.md) |
| 06 | Hub-and-Spoke | César | bloque de César | — |
| 07 | Lift-and-Shift (On-Premise → EC2) | Erik | **Completo (10/10)** | [README](07-lift-and-shift/README.md) · [evidencias](07-lift-and-shift/evidencias/README.md) · [informe](07-lift-and-shift/INFORME.md) |
| 08 | Bastion Host | César | bloque de César | — |

Los laboratorios 04, 05 y 07 están publicados en `erik/practicas`. Cada uno
administra su propia infraestructura con un estado Terraform independiente:
destruir o desactivar uno no afecta a los demás.

## Resultados verificados

**Laboratorio 04 — Serverless y Docker**

- AWS Lambda `cloudlab-erik-lambda` activa.
- Imagen de la API empaquetada y publicada en ECR `cloudlab-erik-api`.
- Cluster ECS `cloudlab-erik-cluster` y servicio `cloudlab-erik-api` operativos.
- Capturas reales de consola AWS incluidas en `evidencias/`.

**Laboratorio 05 — API Gateway, ALB y Reverse Proxy**

- API Gateway HTTP y ALB con NGINX como reverse proxy desplegados y probados.
- Target group con 2 objetivos Fargate en estado `healthy`.
- Evidencias de ejecución y capturas de consola incluidas en `evidencias/`.

**Laboratorio 07 — Lift-and-Shift**

- VM Ubuntu 24.04.5 local (`onprem-legacy-server`) con la aplicación Python
  ejecutándose como servicio `systemd` `legacyapp`, `/health` → HTTP 200.
- EC2 `i-03175f428ac57d526` (`cloudlab-erik-liftshift-ec2`, `t3.micro`,
  Ubuntu 24.04.5) creada con Terraform; misma aplicación y mismo hash SHA256
  `03b47adf2f62b2ebe85bfd0c91899c199dd63243df95d635fa6ac407c1ed8230`.
- HTTP 200 en AWS y captura real de la consola con la instancia en `Running`.
- `terraform destroy` ejecutado al final: 8 recursos eliminados, estado vacío.
- 3 pruebas unitarias en `OK` y 13 archivos de evidencia.

## Cómo ejecutar

1. `git switch erik/practicas && git pull --ff-only origin erik/practicas`.
2. Seguir el README del laboratorio correspondiente. Cada uno es autónomo e
   indica sus requisitos, credenciales, comandos y criterios de aceptación.
3. Las credenciales AWS Academy se configuran **solo en local** en
   `~/.aws/credentials` bajo el perfil `lab`; nunca se versionan.

## Seguridad y buenas prácticas

- No se suben credenciales, tokens, claves privadas, `terraform.tfvars`,
  `terraform.tfstate` ni planes `tfplan`. Cada laboratorio tiene su `.gitignore`.
- El acceso SSH y HTTP se restringe a CIDR `/32` por Security Group; en el
  laboratorio 07 se autorizan dos IP porque la red del laboratorio tiene una
  salida distinta para SSH y para HTTP (ver `04b-terraform-cidr-fix.txt`).
- Los cambios se integran en `erik/practicas` mediante commits ordinarios; la
  rama principal queda para trabajo integrado y revisado.

## Control de costos

Tras obtener las evidencias se desactivaron todos los recursos de pago que ya
no eran necesarios:

| Laboratorio | Acción final | Resultado |
| ----------- | ------------ | --------- |
| 07 | `terraform destroy` sobre su propio estado | 8 recursos destruidos; EC2 `terminated`; 0 recursos en el state |
| 05 | `enable_lab05 = false` y `enable_lab05_alb = false` en `terraform.tfvars` local | 0 ALB, 0 API Gateway |
| 04 | `desired_count = 0` en `terraform.tfvars` local | Lambda, ECR, cluster y servicio ECS siguen activos, pero con **0 tareas Fargate** (`desired=0`, `running=0`) |

La VM local de laboratorio 07 se apagó al terminar. Los archivos
`terraform.tfvars` modificados para la desactivación del laboratorio 05 y para
detener las tareas del 04 están ignorados por Git, por lo que el repositorio
conserva la configuración por defecto de ambos laboratorios. La variable
`desired_count` agregada al laboratorio 04 tiene valor por defecto `null`, que
mantiene el comportamiento original (2 tareas con ALB, 1 sin ALB); basta con
quitar la línea del `tfvars` local para reactivar la demostración.

## Tecnologías

AWS (Lambda, ECR, ECS Fargate, API Gateway, ALB, EC2, VPC, IAM), Terraform,
Docker, Python, NGINX, QEMU/KVM, systemd, Git y GitHub.
