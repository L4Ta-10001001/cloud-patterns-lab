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
| `06-ecr.png` | Captura real de consola: ECR -> repositorio -> pestaña **Images**, tag `v1` y digest `sha256:9383dc4d...`. |
| `07-ecs.txt` | Servicio `ACTIVE`, tarea `RUNNING` y su IP publica. |
| `07-ecs.png` | Captura real de consola: cluster `cloudlab-erik-cluster` -> **Services**, `cloudlab-erik-api` activo con `2/2 Tasks running`. |
| `08-ecs-http.txt` | Respuesta HTTP desde la IP publica de la tarea Fargate. |
| `09-lambda.png` | Captura real de consola: funcion `cloudlab-erik-lambda`, runtime `python3.12` y handler `lambda_function.lambda_handler`. |

Las capturas `06` y `07` provienen de la consola AWS real y muestran las vistas
correctas (tag de imagen y tareas en ejecucion). No se usaron imagenes inventadas.
