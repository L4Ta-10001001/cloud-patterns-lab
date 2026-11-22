# Laboratorio 01 — Circuit Breaker con FastAPI, Docker y AWS

**Responsable:** Erik · **Estado:** Completado e integrado · **Proyecto:** Cloud Patterns Lab

**Rama de desarrollo:** `erik/circuit-breaker` · **Integración:** PR #3 → `erik/practicas` → PR #4 → `main`

## Objetivo

Implementar el patrón **Circuit Breaker** en un cliente HTTP que consume un
backend simulado, demostrar sus tres estados (`CLOSED`, `OPEN`, `HALF-OPEN`) y
ejecutar la misma solución en Docker Compose y en Amazon ECS Fargate.

La implementación usa **PyBreaker 1.4.x** en lugar de reimplementar la máquina
de estados. El cliente es un microservicio FastAPI; el backend es un segundo
microservicio que puede responder correctamente o fallar de forma controlada.

## Integración y estado final

El laboratorio se desarrolló en `erik/circuit-breaker` y se integró con el
flujo acordado del repositorio:

1. **PR #3:** [`erik/circuit-breaker` → `erik/practicas`](https://github.com/L4Ta-10001001/cloud-patterns-lab/pull/3) (mergeado).
2. **PR #4:** [`erik/practicas` → `main`](https://github.com/L4Ta-10001001/cloud-patterns-lab/pull/4) (mergeado).

El [PR directo #2](https://github.com/L4Ta-10001001/cloud-patterns-lab/pull/2)
a `main` se cerró para respetar la integración por `erik/practicas`. El código
y las evidencias finales están en `main`.

Los 12 criterios de aceptación se verificaron: estructura en rama
independiente, dos microservicios, PyBreaker, tres estados, pruebas, dos
contenedores, demo reproducible, Terraform, ECS Fargate, evidencias,
publicación en GitHub y eliminación de los recursos AWS.

## Arquitectura

### Ejecución local

```text
Navegador / curl
       |
       | HTTP 127.0.0.1:8091
       v
+-----------------------------+        HTTP http://backend:8001
|  client (FastAPI :8000)     |  -------------------------------->  +----------------------+
|  PyBreaker + HTTPX          |                                     |  backend (FastAPI    |
|  fail_max=3                 |  <--------------------------------  |  :8001)              |
|  reset_timeout=10 s         |        200 / 500                    |  /work /stats        |
+-----------------------------+                                     +----------------------+
              \                                                            /
               \------------------ red Docker `lab01` -------------------/
```

### Ejecución en AWS

```text
Tu IP pública /32
       |
       | HTTP :8000 (Security Group)
       v
+---------------------------------------------------------------+
|  Tarea ECS Fargate (awsvpc, 0.5 vCPU, 1 GB)                   |
|                                                               |
|   +---------------------------+    http://127.0.0.1:8001      |
|   | contenedor client :8000   |  -----------------------+      |
|   | PyBreaker + HTTPX         |                         v      |
|   +---------------------------+                  +------------------+
|                                                  | contenedor       |
|                                                  | backend :8001    |
|                                                  +------------------+
+---------------------------------------------------------------+
        |                                   |
        v                                   v
  Amazon ECR (2 imágenes)            CloudWatch Logs (2 grupos)
```

La tarea usa una subred pública con IP pública temporal **solo para la
demostración**. No hay Application Load Balancer ni Service Discovery: los dos
contenedores comparten la red de la tarea y el cliente llama al backend por
`127.0.0.1`. El Security Group limita el puerto 8000 a la IPv4 `/32`
configurada.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.12 | Imagen base de ambos contenedores. |
| FastAPI + Uvicorn | API de cliente y backend. |
| PyBreaker 1.4.x | Máquina de estados del Circuit Breaker. |
| HTTPX | Llamadas HTTP del cliente al backend, con timeout de 2 s. |
| Pytest | Pruebas unitarias y de integración. |
| Docker Compose | Ejecución local de los dos contenedores. |
| Terraform 1.15 | ECR, Security Group, task definition, servicio ECS y log groups. |
| Amazon ECR / ECS Fargate / CloudWatch | Registro de imágenes, ejecución y logs. |

## Estructura

```text
01-circuit-breaker/
├── backend/
│   ├── Dockerfile
│   ├── main.py              # /health, /work, /stats
│   └── requirements.txt
├── client/
│   ├── Dockerfile
│   ├── breaker.py           # configuración de PyBreaker y listener
│   ├── main.py              # /health, /request, /breaker/status
│   └── requirements.txt
├── tests/
│   ├── conftest.py          # reloj simulado y reinicio de estado
│   ├── test_breaker.py      # 8 escenarios de los estados
│   ├── test_client.py       # endpoints y códigos 502/503
│   └── test_integration.py  # cliente + backend y contador real
├── scripts/
│   └── demo.sh              # demostración reproducible con aserciones
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   ├── variables.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
├── evidencias/
├── compose.yaml
├── requirements-dev.txt
├── ARQUITECTURA.md
├── INFORME.md
└── README.md
```

## Ejecución local

### 1. Pruebas automatizadas

```bash
cd 01-circuit-breaker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Las pruebas no esperan 10 segundos reales: reemplazan `pybreaker.datetime` por
un reloj controlado. La prueba de integración comprueba además que el contador
del backend **no aumenta** mientras el circuito está `OPEN`.

### 2. Contenedores

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8091/health
```

El backend no publica puertos al host; solo es accesible desde la red interna
`lab01`. El cliente se publica en `127.0.0.1:8091` para no exponerlo en la red
local.

### 3. Demostración completa

```bash
bash scripts/demo.sh
```

El script espera a `/health`, ejecuta la secuencia normal, provoca tres fallos,
verifica el rechazo sin llamada al backend, espera 11 segundos y comprueba la
recuperación por `HALF-OPEN`. Falla con código distinto de cero si alguna
aserción no se cumple. Las salidas se guardan en `evidencias/03` a `06`.

Para detener el entorno local:

```bash
docker compose down
```

## Endpoints

### Cliente (`:8000` en el contenedor, `:8091` en local)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio y del circuito. |
| GET | `/request?scenario=ok\|fail` | Llama al backend a través del breaker. |
| GET | `/breaker/status` | Estado, contadores, configuración y transiciones. |
| GET | `/backend/stats` | Diagnóstico: lee `/stats` del backend sin pasar por el breaker. |

### Backend (`:8001`, solo red interna)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del backend. |
| GET | `/work?scenario=ok\|fail` | Responde `200` o `500` de forma controlada. |
| GET | `/stats` | Total de peticiones recibidas, separadas por escenario. |

## Comportamiento del Circuit Breaker

Configuración en `client/breaker.py`:

| Parámetro | Valor | Efecto |
|---|---|---|
| `fail_max` | 3 | Tres fallos consecutivos abren el circuito. |
| `reset_timeout` | 10 s | Tiempo mínimo antes de permitir una llamada de prueba. |
| `success_threshold` | 1 | Un éxito en `HALF-OPEN` cierra el circuito. |
| Timeout HTTP | 2 s | Una llamada lenta también se contabiliza como fallo. |

Estados:

1. **CLOSED:** todas las llamadas pasan. Cada fallo incrementa el contador;
   un éxito lo reinicia.
2. **OPEN:** el cliente rechaza la petición sin llamar al backend. Al cumplirse
   los 10 segundos, la siguiente petición intenta la transición a `HALF-OPEN`
   (PyBreaker no usa un temporizador en segundo plano).
3. **HALF-OPEN:** se permite una llamada de prueba. Si tiene éxito, vuelve a
   `CLOSED`; si falla, vuelve a `OPEN` y reinicia el período de 10 segundos.

### Códigos HTTP del cliente

| Código | Significado | Cuándo ocurre |
|---|---|---|
| `200` | Operación correcta | El backend respondió `200`. |
| `502` | Fallo del backend | El backend respondió `5xx` o hubo un error de red/timeout. |
| `503` | Circuito abierto | El breaker rechazó la llamada; el backend no fue invocado. |

La respuesta `503` incluye un campo `reason`:

- `threshold_reached`: la llamada que alcanzó el tercer fallo abrió el circuito.
- `timeout_not_elapsed`: rechazo inmediato mientras el circuito sigue `OPEN`.
- `trial_call_failed`: la llamada de prueba de `HALF-OPEN` volvió a fallar.

Esta distinción permite demostrar que un `503` por circuito abierto es distinto
de un `502` por fallo del backend.

## Pruebas automatizadas

Resultado real: **16 pruebas aprobadas**.

| Archivo | Pruebas | Qué verifica |
|---|---|---|
| `tests/test_breaker.py` | 8 | Operación normal, fallo 1, fallo 2, apertura en el fallo 3, rechazo sin llamada, `HALF-OPEN` exitoso, `HALF-OPEN` fallido y operación tras recuperarse. |
| `tests/test_client.py` | 6 | `/health`, solicitud correcta, `502` por fallo, `503` al abrir, rechazo sin backend y estado expuesto. |
| `tests/test_integration.py` | 2 | Flujo completo con el backend real y contador sin cambios durante `OPEN`; contadores iniciales del backend. |

La salida completa está en `evidencias/01-pytest.txt`.

## Despliegue en AWS con Terraform

### Requisitos

- Credenciales temporales del Learner Lab en un perfil local (`AWS_PROFILE`).
- `LabRole` existente.
- Docker, AWS CLI y Terraform instalados.
- Una VPC con subredes públicas y un cluster ECS reutilizables. El laboratorio
  usa por defecto `cloudlab-erik-vpc` y `cloudlab-erik-cluster`.

El estado de Terraform es **independiente** del resto de laboratorios. La VPC,
las subredes, el cluster y `LabRole` se consultan con `data` sources; este
estado nunca los crea ni los destruye.

### Fase 1: validar y planificar

```bash
cd 01-circuit-breaker/terraform
cp terraform.tfvars.example terraform.tfvars
# Editar allowed_cidr con: curl -4 https://checkip.amazonaws.com
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan
```

### Fase 2: crear repositorios ECR y publicar imágenes

```bash
terraform apply -auto-approve \
  -target=aws_ecr_repository.client \
  -target=aws_ecr_repository.backend

CLIENT_REPO=$(terraform output -raw client_repository_url)
BACKEND_REPO=$(terraform output -raw backend_repository_url)
REGISTRY=${CLIENT_REPO%%/*}

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "$REGISTRY"

cd ..
docker build -t "$CLIENT_REPO:v1" ./client
docker build -t "$BACKEND_REPO:v1" ./backend
docker push "$CLIENT_REPO:v1"
docker push "$BACKEND_REPO:v1"
```

### Fase 3: crear el servicio Fargate

```bash
cd terraform
terraform apply -auto-approve
```

Terraform crea **7 recursos**:

- 2 repositorios ECR.
- 2 grupos de CloudWatch Logs.
- 1 Security Group.
- 1 task definition con dos contenedores.
- 1 servicio ECS con `desired_count = 1`.

La tarea ejecuta los contenedores `client` y `backend` en la misma red
`awsvpc`. El cliente recibe `BACKEND_URL=http://127.0.0.1:8001`.

### Fase 4: probar la tarea

```bash
CLUSTER=cloudlab-erik-cluster
SERVICE=cloudlab-erik-lab01-circuit-breaker

TASK=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name "$SERVICE" \
  --query 'taskArns[0]' --output text)
ENI=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)
IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

curl "http://$IP:8000/health"
CLIENT_URL="http://$IP:8000" EVID_DIR=/tmp/lab01-aws bash scripts/demo.sh
```

La misma demo se ejecutó contra la tarea Fargate y produjo los mismos estados
que en local. La evidencia está en `evidencias/11-aws-demo.txt`; los logs de los
dos contenedores están en `evidencias/12-cloudwatch.txt`.

### Limpieza

```bash
cd terraform
terraform destroy
```

El `destroy` se ejecutó al finalizar la demostración y eliminó **7 recursos**.
La verificación posterior confirmó:

- servicio ECS `INACTIVE`, `desired=0`, `running=0`;
- sin tareas, repositorios ECR, log groups ni Security Group del laboratorio;
- clúster, VPC, subredes y `LabRole` compartidos intactos;
- estado Terraform vacío.

La salida completa está en `evidencias/13-terraform-destroy.txt`.

## Resultados reales

- **Pruebas:** 16/16 aprobadas.
- **Local:** `200` en operación normal, dos `502` por fallos consecutivos, `503`
  al abrir el circuito, `503` sin incrementar el contador del backend y `200`
  tras la recuperación `HALF-OPEN`.
- **AWS:** la tarea Fargate quedó `RUNNING` con los dos contenedores; la demo
  remota repitió exactamente la misma secuencia.
- **Backend:** recibió 4 peticiones durante la fase de fallos (`1 ok`, `3 fail`),
  ninguna durante el rechazo y 1 más después de la recuperación (total 5).
- **Transiciones observadas:** `closed → open → half-open → closed`.
- **Limpieza:** 7/7 recursos destruidos; servicio ECS `INACTIVE`; sin restos
  del laboratorio y con el lab04 intacto (`desired=0`).
- **Integración:** PR #3 (`erik/circuit-breaker` → `erik/practicas`) y PR #4
  (`erik/practicas` → `main`) mergeados.

## Estado de aceptación

| Criterio | Estado |
|---|---|
| Estructura en rama independiente | ✅ `erik/circuit-breaker` |
| Dos microservicios FastAPI | ✅ |
| Circuit Breaker con PyBreaker | ✅ |
| Estados `CLOSED`, `OPEN` y `HALF-OPEN` | ✅ |
| Pruebas automatizadas | ✅ 16/16 |
| Dos contenedores Docker | ✅ |
| Demostración reproducible con script | ✅ `scripts/demo.sh` |
| Terraform validado y desplegado en AWS | ✅ |
| Ejecución en ECS Fargate | ✅ |
| Evidencias y diagramas | ✅ 01–13 |
| Código publicado en GitHub | ✅ PR #3 y PR #4 |
| Recursos AWS eliminados | ✅ 7 destruidos |

## Evidencias

| Archivo | Contenido |
|---|---|
| `01-pytest.txt` | Salida de las 16 pruebas. |
| `02-docker-ps.txt` | Contenedores locales en ejecución. |
| `03-normal-operation.txt` | Operación normal en `CLOSED`. |
| `04-circuit-open.txt` | Tres fallos y apertura del circuito. |
| `05-fast-fail.txt` | Rechazo inmediato sin llamada al backend. |
| `06-circuit-recovery.txt` | Recuperación `HALF-OPEN` y cierre. |
| `07-terraform-validate.txt` | `terraform validate` exitoso. |
| `08-terraform-plan.txt` | Plan con 7 recursos. |
| `09-terraform-apply.txt` | Apply completo y outputs. |
| `10-ecs.png` | Captura real del servicio ECS (22-nov-2026 03:55 UTC). |
| `11-aws-demo.txt` | Demo completa contra la tarea Fargate. |
| `12-cloudwatch.txt` | Logs de cliente y backend en CloudWatch. |
| `13-terraform-destroy.txt` | 7 recursos destruidos y verificación posterior sin restos. |

El índice detallado está en `evidencias/README.md`.

## Limitaciones y decisiones

- El estado del breaker vive en memoria del proceso. Por eso se ejecuta **una
  sola tarea** y **un solo proceso** de cliente; con varias réplicas cada una
  tendría su propio estado. Una solución distribuida requeriría un backend
  compartido (por ejemplo, Redis).
- No se implementan reintentos: el laboratorio demuestra el corte del circuito,
  no una política de retry. Los reintentos pertenecen al Laboratorio 02.
- La IP pública de la tarea es una simplificación académica. En producción se
  usaría un ALB o Service Discovery con subredes privadas.
- El backend es simulado; no representa una dependencia externa real.
- Los contenedores usan `python:3.12-slim` y un único proceso Uvicorn por
  contenedor.

## Referencias

- Michael T. Nygard, *Release It!* — patrón Circuit Breaker.
- PyBreaker: <https://github.com/danielfm/pybreaker>
- FastAPI: <https://fastapi.tiangolo.com/>
- Terraform AWS Provider: <https://registry.terraform.io/providers/hashicorp/aws/latest>
