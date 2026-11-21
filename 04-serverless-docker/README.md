# Laboratorio 04 — Serverless y contenedores en AWS con Terraform

**Responsable:** Erik · **Proyecto:** Cloud Patterns Lab

## Objetivo y arquitectura

Demostrar la diferencia entre ejecutar una funcion bajo demanda con AWS Lambda y una API empaquetada en Docker, ejecutada en Amazon ECS Fargate. Terraform administra los recursos AWS.

```text
Test de Lambda -> AWS Lambda (Python)

Docker local -> FastAPI :8080
                      |
                  docker build
                      |
                  Amazon ECR
                      |
                  Amazon ECS Fargate (tarea)
                      |
            IP publica temporal :8080 (acceso restringido a tu IP)
```

> La ejecucion ECS en una subred publica es una simplificacion **solo para la demostracion**. No es la arquitectura de produccion recomendada. En el Laboratorio 05 integraremos un ALB para la distribucion de trafico.

## 1. Prueba local

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
sudo docker compose up --build -d
curl http://127.0.0.1:8080/health
sudo docker compose down
```

## 2. Antes de desplegar en AWS Academy

- Iniciar el Learner Lab y copiar las credenciales temporales a un perfil **local** de AWS CLI, por ejemplo `lab`.
- Comprobar `aws sts get-caller-identity` y `aws iam get-role --role-name LabRole`. **No compartir** tokens, claves ni archivos `~/.aws/credentials`.
- Tener instalados: Terraform, Docker, AWS CLI, Python, curl.
- AWS Academy puede bloquear ciertas operaciones; no se garantiza IAM, ECR, Fargate ni VPC hasta probarlas.

```bash
export AWS_PROFILE=lab
export AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity
aws iam get-role --role-name LabRole --query 'Role.Arn' --output text
```

**Si LabRole no existe, o los servicios no pueden asumirlo, NO continúes con `apply` sin revisar el permiso.** No crees un rol alternativo a ciegas.

## 3. Terraform: fase 1 (Lambda + ECR + ECS Cluster)

Ejecutar desde `04-serverless-docker/terraform`:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

Con `enable_ecs = false` NO se crea Fargate, IP publica ni red.

Para probar Lambda:

```bash
aws lambda invoke \
  --function-name "$(terraform output -raw lambda_function_name)" \
  --payload '{"rawPath":"/"}' \
  --cli-binary-format raw-in-base64-out \
  resultado-lambda.json
cat resultado-lambda.json
```

## 4. Publicar imagen Docker en ECR

Desde `04-serverless-docker/terraform` y con Docker en funcionamiento:

```bash
REGION=${AWS_DEFAULT_REGION:-us-east-1}
REPO_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region "$REGION" \
  | sudo docker login --username AWS --password-stdin "${REPO_URL%/*}"
sudo docker build --platform linux/amd64 -t cloudlab-erik:demo ..
sudo docker tag cloudlab-erik:demo "$REPO_URL:v1"
sudo docker push "$REPO_URL:v1"
```

Si usas credenciales AWS del usuario sin sudo, quizá necesites iniciar sesion Docker de forma consistente (por ejemplo, `sudo docker login` seguido de `sudo docker push`). No exponer credenciales de Docker o AWS en las evidencias.

## 5. Terraform: fase 2 (ECS Fargate)

Antes de activar ECS, obtener tu IPv4 publica:

```bash
curl -4 https://checkip.amazonaws.com
```

Editar `terraform.tfvars`:

```hcl
enable_ecs  = true
allowed_cidr = "TU_IP_PUBLICA/32"
```

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

Una tarea Fargate ejecuta la API. Busca la IP publica de la tarea en la consola ECS/EC2 o mediante AWS CLI y comprueba:

```bash
curl http://IP_PUBLICA_TAREA:8080/health
```

Resultado esperado: `{"status":"ok"}`. Si la respuesta no llega, revisar Security Group, IP origen, logs, ENI y estado de tarea.

## 6. Evidencias obligatorias

- Captura de las seis pruebas locales aprobadas.
- Captura de Docker local ejecutando FastAPI.
- `terraform validate` y `terraform plan` sin errores.
- AWS Lambda desplegada y resultado real de `invoke`.
- ECR con imagen `v1` publicada.
- ECS con tarea RUNNING y respuesta HTTP /health.
- Diagrama de arquitectura en `ARQUITECTURA.md`.
- URL de GitHub de la rama y Pull Request.

Guardar solo evidencias propias, evitando claves, tokens, account IDs si no es necesario o capturas de credenciales.

## 7. Limpieza de AWS (importante)

Al terminar la demostracion, ejecutar desde `terraform`:

```bash
terraform plan -destroy
terraform destroy
```

Terraform destruira los recursos de este estado local, incluidos imagenes del repositorio ECR porque `force_delete = true`. No borrar el estado antes de destruir y no ejecutar `destroy` en carpetas o cuentas ajenas.

## Nota para el laboratorio 05

Reutilizaremos Lambda, ECR, ECS y la VPC de este laboratorio. En vez de duplicar recursos, ampliaremos el mismo conjunto de Terraform para ALB y API Gateway. NGINX se probará con una configuracion independiente en `05-gateway-lb-proxy/`.
