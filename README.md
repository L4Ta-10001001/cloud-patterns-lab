# Cloud Architecture and Design Patterns

Universidad Central del Ecuador  
Facultad de Ingeniería y Ciencias Aplicadas  
Carrera de Sistemas de Información  

**Tema:** Cloud Architecture and Design Patterns  
**Docente:** Ing. Juan Pablo Guevara  
**Integrantes:** Cueva Cesar, Herrera Erik  
**Fecha de entrega:** 2026-11-23  

Laboratorio de investigación y práctica de patrones de arquitectura cloud para la asignatura **Programación Distribuida**.

## Objetivo

Investigar y demostrar patrones de arquitectura cloud mediante implementaciones funcionales, reproducibles y documentadas, con evidencias reales de su ejecución local y en AWS.

## Estado actual

**5 de 8 laboratorios completados.**

| Lab | Tema | Estado | Documentación |
|---|---|---|---|
| 01 | Circuit Breaker | ✅ Completado | [README](01-circuit-breaker/README.md) |
| 02 | Retry | ✅ Completado | [README](02-retry/README.md) |
| 03 | Timeout | ⏳ Pendiente | [README](03-timeout/README.md) |
| 04 | Serverless y contenedores | ✅ Completado | [README](04-serverless-docker/README.md) |
| 05 | API Gateway, ALB y reverse proxy | ✅ Completado | [README](05-gateway-lb-proxy/README.md) |
| 06 | Hub-and-Spoke | ⏳ Pendiente | [README](06-hub-and-spoke/README.md) |
| 07 | Lift-and-Shift | ✅ Completado | [README](07-lift-and-shift/README.md) |
| 08 | Bastion Host | ⏳ Pendiente | [README](08-bastion/README.md) |

## Laboratorio 01 — Circuit Breaker

**¿Qué es?** Patrón de resiliencia que evita solicitudes repetitivas hacia un servicio con fallos, impidiendo fallos en cascada. Controla las solicitudes mediante tres estados: `Closed`, `Open` y `Half-Open`.

**Implementación:** Dos servicios independientes con Spring Boot y Java 17. `Restaurantes` (puerto 8080) y `Pedidos` (puerto 8081). Se utilizó Resilience4j con ventana de cuatro llamadas, umbral de fallos del 50 % y tiempo de espera de diez segundos. Cuando se alcanza el umbral, el circuito pasa a `OPEN` y `Pedidos` usa un método de respaldo (fallback). También contempla `HALF_OPEN` con hasta dos solicitudes de prueba.

**Evidencias:**

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

Documentación completa: [README del laboratorio](01-circuit-breaker/README.md), [arquitectura](01-circuit-breaker/ARQUITECTURA.md) e [informe](01-circuit-breaker/INFORME.md).

## Laboratorio 02 — Retry

**¿Qué es?** Patrón de resiliencia que repite automáticamente una operación cuando falla por un problema temporal. Estrategias: Immediate Retry, Fixed Delay, Exponential Backoff y Jitter. Los reintentos deben tener límite y usarse solo cuando sea seguro repetir la operación (idempotencia en pagos, por ejemplo).

**Implementación:** Dos microservicios con Python, FastAPI y Tenacity. Cliente y Backend independientes. Máximo de tres intentos, Exponential Backoff con esperas de 0,5 s y 1 s, timeout HTTP de 2 segundos. Reintentos limitados a errores temporales (429, 5xx, timeouts, errores de conexión); HTTP 400 no se reintenta. Probado con Docker Compose y desplegado en AWS ECS Fargate con Terraform (dos repositorios ECR, grupos de logs CloudWatch, clúster ECS, Security Group, definición de tarea y servicio ECS).

**Evidencias:**

| Resultado | Evidencia |
|---|---|
| 25 pruebas aprobadas | [01-pytest.txt](02-retry/evidencias/01-pytest.txt) |
| Dos contenedores Docker | [02-docker-ps.txt](02-retry/evidencias/02-docker-ps.txt) |
| Operación normal | [03-normal-operation.txt](02-retry/evidencias/03-normal-operation.txt) |
| Recuperación 503 → 503 → 200 | [04-retry-recovery.txt](02-retry/evidencias/04-retry-recovery.txt) |
| Agotamiento de intentos | [05-retry-exhausted.txt](02-retry/evidencias/05-retry-exhausted.txt) |
| HTTP 400 sin reintentos | [06-no-retry-400.txt](02-retry/evidencias/06-no-retry-400.txt) |
| Exponential Backoff | [07-exponential-backoff.txt](02-retry/evidencias/07-exponential-backoff.txt) |
| Contadores del backend | [08-backend-stats.txt](02-retry/evidencias/08-backend-stats.txt) |
| Terraform validado y aplicado | [09](02-retry/evidencias/09-terraform-validate.txt) · [10](02-retry/evidencias/10-terraform-plan.txt) · [11](02-retry/evidencias/11-terraform-apply.txt) |
| Servicio ECS Fargate | [12-ecs.png](02-retry/evidencias/12-ecs.png) · [12-ecs.txt](02-retry/evidencias/12-ecs.txt) |
| Demo real en AWS | [13-aws-demo.txt](02-retry/evidencias/13-aws-demo.txt) |
| Logs de CloudWatch | [14-cloudwatch.txt](02-retry/evidencias/14-cloudwatch.txt) |
| Destrucción de recursos | [15-terraform-destroy.txt](02-retry/evidencias/15-terraform-destroy.txt) |

**Resultados obtenidos:**

| Escenario | Intentos | Resultado |
|---|---|---|
| Operación normal | 1 | HTTP 200 |
| Fallo temporal | 3 | HTTP 503 → 503 → 200 |
| Fallo permanente | 3 | HTTP 503 final |
| Solicitud incorrecta | 1 | HTTP 400 |
| Exponential Backoff | 3 | Esperas de 0,5 y 1 segundo |
| Pruebas automatizadas | 25 | Todas aprobadas |

Documentación completa: [README del laboratorio](02-retry/README.md), [arquitectura](02-retry/ARQUITECTURA.md) e [informe](02-retry/INFORME.md).

## Laboratorio 03 — Timeout

**¿Qué es?** Mecanismo que establece un tiempo máximo de espera para completar una operación, impidiendo que una aplicación permanezca bloqueada indefinidamente. Si se supera el límite, el cliente interrumpe la espera y genera un error de timeout.

**Implementación:** Dos servicios en Spring Boot. `Inventario` (puerto 8080) devuelve un teclado con 12 unidades; con `lento=true` simula una demora de cinco segundos. `Pedidos` (puerto 8081) consulta a `Inventario` con un límite de lectura de dos segundos. Responde 200 OK si recibe los datos a tiempo, o 504 Gateway Timeout si se agota la espera.

**Estado:** Pendiente de implementación en este repositorio. Documentación base en [README](03-timeout/README.md).

## Laboratorio 04 — Serverless Computing y Docker Containers

**¿Qué es?** Dos enfoques para ejecutar aplicaciones en la nube. Serverless (AWS Lambda) ejecuta código sin administrar servidores; Docker Containers empaquetan la aplicación con dependencias para ejecución consistente (Amazon ECS con Fargate permite ejecutar contenedores sin administrar servidores).

**Implementación:** Función AWS Lambda con Python 3.12 y aplicación web FastAPI empaquetada en Docker, desplegada en Amazon ECS Fargate. Infraestructura gestionada con Terraform; imagen almacenada en Amazon ECR.

**Evidencias obtenidas:**

| Resultado | Evidencia |
|---|---|
| Servicio ECS con dos tareas | [01-ecs.png](04-serverless-docker/evidencias/01-ecs.png) |
| Función Lambda Python 3.12 | [02-lambda.png](04-serverless-docker/evidencias/02-lambda.png) |
| Pruebas Lambda HTTP 200 | [03-lambda-test.txt](04-serverless-docker/evidencias/03-lambda-test.txt) |
| Pruebas contenedor HTTP 200 | [04-container-test.txt](04-serverless-docker/evidencias/04-container-test.txt) |
| Terraform validado y aplicado | [05-terraform-validate.txt](04-serverless-docker/evidencias/05-terraform-validate.txt) · [06-terraform-plan.txt](04-serverless-docker/evidencias/06-terraform-plan.txt) · [07-terraform-apply.txt](04-serverless-docker/evidencias/07-terraform-apply.txt) |
| Destrucción de recursos | [08-terraform-destroy.txt](04-serverless-docker/evidencias/08-terraform-destroy.txt) |

Documentación completa: [README del laboratorio](04-serverless-docker/README.md).

## Laboratorio 05 — API Gateway, Load Balancer y Reverse Proxy

**¿Qué es?** Componentes que gestionan el acceso y la comunicación entre clientes y servidores. API Gateway centraliza, protege y administra el acceso a las APIs. Load Balancer distribuye solicitudes entre servidores. Reverse Proxy actúa como intermediario entre cliente y servidores internos.

**Implementación:** API Gateway integrado con AWS Lambda, Application Load Balancer distribuyendo tráfico entre tareas ECS Fargate (dos destinos saludables), y NGINX como proxy inverso para dirigir solicitudes hacia diferentes servicios. Infraestructura con Terraform.

**Evidencias obtenidas:**

| Resultado | Evidencia |
|---|---|
| API Gateway desplegado | [01-api-gateway.png](05-gateway-lb-proxy/evidencias/01-api-gateway.png) |
| Target Group ALB con dos destinos | [02-alb-target-group.png](05-gateway-lb-proxy/evidencias/02-alb-target-group.png) |
| Pruebas HTTP y enrutamiento NGINX | [03-nginx-routing.txt](05-gateway-lb-proxy/evidencias/03-nginx-routing.txt) |
| Terraform aplicado | [04-terraform-apply.txt](05-gateway-lb-proxy/evidencias/04-terraform-apply.txt) |
| Destrucción de recursos | [05-terraform-destroy.txt](05-gateway-lb-proxy/evidencias/05-terraform-destroy.txt) |

Documentación completa: [README del laboratorio](05-gateway-lb-proxy/README.md).

## Laboratorio 06 — Hub-and-Spoke

**¿Qué es?** Arquitectura de red que centraliza la conectividad mediante un punto principal (Hub) al que se conectan redes secundarias (Spokes). Simplifica administración, enrutamiento y seguridad. En AWS se implementa con Transit Gateway.

**Implementación:** Se creó `tgw-lab-hub` y se conectaron dos VPC (Spoke A: `10.20.0.0/16`, Spoke B: `10.30.0.0/16`). Se desplegó una instancia EC2 en cada una (`ec2-spoke-a: 10.20.1.115`, `ec2-spoke-b: 10.30.1.196`). Se configuraron rutas de ida y regreso entre ambas VPC a través del hub. La instancia de Spoke A hizo cinco pings a Spoke B: 5/5 respuestas, 0 % de pérdida, tiempo promedio de ida y vuelta de 1,823 ms.

**Estado:** Pendiente de implementación en este repositorio. Documentación base en [README](06-hub-and-spoke/README.md).

## Laboratorio 07 — Lift-and-Shift

**¿Qué es?** Estrategia de migración (Rehosting) que traslada aplicaciones desde infraestructura local a la nube conservando su arquitectura y funcionamiento original, sin rediseñar completamente el sistema.

**Implementación:** Aplicación Python en VM Ubuntu Server 24.04 con QEMU/KVM simulando entorno On-Premise. Infraestructura en AWS con Terraform y aplicación trasladada a una instancia Amazon EC2. Transferencia de archivos mediante SCP y configuración con systemd. Se comparó el SHA256 del archivo original y migrado para confirmar transferencia sin modificaciones.

**Evidencias obtenidas:**

| Resultado | Evidencia |
|---|---|
| Instancia EC2 creada y ejecutándose | [01-ec2.png](07-lift-and-shift/evidencias/01-ec2.png) |
| Comparación SHA256 original vs migrado | [02-hash-comparison.txt](07-lift-and-shift/evidencias/02-hash-comparison.txt) |
| Pruebas HTTP 200 en ambos entornos | [03-http-tests.txt](07-lift-and-shift/evidencias/03-http-tests.txt) |
| Terraform: 8 recursos creados y eliminados | [04-terraform-apply.txt](07-lift-and-shift/evidencias/04-terraform-apply.txt) · [05-terraform-destroy.txt](07-lift-and-shift/evidencias/05-terraform-destroy.txt) |

Documentación completa: [README del laboratorio](07-lift-and-shift/README.md).

## Laboratorio 08 — Bastion Host

**¿Qué es?** Servidor intermediario (Jump Server) para acceder de manera controlada a máquinas en redes privadas, evitando exponer servidores internos directamente a Internet. En AWS se implementa con EC2 y Security Groups; alternativa moderna es AWS Systems Manager Session Manager.

**Implementación:** VPC `lab-bastion` con dos instancias EC2. Bastión en subred pública con IPv4 pública para conexión desde Windows. Servidor privado en subred privada (`10.10.2.107`). Security Group `bastion-ssh` permite acceso desde la IP del administrador; `privado-ssh` permite SSH del puerto 22 desde el bastión. Conexión SSH verificada: `SSH_CONNECTION` mostró conexión desde `10.10.1.96` (IP interna del bastión) hasta `10.10.2.107` por el puerto 22.

**Estado:** Pendiente de implementación en este repositorio. Documentación base en [README](08-bastion/README.md).

## Anexos — Implementación en proyectos individuales

El documento incluye propuestas de aplicación de los ocho patrones en dos proyectos individuales:

- **Consulmed ONE:** aplicación y justificación de cada patrón en la comunicación de microservicios (gRPC), notificaciones, llamadas entre fachada y microservicios, procesamiento serverless, API Gateway/ALB/reverse proxy, separación de redes con Hub-and-Spoke, migración de sistema legado a EC2 y administración restringida con Bastion.
- **AlergoAssist:** aplicación propuesta de cada patrón (Circuit Breaker en consultas a Médicos, Retry en lectura de Citas, Timeout en verificación de especialistas, Lambda/Docker/ECS para microservicios, API Gateway para rutas públicas, Hub-and-Spoke para separación de redes, Lift-and-Shift de agenda local a EC2, Bastion para acceso administrativo).

## Conclusiones

Los patrones y tecnologías investigados permiten resolver diferentes necesidades de los sistemas distribuidos. Circuit Breaker, Retry y Timeout mejoran la resiliencia frente a fallos de comunicación. Serverless y Docker ofrecen alternativas para ejecutar y desplegar aplicaciones. API Gateway, Load Balancer y Reverse Proxy permiten administrar solicitudes y tráfico. Hub-and-Spoke organiza la conectividad entre redes, Lift-and-Shift facilita la migración a la nube y Bastion contribuye a proteger el acceso administrativo.

En conjunto, estos conceptos permiten diseñar infraestructuras más confiables, seguras y fáciles de administrar. Su aplicación debe responder a necesidades concretas, considerando la complejidad, los recursos disponibles y los requisitos del sistema.

## Tecnologías

AWS (Lambda, ECR, ECS Fargate, EC2, API Gateway, ALB, CloudWatch, Transit Gateway), Terraform, Docker y Docker Compose, Python 3.12, FastAPI, PyBreaker, Tenacity, Resilience4j, Spring Boot, Java 17, HTTPX, Pytest, NGINX, Git y GitHub.

## Evidencias y buenas prácticas

- Las evidencias se generan ejecutando comandos reales; no se fabrican resultados.
- No se versionan credenciales, tokens, llaves privadas, `terraform.tfvars`, estados de Terraform ni planes.
- Los recursos AWS de prueba se apagan o destruyen al finalizar cada laboratorio.
- Los estados de Terraform son independientes por laboratorio para evitar modificaciones accidentales entre ellos.

## Cómo revisar un laboratorio

Cada README explica los requisitos, la ejecución local, el despliegue y las evidencias. Ejemplo para Laboratorio 01 y 02:

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

```bash
cd 02-retry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -v
docker compose up --build -d
bash scripts/demo.sh
docker compose down
```

## Referencias principales

- Amazon Web Services. Circuit Breaker Pattern. <https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html>
- Amazon Web Services. Retry with Backoff Pattern. <https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html>
- Amazon Web Services. Set Client Timeouts. <https://docs.aws.amazon.com/wellarchitected/latest/framework/rel05-bp05.html>
- Amazon Web Services. Amazon ECS and AWS Lambda Comparison. <https://aws.amazon.com/compare/ecs-and-lambda/>
- Amazon Web Services. Choosing the Right AWS Service for Microservice Endpoints. <https://docs.aws.amazon.com/prescriptive-guidance/latest/choosing-the-right-aws-service-for-your-microservice-endpoints/>
- Amazon Web Services. Hub-and-Spoke Network Topologies. <https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_planning_network_topology_prefer_hub_and_spoke.html>
- Amazon Web Services. Migration Strategies. <https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html>
- Amazon Web Services. Access a Bastion Host Using Session Manager. <https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/access-a-bastion-host-by-using-session-manager-and-amazon-ec2-instance-connect.html>
- Netflix Technology Blog. Fault Tolerance in a High Volume, Distributed System. <https://netflixtechblog.com/fault-tolerance-in-a-high-volume-distributed-system-91ab4faae74a>
- Stripe. Designing Robust and Predictable APIs with Idempotency. <https://stripe.com/blog/idempotency>

## Estado AWS y control de costos

- **Lab01:** 7 recursos destruidos; servicio ECS `INACTIVE`; sin ECR, log groups ni Security Group del laboratorio. Clúster, VPC, subredes y `LabRole` compartidos intactos.
- **Lab02:** 6 recursos runtime y 2 repositorios ECR destruidos; servicio y clúster ECS `INACTIVE`, sin tareas, log groups ni Security Group del laboratorio. Task definition `INACTIVE` y VPC/subredes/`LabRole` compartidos intactos.
- **Lab04:** servicio ECS `cloudlab-erik-api` en `desired=0`, `running=0`.
- **Lab05:** infraestructura desactivada mediante variables locales.
- **Lab07:** instancia EC2 terminada y recursos destruidos; VM local apagada.
- No hay instancias EC2 en ejecución.
