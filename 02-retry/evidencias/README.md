# Evidencias — Laboratorio 02: Retry Pattern

Todas las evidencias se generaron ejecutando comandos reales. No se
fabricaron respuestas ni se simularon resultados para el informe.

## Índice

| N.º | Archivo | ¿Qué demuestra? | Estado |
|---|---|---|---|
| 01 | `01-pytest.txt` | Suite automatizada aprobada: 25 pruebas | ✅ |
| 02 | `02-docker-ps.txt` | Dos contenedores en ejecución y healthy | ✅ |
| 03 | `03-normal-operation.txt` | Operación exitosa con un solo intento | ✅ |
| 04 | `04-retry-recovery.txt` | Dos fallos 503 y recuperación con 200 en el tercer intento | ✅ |
| 05 | `05-retry-exhausted.txt` | Tres intentos y error final controlado | ✅ |
| 06 | `06-no-retry-400.txt` | HTTP 400 sin reintentos | ✅ |
| 07 | `07-exponential-backoff.txt` | Esperas de 0.5 s y 1.0 s | ✅ |
| 08 | `08-backend-stats.txt` | Contadores del backend coinciden con los intentos | ✅ |
| 09 | `09-terraform-validate.txt` | Configuración Terraform válida | ✅ |
| 10 | `10-terraform-plan.txt` | 2 recursos ECR y 6 recursos runtime planificados | ✅ |
| 11 | `11-terraform-apply.txt` | ECR, imágenes y runtime ECS creados y verificados | ✅ |
| 12 | `12-ecs.png` / `12-ecs.txt` | Salida real de AWS CLI sobre la tarea ECS; PNG renderizado | ✅ |
| 13 | `13-aws-demo.txt` | Retry ejecutado contra Fargate, con contadores del backend | ✅ |
| 14 | `14-cloudwatch.txt` | Logs reales de cliente y backend en CloudWatch | ✅ |
| 15 | `15-terraform-destroy.txt` | 6 recursos runtime y 2 repositorios ECR destruidos | ✅ |

## Las cuatro evidencias más importantes

### Figura 1. Recuperación mediante Retry

`04-retry-recovery.txt` muestra la secuencia real:

```text
Intento 1 → HTTP 503
Intento 2 → HTTP 503
Intento 3 → HTTP 200
```

El cliente responde `attempts=3`, `retries=2`, `recovered=true` y
`waits=[0.5, 1.0]`. El backend registra exactamente tres solicitudes.

### Figura 2. Agotamiento de reintentos

`05-retry-exhausted.txt` muestra tres respuestas 503 y un error final
controlado. El backend registra tres solicitudes, no cuatro. El cliente
responde `attempts=3`, `retries=2`, `recovered=false`.

### Figura 3. Exponential Backoff

`07-exponential-backoff.txt` muestra las esperas configuradas `[0.5, 1.0]` y
los intervalos reales entre intentos, aproximadamente `0.512 s` y `1.032 s`.
El intervalo crece, por lo que no se trata de reintentos inmediatos.

### Figura 4. Ejecución en AWS

La tarea Fargate real quedó `RUNNING` y `HEALTHY` con los contenedores
`backend` y `client`. La evidencia `13-aws-demo.txt` repite los escenarios
contra la IP pública `13.218.98.224` y confirma con los contadores del backend:

```text
transient   → 200 con intentos [503, 503, 200]
permanent   → 503 con intentos [503, 503, 503]
bad_request → 400 con un solo intento
backoff     → 200 con intentos [503, 503, 200]
```

`14-cloudwatch.txt` contiene los logs reales de ambos contenedores. Allí se
observan los intentos `retryable` 1 y 2, el intento 3 `success`, y las
peticiones `request=1`, `request=2`, `request=3` del backend con el mismo
`run_id`.

`12-ecs.png` es un **renderizado de la salida real de AWS CLI** guardada en
`12-ecs.txt`; no es una captura de la consola web de AWS. El texto crudo
incluye la identidad, el servicio, la tarea, los contenedores, la task
definition, la interfaz de red y una prueba HTTP real.

## Detalle de la demostración local

La demo se ejecutó con:

```bash
docker compose up --build -d
bash scripts/demo.sh
```

| Escenario | HTTP final | Intentos | Reintentos | Backend |
|---|---|---|---|---|
| `success` | 200 | 1 | 0 | 1 solicitud |
| `transient` | 200 | 3 | 2 | 503, 503, 200 |
| `permanent` | 503 | 3 | 2 | 503, 503, 503 |
| `bad_request` | 400 | 1 | 0 | 400 |
| `transient` (backoff) | 200 | 3 | 2 | 503, 503, 200 |

Los contadores del backend se consultan con `GET /backend/stats?run_id=...`,
que no aplica reintentos ni incrementa los contadores.

## Detalle de la ejecución en AWS

| Elemento | Valor real |
|---|---|
| Cuenta / región | `533267299755` / `us-east-1` |
| Servicio | `cloudlab-erik-retry-service`, `ACTIVE` |
| Tarea | `RUNNING`, `HEALTHY`, 512 CPU / 1024 MiB |
| Contenedores | `backend` y `client`, ambos `HEALTHY` |
| IP pública | `13.218.98.224` |
| Task definition | `cloudlab-erik-retry:1` |
| Red | `awsvpc`, VPC por defecto `vpc-0bfdd39b2f8f6f14b` |
| Security Group | `cloudlab-erik-retry-client-sg`, puerto 8000 desde la IP autorizada |
| Logs | `/ecs/cloudlab-erik-retry-client` y `/ecs/cloudlab-erik-retry-backend` |

La prueba HTTP real de `12-ecs.txt` devolvió HTTP 200 con `attempts=3`,
`retries=2`, `recovered=true` y esperas `[0.5, 1.0]`.

## Verificación de la suite

```text
25 passed, 1 warning in 0.51s
```

La advertencia proviene de Starlette TestClient y no afecta el resultado.

## Terraform

- `09-terraform-validate.txt` contiene la validación de `terraform/ecr` y
  `terraform/runtime`.
- `10-terraform-plan.txt` contiene los planes de ambos estados: 2 recursos
  ECR y 6 recursos runtime.
- `11-terraform-apply.txt` contiene la creación de los repositorios ECR, la
  construcción y publicación de las imágenes `linux/amd64`, la creación del
  runtime ECS y la verificación del servicio y la tarea.
- `15-terraform-destroy.txt` contiene la destrucción real: 6 recursos de
  runtime y 2 repositorios ECR.

Los estados de Terraform, los planes y los `terraform.tfvars` no se versionan.

## Limpieza

Al finalizar se destruyen primero los recursos de runtime y después los
repositorios ECR. Los repositorios usan `force_delete = true` para poder
eliminarlos aunque contengan las imágenes publicadas. La evidencia `15`
incluye la salida real de ambos `terraform destroy` y la verificación
posterior:

- Servicio ECS `INACTIVE`, con `desired=0` y `running=0`.
- Sin tareas en ejecución.
- Clúster ECS `INACTIVE`, sin servicios activos ni tareas.
- Task definition `cloudlab-erik-retry:1` en estado `INACTIVE` (AWS conserva
  las definiciones deregistradas, no las elimina).
- Repositorios ECR eliminados.
- Log groups eliminados.
- Security Group eliminado.
- Sin interfaces de red asociadas al Security Group.
- Estado Terraform vacío en ambos directorios.
- VPC por defecto y `LabRole` compartidos intactos.

## Integración en GitHub

El laboratorio se integró en la rama `erik/practicas` mediante el
[PR #11](https://github.com/L4Ta-10001001/cloud-patterns-lab/pull/11). El flujo
de revisión y la incorporación a `main` se documentan en el `README.md`
principal del repositorio.
