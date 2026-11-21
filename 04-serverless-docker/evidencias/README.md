# Evidencias de la practica 04

Salidas reales de las pruebas locales y de AWS CLI. No crear evidencias ficticias,
ni subir credenciales, tokens, claves ni el estado de Terraform.

| Archivo | Evidencia |
|---|---|
| `01-pytest.txt` | Seis pruebas locales aprobadas (`6 passed`). |
| `02-docker-ps.txt` | Contenedor FastAPI ejecutandose con Docker Compose. |
| `03-http.txt` | Respuestas HTTP locales en `/health` y `/` (HTTP 200). |
| `04-terraform-validate.txt` | `fmt -check`, `validate` y `plan` sin cambios pendientes. |
| `05-lambda-invoke.json` | Resultado real de `aws lambda invoke` (statusCode 200). |
| `06-ecr.txt` | Repositorio `cloudlab-erik-api` con imagen `v1` publicada. |
| `07-ecs.txt` | Servicio `ACTIVE`, tarea `RUNNING` y su IP publica. |
| `08-ecs-http.txt` | Respuesta HTTP desde la IP publica de la tarea Fargate. |

Las evidencias `06` y `07` usan salida real de AWS CLI. Si la rubrica solicita
capturas de la consola AWS (`06-ecr.png`, `07-ecs.png`), tomarlas desde la
consola; no reemplazarlas por imagenes inventadas.
