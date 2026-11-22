# Laboratorio 07 — Lift-and-Shift (On-Premise → AWS EC2)

**Responsable:** Erik · **Estado:** completado (10/10) · **Rama:** `erik/practicas`

Demostración de **rehosting sin cambiar el código**: una aplicación Python
ejecutada primero en una VM Ubuntu local y después en una instancia EC2, con la
infraestructura de destino creada por Terraform. El archivo de la aplicación se
extrae **de la VM on-premise**, se transfiere a EC2 y se comprueba que el hash
SHA256 es idéntico.

> Alcance académico: se migra una carga de trabajo simple (código + unidad
> `systemd`), no se clona el sistema operativo ni se replican discos. Para una
> migración completa de servidores existe AWS Transform MGN (antes AWS
> Application Migration Service).

## 1. Contenido del laboratorio

```
07-lift-and-shift/
├── app/server.py                  # aplicación heredada (sin modificaciones)
├── systemd/legacyapp.service      # unidad systemd del servicio
├── scripts/install-app.sh         # instalador usado en origen y destino
├── terraform/                     # VPC, subred, IGW, rutas, SG, key pair y EC2
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
├── tests/test_server.py           # 3 pruebas unitarias
├── evidencias/                    # 13 archivos, índice en su README
├── README.md                      # este documento
├── ARQUITECTURA.md                # diagrama y decisiones de diseño
└── INFORME.md                     # texto de apoyo y resultados reales
```

El estado Terraform es **independiente** de los laboratorios 04 y 05.

## 2. Entorno real utilizado

| Elemento | Valor |
| -------- | ----- |
| Host | Arch Linux con `/dev/kvm` disponible |
| Hipervisor | QEMU/KVM en modo usuario (`-netdev user`), sin libvirt |
| VM on-premise | `onprem-legacy-server`, Ubuntu 24.04.5 LTS, Python 3.12.3, 1 vCPU / 2 GB / 15 GB |
| Acceso a la VM | SSH `127.0.0.1:2222` → puerto 22; HTTP `127.0.0.1:8088` → puerto 8080 |
| AWS | Cuenta `533267299755`, región `us-east-1`, perfil `lab`, rol `LabRole` |
| EC2 | `i-03175f428ac57d526`, `cloudlab-erik-liftshift-ec2`, `t3.micro`, IP `3.235.42.178` |
| Hash de `server.py` | `03b47adf2f62b2ebe85bfd0c91899c199dd63243df95d635fa6ac407c1ed8230` (idéntico en origen y destino) |

El puerto HTTP de la VM se publicó en `127.0.0.1:8088` para no interferir con
el contenedor del laboratorio 04, que usa `8080` en el mismo host.

## 3. Reproducción paso a paso

### 3.1 Tests e incorporación al repositorio

```bash
cd ~/Documents/university/prograDistribuida/cloud-patterns-lab
git switch erik/practicas
git pull --ff-only origin erik/practicas

python3 -m unittest discover -s 07-lift-and-shift/tests -v \
  2>&1 | tee 07-lift-and-shift/evidencias/01-tests.txt
# Ran 3 tests ... OK
```

### 3.2 Entorno on-premise

Se usó una imagen cloud oficial de Ubuntu 24.04 con `cloud-init` para inyectar
la clave pública `~/.ssh/cloudlab-onprem`. En la VM quedó instalada la
aplicación como servicio `systemd`:

```bash
ssh -i ~/.ssh/cloudlab-onprem -p 2222 ubuntu@127.0.0.1 \
  'mkdir -p ~/lab07'
scp -P 2222 -i ~/.ssh/cloudlab-onprem -r \
  07-lift-and-shift/app 07-lift-and-shift/systemd 07-lift-and-shift/scripts \
  ubuntu@127.0.0.1:/home/ubuntu/lab07/
ssh -i ~/.ssh/cloudlab-onprem -p 2222 ubuntu@127.0.0.1 \
  'echo "<password-sudo-local>" | sudo -S bash ~/lab07/scripts/install-app.sh'

curl -i http://127.0.0.1:8088/health
ssh -i ~/.ssh/cloudlab-onprem -p 2222 ubuntu@127.0.0.1 \
  'systemctl is-active legacyapp; sha256sum /opt/legacyapp/server.py'
# active
# 03b47adf...  /opt/legacyapp/server.py
```

> En este entorno `libvirt` no era utilizable: `sudo` pedía contraseña
> interactiva y `/var/lib/libvirt/images` no era escribible, aunque `/dev/kvm`
> sí estaba disponible. Por eso se empleó QEMU en modo usuario con las
> redirecciones de puertos indicadas. Con VirtualBox, Proxmox o libvirt se puede
> seguir el mismo procedimiento usando la IP real de la VM.

### 3.3 Infraestructura AWS con Terraform

```bash
export AWS_PROFILE=lab AWS_DEFAULT_REGION=us-east-1
aws sts get-caller-identity

ssh-keygen -t ed25519 -f ~/.ssh/cloudlab-liftshift -C 'cloudlab-liftshift'
chmod 600 ~/.ssh/cloudlab-liftshift

cd 07-lift-and-shift/terraform
cp terraform.tfvars.example terraform.tfvars
# Completar: aws_region, allowed_cidr (SSH), http_allowed_cidr (HTTP),
# instance_type, create_key_pair y public_key_path.

terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan | tee ../evidencias/04-terraform-plan.txt
terraform apply tfplan     | tee ../evidencias/05-terraform-apply.txt
terraform output
# instance_public_ip = 3.235.42.178
```

**Nota de red:** `curl -4 https://checkip.amazonaws.com` devuelve
`157.100.142.229/32`, pero el tráfico SSH desde este laboratorio sale por
`181.199.46.145/32`. El Security Group autoriza la primera IP en el puerto
8080 (HTTP) y la segunda en el 22 (SSH), gracias a la variable
`http_allowed_cidr`. Sin este ajuste el SSH funcionaba pero el HTTP expiraba.

### 3.4 Migración real desde la VM

```bash
cd ../..
export EC2_IP="$(terraform -chdir=07-lift-and-shift/terraform output -raw instance_public_ip)"
export KEY="$HOME/.ssh/cloudlab-liftshift"

mkdir -p /tmp/cloudlab07-migration/{app,systemd,scripts}
scp -P 2222 -i ~/.ssh/cloudlab-onprem \
  ubuntu@127.0.0.1:/opt/legacyapp/server.py /tmp/cloudlab07-migration/app/
scp -P 2222 -i ~/.ssh/cloudlab-onprem \
  ubuntu@127.0.0.1:/etc/systemd/system/legacyapp.service /tmp/cloudlab07-migration/systemd/
cp 07-lift-and-shift/scripts/install-app.sh /tmp/cloudlab07-migration/scripts/

ssh -i "$KEY" "ubuntu@$EC2_IP" 'mkdir -p /home/ubuntu/lab07'
scp -i "$KEY" -r /tmp/cloudlab07-migration/{app,systemd,scripts} \
  "ubuntu@$EC2_IP:/home/ubuntu/lab07/"
ssh -i "$KEY" "ubuntu@$EC2_IP" \
  'echo "<password-sudo-local>" | sudo -S bash /home/ubuntu/lab07/scripts/install-app.sh'
```

No se editaron `server.py` ni `legacyapp.service` entre origen y destino.

### 3.5 Verificación

```bash
ssh -i "$KEY" "ubuntu@$EC2_IP" \
  'systemctl is-active legacyapp; sha256sum /opt/legacyapp/server.py'
curl -i "http://$EC2_IP:8080/health"
# HTTP/1.0 200 OK  {"status": "ok"}
```

La evidencia `09-sha256-comparison.txt` muestra el mismo hash en ambas
máquinas. La captura `06-ec2-instance.png` muestra la consola AWS con la
instancia en estado `Running`.

## 4. Resultado de la ejecución

| Comprobación | Resultado real |
| ------------ | -------------- |
| Pruebas unitarias | 3 tests, `OK` |
| Servicio en VM | `active`, `/health` → HTTP 200 |
| Terraform apply | `8 added, 0 changed, 0 destroyed` |
| Servicio en EC2 | `active`, Ubuntu 24.04.5 LTS |
| HTTP en AWS | HTTP 200 en `/health` y `/` |
| SHA256 | idéntico en VM y EC2 |
| Plan final antes de limpiar | `No changes. Your infrastructure matches the configuration.` |
| Limpieza | `8 destroyed`, instancia `terminated`, state vacío |

Detalle completo: [índice de evidencias](evidencias/README.md) e
[informe](INFORME.md). Diagrama: [arquitectura](ARQUITECTURA.md).

## 5. Seguridad

- La clave privada `~/.ssh/cloudlab-liftshift` y la de la VM
  `~/.ssh/cloudlab-onprem` se guardan solo en el equipo local.
- No se versionan `terraform.tfvars`, `terraform.tfstate`, planes ni claves
  privadas; la clave pública se registra como recurso `aws_key_pair`.
- SSH y HTTP se limitan a direcciones `/32` concretas.
- La contraseña de `sudo` de la VM es un valor local de laboratorio y tampoco
  se versiona.

## 6. Estado final y costos

La instancia EC2 y el resto de recursos del laboratorio 07 se eliminaron con
`terraform destroy` **después** de guardar las evidencias, porque AWS cobra por
instancias EC2 y direcciones IPv4 públicas. La VM local se apagó una vez
finalizada la migración. Los laboratorios 04 y 05 no fueron afectados por esta
destrucción; la infraestructura opcional del laboratorio 05 se desactivó por
separado usando sus propios flags de Terraform.

Commits de esta entrega en `erik/practicas`:

- `6de6b96` — `feat(lab07): rehost onprem application to EC2 with Terraform`
- `1cb1bb7` — `docs(evidence): add EC2 console screenshot for lab07`
- `995d867` — `chore(lab07): destroy EC2 lab resources and document cleanup`
