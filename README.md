# Cloud Architecture and Design Patterns

Laboratorio de investigación y práctica de patrones de arquitectura cloud para
la asignatura **Programación Distribuida**.

## Objetivo

Investigar y demostrar patrones de arquitectura cloud mediante
implementaciones funcionales, reproducibles y documentadas, con evidencias
reales de su ejecución local y en AWS.

## Estado actual

**4 de 8 laboratorios completados.**

| Lab | Tema | Responsable | Estado | Documentación |
|---|---|---|---|---|
| 01 | Circuit Breaker | Erik | ✅ Completado | [README](01-circuit-breaker/README.md) |
| 02 | Retry | César | ⏳ Pendiente | [README](02-retry/README.md) |
| 03 | Timeout | César | ⏳ Pendiente | [README](03-timeout/README.md) |
| 04 | Serverless y contenedores | Erik | ✅ Completado | [README](04-serverless-docker/README.md) |
| 05 | API Gateway, ALB y reverse proxy | Erik | ✅ Completado | [README](05-gateway-lb-proxy/README.md) |
| 06 | Hub-and-Spoke | César | ⏳ Pendiente | [README](06-hub-and-spoke/README.md) |
| 07 | Lift-and-Shift | Erik | ✅ Completado | [README](07-lift-and-shift/README.md) |
| 08 | Bastion Host | César | ⏳ Pendiente | [README](08-bastion/README.md) |

## Equipo y responsabilidades

| Integrante | Laboratorios |
|---|---|
| Erik | 01, 04, 05, 07 |
| César | 02, 03, 06, 08 |

## Laboratorio 01 — Circuit Breaker

Implementación completa con dos microservicios FastAPI, PyBreaker, Docker
Compose y Amazon ECS Fargate. Demuestra los estados `CLOSED`, `OPEN` y
`HALF-OPEN`, el rechazo sin llamada al backend y la recuperación controlada.

| Resultado | Evidencia |
|---|---|
| 16 pruebas aprobadas | [01-pytest.txt](01-circuit-breaker/evidencias/01-pytest.txt) |
| Dos contenedores Docker | [02-docker-ps.txt](01-circuit-breaker/evidencias/02-docker-ps.txt) |
| Operación normal | [03-normal-operation.txt](01-circuit-breaker/evidencias/03-normal-operation.txt) |
| Apertura del circuito | [04-circuit-open.txt](01-circuit-breaker/evidencias/04-circuit-open.txt) |
| Rechazo sin llamar al backend | [05-fast-fail.txt](01-circuit-breaker/evidencias/05-fast-fail.txt) |
| Recuperación `HALF-OPEN` | [06-circuit-recovery.txt](01-circuit-breaker/evidencias/06-circuit-recovery.txt) |
| Terraform validado y aplicado | [07](01-circuit-breaker/evidencias/07-terraform-validate.txt) · [08](01-circuit-breaker/evidencias/08-terraform-plan.txt) · [09](01-circuit-breaker/evidencias/09-terraform-apply.txt) |
| Servicio ECS Fargate | [10-ecs.png](01-circuit-breaker/evidencias/10-ecs.png) |
| Demo real en AWS | [11-aws-demo.txt](01-circuit-breaker/evidencias/11-aws-demo.txt) |
| Logs de CloudWatch | [12-cloudwatch.txt](01-circuit-breaker/evidencias/12-cloudwatch.txt) |
| Destrucción de recursos | [13-terraform-destroy.txt](01-circuit-breaker/evidencias/13-terraform-destroy.txt) |

Documentación completa: [README del laboratorio](01-circuit-breaker/README.md),
[arquitectura](01-circuit-breaker/ARQUITECTURA.md) e
[informe](01-circuit-breaker/INFORME.md).

## Laboratorios 04, 05 y 07

| Lab | Implementación | Estado |
|---|---|---|
| 04 | Lambda, ECR y ECS Fargate con Terraform. | Completado; servicio ECS en `desired=0` y evidencias publicadas. |
| 05 | API Gateway, ALB y NGINX reverse proxy. | Completado; infraestructura desactivada en la configuración local y evidencias publicadas. |
| 07 | Lift-and-Shift de una app Python a EC2. | Completado; migración verificada con hash idéntico y recursos AWS destruidos. |

## Estructura del repositorio

```text
cloud-patterns-lab/
├── 01-circuit-breaker/      # FastAPI + PyBreaker + Docker + ECS Fargate
├── 02-retry/                # Pendiente (César)
├── 03-timeout/              # Pendiente (César)
├── 04-serverless-docker/    # Lambda + ECR + ECS Fargate
├── 05-gateway-lb-proxy/     # API Gateway + ALB + NGINX
├── 06-hub-and-spoke/        # Pendiente (César)
├── 07-lift-and-shift/       # VM on-premise → EC2
└── 08-bastion/              # Pendiente (César)
```

Cada laboratorio incluye su propio `README.md`, código, configuración,
pruebas y carpeta `evidencias/`.

## Tecnologías

AWS (Lambda, ECR, ECS Fargate, EC2, API Gateway, ALB, CloudWatch), Terraform,
Docker y Docker Compose, Python 3.12, FastAPI, PyBreaker, HTTPX, Pytest,
NGINX, Git y GitHub.

## Evidencias y buenas prácticas

- Las evidencias se generan ejecutando los comandos reales; no se fabrican
  resultados.
- No se versionan credenciales, tokens, llaves privadas, `terraform.tfvars`,
  estados de Terraform ni planes.
- Los recursos AWS de prueba se apagan o destruyen al finalizar cada
  laboratorio.
- Los estados de Terraform son independientes por laboratorio para evitar
  modificaciones accidentales entre ellos.

## Estado AWS y control de costos

- **Lab01:** 7 recursos destruidos; servicio ECS `INACTIVE`; sin ECR, log
  groups ni Security Group del laboratorio. Clúster, VPC, subredes y `LabRole`
  compartidos intactos.
- **Lab04:** servicio ECS `cloudlab-erik-api` en `desired=0`, `running=0`.
- **Lab05:** infraestructura desactivada mediante variables locales.
- **Lab07:** instancia EC2 terminada y recursos destruidos; VM local apagada.
- No hay instancias EC2 en ejecución.

## Cómo revisar un laboratorio

Cada README explica los requisitos, la ejecución local, el despliegue y las
evidencias. Para el Laboratorio 01:

```bash
cd 01-circuit-breaker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -v
docker compose up --build -d
bash scripts/demo.sh
docker compose down
```

## Entregables

Cada laboratorio incluye:

- Descripción de la solución y diagrama de arquitectura.
- Código y configuración.
- Instrucciones de ejecución local y en AWS.
- Pruebas automatizadas.
- Evidencias reales (logs, capturas y salidas de comandos).
- Resultados y limitaciones.

## Referencias

- Documentación de AWS: <https://docs.aws.amazon.com/>
- Terraform AWS Provider: <https://registry.terraform.io/providers/hashicorp/aws/latest>
- PyBreaker: <https://github.com/danielfm/pybreaker>
- FastAPI: <https://fastapi.tiangolo.com/>
