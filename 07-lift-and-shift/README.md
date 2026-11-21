# Laboratorio 07 — Lift-and-Shift (On-Premise → AWS EC2)

**Responsable:** Erik. **Objetivo:** demostrar una migración simple **sin modificar el código** de una app Python ejecutada primero en una VM Ubuntu 24.04 local y luego en EC2 Ubuntu 24.04. Terraform crea la infraestructura de destino. **No modifica ni reutiliza el estado Terraform de Lab04/05.**

> Alcance académico: **rehosting de una carga de trabajo simple**, no clonación completa del sistema operativo ni replicación de discos. Para migrar un servidor completo existe AWS Transform MGN (antes AWS Application Migration Service).

## 0. Requisitos

- Equipo Arch Linux con `git`, `python3`, `openssh`, `curl`, `terraform`, `aws-cli`.
- **VM Ubuntu Server 24.04 local**, encendida, con red accesible desde Arch y `openssh-server` activo. Puede ser VirtualBox, KVM/virt-manager o Proxmox. Anota `VM_USER` y `VM_IP`.
- Cuenta AWS Academy activa y credenciales `AWS_PROFILE=lab` válidas, región `us-east-1`.
- EC2 `t3.micro` permitida y permiso para crear recursos de EC2/VPC/KeyPair (si está restringido, revisar el plan y la consola).
- Tu IP pública actual, para permitir únicamente tu `/32` en SSH y HTTP 8080.
- Comprobar créditos/costos y limpiar EC2 tras obtener evidencias.

## 1. Ejecutar los tests antes de migrar (desde Arch)

Desde la raíz del repositorio:

```bash
python3 -m unittest discover -s 07-lift-and-shift/tests -v \
  2>&1 | tee 07-lift-and-shift/evidencias/01-tests.txt
```

Se deben superar tres pruebas: `/health`, `/` y error 404.

## 2. Preparar On-Premise: VM Ubuntu

Crear una VM Ubuntu Server 24.04 (ejemplo: 1 vCPU, 1–2 GB RAM, 10 GB disco), conectada por una red accesible desde el host Arch. En la VM:

```bash
sudo apt-get update
sudo apt-get install -y python3 openssh-server curl
sudo systemctl enable --now ssh
hostname -I
```

En tu Arch exporta IP/usuario reales de la VM:

```bash
export VM_USER='USUARIO_DE_LA_VM'
export VM_IP='IP_PRIVADA_DE_LA_VM'
ssh "$VM_USER@$VM_IP" 'mkdir -p "$HOME/lab07"'
```

**Desde la raíz del repositorio**, envía los archivos de aplicación, `systemd` y el instalador a la VM:

```bash
scp -r 07-lift-and-shift/app 07-lift-and-shift/systemd \
  07-lift-and-shift/scripts "$VM_USER@$VM_IP:/home/$VM_USER/lab07/"
ssh "$VM_USER@$VM_IP" 'sudo bash ~/lab07/scripts/install-app.sh'
```

Comprobar y guardar evidencias en Arch:

```bash
curl -i "http://$VM_IP:8080/health" | tee 07-lift-and-shift/evidencias/02-onprem-health.txt
ssh "$VM_USER@$VM_IP" 'sudo systemctl is-active legacyapp; sha256sum /opt/legacyapp/server.py' \
  | tee 07-lift-and-shift/evidencias/03-onprem-service.txt
```

La VM debe tener el servicio `legacyapp` activo y responder `HTTP 200`.

## 3. Preparar Terraform de AWS (estado separado)

En Arch, desde la raíz del repo:

```bash
export AWS_PROFILE=lab
export AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity
ssh-keygen -t ed25519 -f ~/.ssh/cloudlab-liftshift -C 'cloudlab-liftshift'   # solo si no existe esa clave
chmod 600 ~/.ssh/cloudlab-liftshift
cd 07-lift-and-shift/terraform
cp terraform.tfvars.example terraform.tfvars
curl -4 https://checkip.amazonaws.com
```

Editar `terraform.tfvars` y reemplazar el CIDR de ejemplo por tu IP pública real terminada en `/32`. Terraform creará **una VPC nueva**, subred pública, Internet Gateway, rutas, SG limitado y EC2 Ubuntu 24.04; no modifica el estado de otros labs.

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan -out=tfplan | tee ../evidencias/04-terraform-plan.txt
```

Verificar que el plan solo cree recursos `lab07` y no elimine o altere otros recursos. Aplicar:

```bash
terraform apply tfplan | tee ../evidencias/05-terraform-apply.txt
terraform output
terraform plan | tee ../evidencias/10-terraform-no-changes.txt
export EC2_IP="$(terraform output -raw instance_public_ip)"
```

Si `aws_key_pair` falla por permisos AWS Academy, `create_key_pair=false` y `existing_key_name` permite usar una key pair válida creada previamente. El archivo privado correspondiente debe estar en tu equipo y debes usarlo en el SSH. No inventes llaves privadas ni desactives controles de seguridad.

## 4. Migrar los mismos archivos desde la VM local

En tu Arch, desde la raíz del repositorio (si aún estás en `terraform/`, vuelve a la raíz con `cd ../..`):

```bash
# Si necesitas reconstruir EC2_IP desde la raíz:
export EC2_IP="$(terraform -chdir=07-lift-and-shift/terraform output -raw instance_public_ip)"
export KEY="$HOME/.ssh/cloudlab-liftshift"

# 4.1 Extraer DIRECTAMENTE los archivos instalados en la VM (no copiar el código del repositorio)
mkdir -p /tmp/cloudlab07-migration/{app,systemd,scripts}
scp "$VM_USER@$VM_IP:/opt/legacyapp/server.py" /tmp/cloudlab07-migration/app/
scp "$VM_USER@$VM_IP:/etc/systemd/system/legacyapp.service" /tmp/cloudlab07-migration/systemd/
cp 07-lift-and-shift/scripts/install-app.sh /tmp/cloudlab07-migration/scripts/

# 4.2 Verificar el hash extraído
sha256sum /tmp/cloudlab07-migration/app/server.py

# 4.3 Enviar el material de la VM al destino EC2
ssh -i "$KEY" "ubuntu@$EC2_IP" 'mkdir -p /home/ubuntu/lab07'
scp -i "$KEY" -r /tmp/cloudlab07-migration/app \
  /tmp/cloudlab07-migration/systemd /tmp/cloudlab07-migration/scripts \
  "ubuntu@$EC2_IP:/home/ubuntu/lab07/"

# 4.4 Instalar EXACTAMENTE los archivos de la VM en EC2
ssh -i "$KEY" "ubuntu@$EC2_IP" 'sudo bash /home/ubuntu/lab07/scripts/install-app.sh'
```

No refactorizar ni editar `server.py` ni `legacyapp.service` entre origen y destino.

## 5. Comprobar el resultado y guardar evidencias

En Arch, desde la raíz del repositorio:

```bash
ssh -i "$KEY" "ubuntu@$EC2_IP" \
  'sudo systemctl is-active legacyapp; sha256sum /opt/legacyapp/server.py' \
  | tee 07-lift-and-shift/evidencias/07-ec2-service.txt

curl -i "http://$EC2_IP:8080/health" | tee 07-lift-and-shift/evidencias/08-ec2-http.txt
curl -s "http://$EC2_IP:8080/"

{
  echo 'ORIGEN (VM local)'; ssh "$VM_USER@$VM_IP" 'sha256sum /opt/legacyapp/server.py'
  echo 'DESTINO (EC2)'; ssh -i "$KEY" "ubuntu@$EC2_IP" 'sha256sum /opt/legacyapp/server.py'
} | tee 07-lift-and-shift/evidencias/09-sha256-comparison.txt
```

Los dos hashes de `server.py` deben ser **idénticos** (al comparar, ignorar el texto de la ruta). `curl` debe devolver HTTP 200 tanto en origen como destino. Capturar una imagen real de **EC2 → Instances → cloudlab-erik-liftshift-ec2 → Running**, y guardar como `evidencias/06-ec2-instance.png`.

**Criterio de aceptación:** la misma app y archivo de servicio que funcionaban en la VM funcionan en EC2; no se hicieron cambios en la lógica; logs y hash verificables.

## 6. GitHub

Desde la raíz del repo:

```bash
git status
git add 07-lift-and-shift/
git diff --cached --stat
# IMPORTANTE: verificar que no haya contraseñas, key privada, tfstate, tfvars, tfplan

git commit -m 'feat(lab07): rehost onprem Python app to EC2 with Terraform'
git push origin erik/practicas
```

## 7. Costos: limpiar solo Lab07

Desde `07-lift-and-shift/terraform`:

```bash
terraform plan -destroy
terraform destroy
```

Se eliminarán los recursos **gestionados por el estado de Lab07**. No destruye Lab04/05 si están en su carpeta y estado separado. `terraform destroy` elimina EC2 y sus datos locales; conservar antes las evidencias. Dejar el estado y archivos necesarios en el ordenador para administración, pero no subirlos a Git.

**Atención:** un ALB y dos tareas Fargate del Lab05 siguen generando cargos por separado. Limpiarlos requiere trabajar en el **Terraform de Lab04/05** con sus propios flags y revisar cuidadosamente su `plan`; no usar `terraform destroy` sobre esos labs si se quieren conservar Lambda/ECR u otros recursos.
