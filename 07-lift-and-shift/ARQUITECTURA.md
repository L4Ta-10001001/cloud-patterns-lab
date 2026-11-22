# Arquitectura — Lab07

```mermaid
flowchart LR
  DEV[Equipo Arch Linux] -->|SSH y SCP| VM[VM Ubuntu 24.04 - On-Premise]
  VM -->|Aplicación y servicio sin cambios| STAGING[Staging temporal en Arch]
  STAGING -->|SCP| EC2[Amazon EC2 Ubuntu 24.04]
  TF[Terraform] -->|VPC, subnet, IGW, rutas, SG, EC2| EC2
  DEV -->|curl HTTP :8080| VM
  DEV -->|curl HTTP :8080, origen /32| EC2
```

## Relación con Lift-and-Shift

La práctica mueve **los mismos archivos** de código y configuración del servicio `systemd` desde una VM local a una instancia EC2. Se prueba el mismo endpoint y se compara SHA256 antes y después. La infraestructura se crea con Terraform y la lógica de aplicación no se refactoriza.

Esta es una **simulación de rehosting a nivel de aplicación**, no migración de discos/SO ni replicación continua. Para rehosting de servidores completos AWS ofrece AWS Transform MGN (anteriormente AWS Application Migration Service).

## Seguridad

- Acceso a SSH 22 y HTTP 8080 restringido a `allowed_cidr=/32`.
- Se emplean pares de claves SSH, sin subir claves privadas a GitHub.
- EC2 de laboratorio con IPv4 pública por simplicidad; en producción se usaría una arquitectura privada detrás de balanceador y acceso administrativo sin puertos abiertos.
