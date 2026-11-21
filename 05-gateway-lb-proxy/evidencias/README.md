# Evidencias del laboratorio 05

Archivos reales de ejecución. No agregar resultados ficticios.

| Archivo | Estado | Evidencia |
|---|---|---|
| `01-nginx-a.txt` | ✅ | `HTTP/1.1 200 OK` en `/a/health`, `X-Backend: api-a`, `{"status":"ok"}` |
| `02-nginx-b.txt` | ✅ | `HTTP/1.1 200 OK` en `/b/health`, `X-Backend: api-b`, `{"status":"ok"}` |
| `03-nginx-ps.txt` | ✅ | Tres contenedores: `api_a`, `api_b` y `proxy` en `127.0.0.1:8090` |
| `04-terraform-plan.txt` | ⚠️ | `terraform validate` OK; `plan` bloqueado: credenciales AWS canceladas (`voc-cancel-cred`) |
| `03-api-gateway.txt` | ⏳ | Pendiente: respuesta HTTP de API Gateway tras renovar credenciales |
| `05-target-health.json` | ⏳ | Pendiente: dos destinos `healthy` del ALB |
| `06-alb-http.txt` | ⏳ | Pendiente: respuesta HTTP 200 desde el ALB |

Las fases AWS (05-A y 05-B) requieren credenciales vigentes del AWS Academy
Learner Lab. El error exacto quedó registrado en `04-terraform-plan.txt`; no se
modificaron políticas IAM.
