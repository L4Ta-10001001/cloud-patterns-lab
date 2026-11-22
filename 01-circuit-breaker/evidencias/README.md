# Evidencias — Laboratorio 01: Circuit Breaker

Todas las evidencias se generaron ejecutando los comandos reales del
laboratorio. No se incluyen credenciales, tokens, llaves privadas ni archivos
`terraform.tfvars`/estado.

| # | Archivo | Origen | Resultado |
|---|---|---|---|
| 01 | `01-pytest.txt` | `python -m pytest -v` | 16 pruebas aprobadas. |
| 02 | `02-docker-ps.txt` | `docker compose ps` | Contenedores `lab01-client` y `lab01-backend` en ejecución. |
| 03 | `03-normal-operation.txt` | `bash scripts/demo.sh` | `200` con el circuito `CLOSED`. |
| 04 | `04-circuit-open.txt` | `bash scripts/demo.sh` | `502`, `502`, `503`; circuito `OPEN`. |
| 05 | `05-fast-fail.txt` | `bash scripts/demo.sh` | `503` sin incrementar el contador del backend. |
| 06 | `06-circuit-recovery.txt` | `bash scripts/demo.sh` | `HALF-OPEN` → `CLOSED` tras 11 s. |
| 07 | `07-terraform-validate.txt` | `terraform validate` | Configuración válida. |
| 08 | `08-terraform-plan.txt` | `terraform plan` | 7 recursos a crear. |
| 09 | `09-terraform-apply.txt` | `terraform apply` | 5 recursos creados tras los 2 ECR iniciales. |
| 10 | `10-ecs.png` | Consola de AWS | Servicio `cloudlab-erik-lab01-circuit-breaker` en ECS. |
| 11 | `11-aws-demo.txt` | `CLIENT_URL=http://IP:8000 bash scripts/demo.sh` | Misma secuencia que en local, contra la tarea Fargate. |
| 12 | `12-cloudwatch.txt` | `aws logs tail` | Logs de cliente y backend; el backend solo recibió las llamadas permitidas. |
| 13 | `13-terraform-destroy.txt` | `terraform destroy` | Recursos del laboratorio eliminados. |

## Detalle de la demostración

La secuencia local y remota fue:

1. `GET /request?scenario=ok` → `200`, breaker `CLOSED`.
2. `GET /request?scenario=fail` → `502`, breaker `CLOSED` (fallo 1).
3. `GET /request?scenario=fail` → `502`, breaker `CLOSED` (fallo 2).
4. `GET /request?scenario=fail` → `503` con `reason=threshold_reached`,
   breaker `OPEN` (fallo 3).
5. `GET /request?scenario=ok` → `503` con `reason=timeout_not_elapsed`; el
   contador del backend no cambia.
6. Espera de 11 s.
7. `GET /request?scenario=ok` → `200`; transición `open → half-open → closed`.

En AWS, el contador del backend terminó en:

```json
{"total": 5, "ok": 2, "fail": 3}
```

## Captura de la consola ECS (10)

La captura se toma desde la consola de AWS, en la región `us-east-1`, con la
sesión del Learner Lab:

```text
https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/cloudlab-erik-cluster/services/cloudlab-erik-lab01-circuit-breaker?region=us-east-1
```

Debe verse el nombre del servicio, el estado `ACTIVE`, `Desired count = 1`,
`Running count = 1` y la task definition
`cloudlab-erik-lab01-circuit-breaker`. La captura se guarda como
`evidencias/10-ecs.png`.

## Limpieza (13)

Después de la captura se ejecuta `terraform destroy` desde
`01-circuit-breaker/terraform`. La salida se guarda en
`13-terraform-destroy.txt`. Este estado solo contiene los recursos del
laboratorio 01; no destruye la VPC, las subredes, el cluster ni `LabRole`
compartidos.
