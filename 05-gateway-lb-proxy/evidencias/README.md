# Evidencias del laboratorio 05

Archivos reales de ejecución. No se agregaron resultados ficticios.

| Archivo | Evidencia |
|---|---|
| `01-nginx-a.txt` | `HTTP/1.1 200 OK` en `/a/health`, `X-Backend: api-a`, `{"status":"ok"}` |
| `02-nginx-b.txt` | `HTTP/1.1 200 OK` en `/b/health`, `X-Backend: api-b`, `{"status":"ok"}` |
| `03-nginx-ps.txt` | Tres contenedores: `api_a`, `api_b` y `proxy` en `127.0.0.1:8090` |
| `03-api-gateway.txt` | HTTP 200 en `GET /health` y `GET /` de la HTTP API de API Gateway |
| `04-terraform-plan.txt` | `terraform plan` final sin cambios + `terraform output` con los recursos Lab05 |
| `05-target-health.json` | Dos destinos registrados y `healthy` en el Target Group del ALB |
| `06-alb-http.txt` | HTTP 200 en `/health` y `/` desde el DNS público del ALB |
| `07-api-gateway.png` | Captura real de consola: HTTP API `apm370rtne` -> **Stages** -> `$default` con su *Invoke URL*. |
| `08-alb.png` | Captura real de consola: ALB `cloudlab-erik-alb`, tipo *Application*, estado `Active` y DNS público. |
| `09-target-group.png` | Captura real de consola: Target Group `cloudlab-erik-tg` -> **Targets**, 2 destinos `healthy` en el puerto 8080. |

Notas:

- El error inicial por credenciales canceladas (`voc-cancel-cred`) se resolvió
  renovando el perfil `lab` de AWS CLI; no se modificaron políticas IAM.
- El tráfico hacia la API ya no entra directo al puerto 8080 del Security
  Group de ECS: solo lo hace desde el Security Group del ALB.
- Las capturas de consola AWS se tomaron desde la sesión real del Learner Lab;
  no contienen claves ni tokens de acceso.
