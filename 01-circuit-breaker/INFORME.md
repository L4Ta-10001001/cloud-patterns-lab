# Informe — Laboratorio 01: Circuit Breaker

## Pregunta de investigación

**¿Cómo se implementó el patrón Circuit Breaker en la solución y qué demuestra
su ejecución real?**

Este informe responde desde la implementación y la evidencia obtenida; la
fundamentación teórica del patrón se desarrolla en el documento de
investigación del laboratorio.

## 1. Solución implementada

Se construyeron dos microservicios FastAPI:

- **Cliente (`client`)**: expone la API que consume el usuario y protege la
  llamada al backend con una instancia de `pybreaker.CircuitBreaker`.
- **Backend (`backend`)**: simula una dependencia externa. Responde `200` o
  `500` según el parámetro `scenario` y lleva un contador de peticiones
  recibidas.

El cliente no reimplementa la máquina de estados. Usa PyBreaker 1.4.x con esta
configuración:

```python
pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=10,
    success_threshold=1,
    name="backend",
)
```

La llamada protegida es una función que usa HTTPX con timeout de 2 segundos:

```python
response = httpx.get(f"{BACKEND_URL}/work", params={"scenario": scenario}, timeout=2.0)
if response.status_code >= 500:
    raise BackendError(...)
```

Así, tanto un `500` como un timeout o un error de red se contabilizan como
fallo. Un `200` reinicia el contador de fallos.

### Traducción a respuestas HTTP

| Situación | Excepción | Respuesta del cliente |
|---|---|---|
| Backend responde `200` | — | `200` |
| Backend responde `500` | `BackendError` | `502` |
| Timeout o error de red | `httpx.HTTPError` | `502` |
| Circuito abierto al alcanzar el umbral | `CircuitBreakerError` | `503` + `threshold_reached` |
| Rechazo con el circuito ya abierto | `CircuitBreakerError` | `503` + `timeout_not_elapsed` |
| Falla la llamada de prueba en `HALF-OPEN` | `CircuitBreakerError` | `503` + `trial_call_failed` |

Esta separación es importante: un `502` indica que el backend **fue llamado y
falló**; un `503` indica que el breaker **impidió la llamada**. El campo
`reason` permite distinguir ambos casos en las evidencias.

### Observabilidad

Un `TransitionListener` registra cada cambio de estado con:

- estado anterior y nuevo,
- timestamp UTC,
- valor de `fail_counter`.

Los eventos se exponen en `GET /breaker/status` y se escriben en los logs del
contenedor. Esto permitió reconstruir la secuencia real:

```text
closed -> open -> half-open -> closed
```

El backend expone `GET /stats` con el total de peticiones. Esta es la prueba
objetiva de que, mientras el circuito está `OPEN`, el backend no recibe ninguna
llamada nueva.

## 2. Demostración de los tres estados

La secuencia ejecutada por `scripts/demo.sh` es:

1. **CLOSED:** una petición `ok` devuelve `200` y el backend registra 1 llamada.
2. **CLOSED con fallos:** tres peticiones `fail` producen `502`, `502` y `503`.
   En la tercera, PyBreaker alcanza `fail_max=3` y abre el circuito.
3. **OPEN:** una petición `ok` devuelve `503` con
   `reason=timeout_not_elapsed`. El contador del backend no cambia.
4. **HALF-OPEN:** tras 11 segundos, una petición `ok` dispara la transición
   `open -> half-open`; como el backend responde `200`, el circuito pasa a
   `closed`.
5. **CLOSED recuperado:** las peticiones vuelven a pasar con normalidad.

El script usa `set -euo pipefail` y compara explícitamente los estados y el
contador del backend. Si una aserción falla, termina con código distinto de
cero; no es una secuencia de `curl` sin verificación.

## 3. Pruebas automatizadas

Se ejecutaron **16 pruebas**, todas aprobadas:

| Grupo | Cantidad | Cobertura |
|---|---|---|
| Estados del breaker | 8 | Operación normal, fallo 1, fallo 2, apertura, rechazo sin llamada, `HALF-OPEN` exitoso, `HALF-OPEN` fallido y recuperación. |
| Endpoints del cliente | 6 | `/health`, `200`, `502`, `503`, rechazo sin backend y estado expuesto. |
| Integración | 2 | Cliente y backend reales, contador sin cambios durante `OPEN`. |

Las pruebas de estados usan un reloj simulado que reemplaza
`pybreaker.datetime`. Esto permite avanzar 10 segundos sin `sleep` reales y
hace la suite rápida y determinista. La prueba de integración usa el backend
real mediante `TestClient` y comprueba el contador antes y después del rechazo:

```python
assert backend_main.stats()["total"] == 4
rechazada = client.get("/request", params={"scenario": "ok"})
assert rechazada.status_code == 503
assert backend_main.stats()["total"] == 4   # el backend no recibió la llamada
```

## 4. Ejecución real en Docker y AWS

### Docker Compose

Los dos contenedores se construyeron con `python:3.12-slim`. El cliente se
publicó en `127.0.0.1:8091` y el backend quedó solo en la red interna. La demo
local reprodujo la secuencia completa y guardó las evidencias `03` a `06`.

### Amazon ECS Fargate

Terraform creó 7 recursos: 2 repositorios ECR, 2 log groups, 1 Security Group,
1 task definition y 1 servicio ECS. La tarea Fargate ejecutó ambos contenedores
con `desired_count=1`; el cliente usó `http://127.0.0.1:8001` para comunicarse
con el backend dentro de la misma tarea.

La misma demo se ejecutó contra la IP pública de la tarea. Los resultados
remotos fueron idénticos a los locales:

- `200` en operación normal.
- `502`, `502`, `503` en los tres fallos.
- `503` con `timeout_not_elapsed` y contador del backend sin cambios.
- `200` tras la recuperación `HALF-OPEN`.
- Contador final del backend: `{"total": 5, "ok": 2, "fail": 3}`.

CloudWatch mostró las peticiones del cliente y confirmó que el backend solo
recibió las llamadas permitidas por el breaker.

## 5. Qué demuestra la solución

1. **El patrón funciona con una librería especializada:** PyBreaker gestiona
   los contadores, el timeout y las transiciones; el código de negocio solo
   define la operación protegida y traduce excepciones a respuestas HTTP.
2. **Los tres estados son observables:** no se infieren de la teoría; se
   verifican con `/breaker/status`, con los eventos del listener y con los
   códigos HTTP.
3. **El fast-fail es real:** durante `OPEN`, el backend no recibe ninguna
   petición. El contador `/stats` es la prueba, no solo el código `503`.
4. **La recuperación es controlada:** tras el `reset_timeout`, una única
   llamada de prueba decide entre cerrar el circuito o volver a abrirlo.
5. **La solución es reproducible:** las mismas imágenes y el mismo script
   funcionan en Docker Compose y en ECS Fargate, con la única diferencia de la
   URL del backend (`backend:8001` vs. `127.0.0.1:8001`).
6. **La infraestructura es aislada:** Terraform reutiliza la VPC, las subredes,
   el cluster y `LabRole` mediante data sources, y destruye solo sus 7 recursos
   al finalizar.

## 6. Limitaciones

- El estado del breaker es local al proceso. Con varias tareas o réplicas,
  cada una tendría su propio circuito; una implementación distribuida
  necesitaría un almacén compartido como Redis.
- La tarea Fargate tiene IP pública para facilitar la demostración. En
  producción se usaría un ALB y subredes privadas.
- El backend es simulado y el fallo se activa con un parámetro; no se prueba
  contra una dependencia externa real.
- No hay reintentos ni fallback: el laboratorio se concentra en el corte del
  circuito. Esas políticas corresponden a otros patrones del curso.
- La ventana de 10 segundos es adecuada para la demo, pero en un sistema real
  se calibraría con métricas de latencia y tasa de error.

## 7. Conclusión

La solución implementa el Circuit Breaker con PyBreaker y demuestra, con
pruebas automatizadas y ejecución real en Docker y ECS Fargate, que el cliente
deja de llamar a un backend que falla, rechaza las peticiones mientras el
circuito está abierto y se recupera de forma controlada mediante una llamada de
prueba. La evidencia del contador del backend confirma que el `503` por
circuito abierto no es un fallo del backend, sino una decisión deliberada del
cliente para protegerlo y proteger al usuario.
