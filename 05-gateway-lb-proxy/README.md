# Laboratorio 05 — API Gateway, Load Balancer y Reverse Proxy

Responsable: **Erik**. Reutiliza el laboratorio 04 existente (Lambda, ECR, ECS, VPC). NO requiere crear un ECS cluster nuevo.

## 0. Requisitos previos
- Haber completado Lab04 y tener su Terraform state local actualizado.
- La función Lambda y el servicio ECS existentes deben estar operativos.
- Trabajar desde `erik/practicas`. Guardar Lab04 en Git ANTES de cambiarlo.
- `AWS_PROFILE=lab`, credenciales vigentes y `AWS_DEFAULT_REGION=us-east-1`.
- No subir nunca `*.tfstate`, `*.tfvars`, `tfplan`, secretos ni accesos AWS.

## A. Reverse Proxy con NGINX (local, sin AWS)
Desde esta carpeta:

```bash
sudo docker compose up --build -d
curl -i http://127.0.0.1:8090/a/health
curl -i http://127.0.0.1:8090/b/health
```

Ambas rutas deben responder `HTTP/1.1 200 OK` con `{"status":"ok"}` y respectivamente encabezados `X-Backend: api-a` / `X-Backend: api-b`. Hay **dos contenedores backend**, confirmables con `sudo docker compose ps`.

Guardar evidencias:

```bash
mkdir -p evidencias
curl -i http://127.0.0.1:8090/a/health | tee evidencias/01-nginx-a.txt
curl -i http://127.0.0.1:8090/b/health | tee evidencias/02-nginx-b.txt
sudo docker compose ps
sudo docker compose down
```

## B. API Gateway conectado a la Lambda del Lab04

Desde la RAÍZ del repositorio (no desde la carpeta Terraform):

```bash
python 05-gateway-lb-proxy/scripts/integrate_lab05.py
```

Esto **solo edita** el `main.tf` preexistente: permite adjuntar el ALB posteriormente a las tareas actuales y cerrar el acceso directo al puerto de la API. No hace cambios AWS.

Abre `04-serverless-docker/terraform/terraform.tfvars` y MANTÉN tus valores actuales:

```hcl
enable_ecs      = true
enable_lab05    = true
enable_lab05_alb = false
```

**No reemplaces tu `allowed_cidr` ni lo subas a Git.** Debe ser tu IP pública actual en notación `/32`.

```bash
cd 04-serverless-docker/terraform
terraform fmt -recursive
terraform init
terraform validate
terraform plan -out=tfplan
```

Revisa que el plan no proponga eliminar tu Lambda/ECR/VPC/ECS ni reemplazar el servicio de forma imprevista. Deberían aparecer los componentes de HTTP API (y permiso Lambda). Aplica si los recursos son los esperados:

```bash
terraform apply tfplan
API_URL="$(terraform output -raw lab05_api_gateway_url)"
curl -i "$API_URL/health" | tee ../../05-gateway-lb-proxy/evidencias/03-api-gateway.txt
```

Resultado esperado `HTTP 200` con `{"status":"ok"}`. API Gateway invoca la Lambda existente, sin duplicarla.

**Si AWS Academy niega `lambda:AddPermission` o crear API Gateway, conserva el mensaje de error y NO cambies políticas IAM a ciegas.**

## C. Application Load Balancer + 2 tareas ECS (fase siguiente)

En `04-serverless-docker/terraform/terraform.tfvars`, cambia SOLO:

```hcl
enable_lab05_alb = true
```

El módulo configurará:
- ALB externo en las dos subredes ya creadas.
- Target Group de tipo `ip`, puerto 8080, health check `/health`.
- Listener HTTP :80 accesible SOLO desde tu `allowed_cidr`.
- Actualización del servicio ECS EXISTENTE para registrar sus tareas y ejecutar 2 réplicas.
- Cambio de SG: se elimina la entrada directa desde tu IP a ECS:8080 y se permite únicamente el SG del ALB.

```bash
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan
```

**Revisa especialmente el plan antes de aplicar**, porque la actualización del servicio ECS puede iniciar un nuevo despliegue (cambio transitorio de tareas). Si es correcto:

```bash
terraform apply tfplan
ALB_DNS="$(terraform output -raw lab05_alb_dns_name)"
curl -i "http://$ALB_DNS/health" | tee ../../05-gateway-lb-proxy/evidencias/06-alb-http.txt
aws elbv2 describe-target-health \
  --target-group-arn "$(terraform output -raw lab05_target_group_arn)" \
  > ../../05-gateway-lb-proxy/evidencias/05-target-health.json
```

`describe-target-health` debería mostrar dos destinos registrados y sanos; una primera respuesta 503 significa que hay que esperar o revisar los health checks, SG y tareas, no que haya terminado correctamente.

## D. Entrega GitHub
Desde la raíz del repositorio:

```bash
git status
git add 04-serverless-docker/terraform/main.tf \
        04-serverless-docker/terraform/lab05.tf \
        05-gateway-lb-proxy/
git diff --cached --stat
git commit -m "feat(lab05): API gateway ALB and NGINX reverse proxy"
git push origin erik/practicas
```

## E. Limpieza segura (cuando se hayan guardado las evidencias)

El Lab05 y el Lab04 comparten el mismo estado. **NO ejecutes `terraform destroy` dentro de Lab05** ni elimines a mano el ALB con consola, porque puedes romper dependencias del ECS service.

Para deshabilitar solo Lab05 al terminar:

1. Cambia `enable_lab05_alb = false` y `enable_lab05 = false` en `04-serverless-docker/terraform/terraform.tfvars`.
2. Desde el Terraform del Lab04, ejecuta `terraform plan` y revisa las operaciones, luego `terraform apply`.
3. Esto devuelve el ECS service a 1 tarea, retira el ALB y la API HTTP, y conserva el Lab04 (Fargate seguirá generando cargos).
4. Para eliminar TODO al final de los trabajos, desde Lab04 `terraform destroy`, solo tras confirmar que no se necesita para el Lab07.
