# Arquitectura del Laboratorio 01 — Circuit Breaker

## Vista general

La solución tiene dos microservicios FastAPI. El **cliente** es el único
expuesto al usuario y envuelve cada llamada al **backend** con un Circuit
Breaker de PyBreaker. El backend simula una dependencia que puede fallar.

```mermaid
flowchart LR
  U[Usuario / curl] -->|HTTP :8000| C[Cliente FastAPI]
  C -->|HTTPX :8001| B[Backend FastAPI]
  C -.->|PyBreaker| CB((Circuit Breaker))
  B --> S[(Contador en memoria)]
  C --> L[Event log de transiciones]
```

En Docker Compose los servicios se comunican por la red `lab01` con el nombre
`backend`. En AWS ambos contenedores comparten la red de la tarea Fargate y el
cliente usa `http://127.0.0.1:8001`.

## Máquina de estados

```mermaid
stateDiagram-v2
  [*] --> CLOSED
  CLOSED --> CLOSED: éxito (fail_counter = 0)
  CLOSED --> CLOSED: fallo (fail_counter < 3)
  CLOSED --> OPEN: 3 fallos consecutivos
  OPEN --> OPEN: petición antes de 10 s\n(rechazo sin llamar al backend)
  OPEN --> HALF_OPEN: petición después de 10 s
  HALF_OPEN --> CLOSED: llamada de prueba exitosa
  HALF_OPEN --> OPEN: llamada de prueba fallida
```

Parámetros:

| Parámetro | Valor | Implementación |
|---|---|---|
| `fail_max` | 3 | `pybreaker.CircuitBreaker(fail_max=3, ...)` |
| `reset_timeout` | 10 s | Temporizador de PyBreaker basado en `datetime.now(UTC)`. |
| `success_threshold` | 1 | Un éxito en `HALF-OPEN` cierra el circuito. |
| Timeout HTTP | 2 s | `httpx.Client(timeout=2.0)`. |

PyBreaker no ejecuta un temporizador en segundo plano: el paso de `OPEN` a
`HALF-OPEN` ocurre cuando llega una petición después del `reset_timeout`. Por
eso la demo espera 11 segundos antes de la llamada de recuperación.

## Flujo de una petición

```mermaid
sequenceDiagram
  participant U as Usuario
  participant C as Cliente
  participant CB as Circuit Breaker
  participant B as Backend

  U->>C: GET /request?scenario=ok
  C->>CB: call(call_backend, "ok")
  alt Circuito CLOSED o HALF-OPEN
    CB->>B: GET /work?scenario=ok
    alt 200
      B-->>CB: 200 OK
      CB-->>C: resultado
      C-->>U: 200 + breaker=CLOSED
    else 500 o timeout
      B-->>CB: 500 / error
      CB->>CB: fail_counter += 1
      CB-->>C: BackendError
      C-->>U: 502 + breaker=CLOSED/OPEN
    end
  else Circuito OPEN
    CB-->>C: CircuitBreakerError
    C-->>U: 503 + reason=timeout_not_elapsed
  end
```

Puntos clave:

- El backend se invoca **solo** si el breaker lo permite. Mientras está `OPEN`,
  el cliente responde `503` sin abrir una conexión HTTP.
- Un `500` del backend se convierte en `BackendError`, que PyBreaker contabiliza
  como fallo.
- La llamada que alcanza el tercer fallo devuelve `503` con
  `reason=threshold_reached`; las siguientes devuelven `503` con
  `reason=timeout_not_elapsed`.
- El listener `TransitionListener` guarda cada cambio de estado con timestamp y
  `fail_counter`; se expone en `/breaker/status` y se registra en los logs.

## Componentes

| Componente | Responsabilidad |
|---|---|
| `client/main.py` | API pública, llamada HTTPX y traducción de errores a `502`/`503`. |
| `client/breaker.py` | Instancia única de PyBreaker, parámetros y listener de transiciones. |
| `backend/main.py` | Respuestas controladas `200`/`500` y contador de peticiones. |
| `compose.yaml` | Red interna y publicación del cliente en `127.0.0.1:8091`. |
| `scripts/demo.sh` | Secuencia reproducible con aserciones de estado y de contador. |
| Terraform | ECR, Security Group, task definition, servicio ECS y log groups. |

## Despliegue en AWS

```mermaid
flowchart TB
  subgraph AWS[AWS Academy — us-east-1]
    ECR1[ECR client] --> TD
    ECR2[ECR backend] --> TD
    subgraph ECS[Cluster cloudlab-erik-cluster]
      subgraph T[Task Fargate 0.5 vCPU / 1 GB]
        CL[client :8000]
        BE[backend :8001]
        CL -->|127.0.0.1:8001| BE
      end
    end
    SG[Security Group :8000] --> CL
    TD[Task definition] --> T
    CL --> CW1[CloudWatch /ecs/...-client]
    BE --> CW2[CloudWatch /ecs/...-backend]
  end
  U[IP autorizada /32] --> SG
  TF[Terraform] -.->|crea| ECR1
  TF -.->|crea| ECR2
  TF -.->|crea| SG
  TF -.->|crea| TD
  TF -.->|crea| CW1
  TF -.->|crea| CW2
  TF -.->|reutiliza data sources| ECS
```

Decisiones de infraestructura:

- **Estado Terraform independiente:** evita que un `destroy` afecte a los
  laboratorios 04, 05 o 07.
- **Data sources para recursos compartidos:** VPC, subredes, cluster y
  `LabRole` se consultan, no se administran.
- **Una sola tarea Fargate:** mantiene el estado del breaker en un único
  proceso y reduce el costo.
- **Dos contenedores en la misma tarea:** permite usar `localhost` y evita un
  ALB o Service Discovery.
- **IP pública temporal:** simplifica el acceso de demostración; el Security
  Group limita el puerto 8000 a una IPv4 `/32`.
- **CloudWatch Logs con retención de 3 días:** suficiente para las evidencias y
  de bajo costo.

## Alternativas descartadas

| Alternativa | Motivo para no usarla |
|---|---|
| Implementar la máquina de estados a mano | PyBreaker ya resuelve concurrencia, contadores y transiciones; el objetivo es demostrar el patrón, no reescribir la librería. |
| Varias réplicas del cliente | El estado en memoria se fragmentaría y la demo dejaría de ser determinista. |
| ALB o Service Discovery | Innecesarios para dos contenedores en la misma tarea; agregan costo y complejidad. |
| Reintentos automáticos | Corresponden al Laboratorio 02 y ocultarían el efecto del breaker. |
| Estado distribuido en Redis | Fuera del alcance de una práctica de una sola tarea; se documenta como limitación. |
