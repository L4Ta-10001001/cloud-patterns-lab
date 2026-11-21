# Texto de apoyo para el informe — Lab07

## Solución propuesta

Se utiliza una máquina virtual local Ubuntu 24.04 como entorno on-premise. En ella se ejecuta una API Python 3 mediante un servicio systemd (`legacyapp`). Posteriormente, Terraform aprovisiona una instancia Amazon EC2 Ubuntu 24.04 con conectividad y reglas de seguridad que permiten acceso SSH y HTTP únicamente desde la IP autorizada. Los archivos de la aplicación y su servicio se extraen de la VM local y se trasladan a EC2 sin modificar su código.

## Funcionamiento

1. Ejecutar la misma aplicación en la VM local y comprobar `/health`.
2. Aprovisionar recursos AWS con Terraform.
3. Transferir el código y la definición de servicio desde la VM a EC2.
4. Ejecutar la aplicación en EC2 y comprobar `/health`.
5. Comparar hashes SHA256 para demostrar que el código no se modificó.

## Resultados obtenidos

- Estado de la VM local: Ubuntu 24.04.5 LTS (`onprem-legacy-server`) con Python
  3.12.3, `sshd` activo y servicio `legacyapp` en estado `active`.
- Estado EC2: instancia `i-03175f428ac57d526` (`cloudlab-erik-liftshift-ec2`),
  Ubuntu 24.04.5 LTS, `running`, servicio `legacyapp` en estado `active`.
- HTTP en origen: `HTTP/1.0 200 OK` y `{"status": "ok"}` en la VM local.
- HTTP en destino: `HTTP/1.0 200 OK` y `{"status": "ok"}` en
  `http://3.235.42.178:8080/health`.
- ¿Hash idéntico?: sí. `03b47adf2f62b2ebe85bfd0c91899c199dd63243df95d635fa6ac407c1ed8230`
  tanto en `/opt/legacyapp/server.py` de la VM como en EC2.
- URL del repositorio: `git@github.com:L4Ta-10001001/cloud-patterns-lab.git`,
  rama `erik/practicas`.

Nota de red: el tráfico SSH sale con IP `181.199.46.145/32` y el HTTP con
`157.100.142.229/32`, por lo que el Security Group autoriza ambas direcciones.
El puerto 8080 de la VM se publica en el host Arch como `127.0.0.1:8088`
mediante NAT de QEMU para no interferir con el laboratorio 04.

Limpieza: tras guardar las evidencias se ejecutó `terraform destroy` únicamente
sobre el estado del laboratorio 07 (`8 destroyed`). La instancia EC2 quedó en
estado `terminated`. Los laboratorios 04 y 05 no fueron afectados.

## Conclusión

Si las pruebas anteriores son exitosas, se demuestra una migración simplificada de la aplicación a AWS sin rediseñar su lógica. Se aclara que la práctica migra archivos de una carga de trabajo y no realiza la replicación completa de una máquina virtual, tarea para la que existen herramientas especializadas como AWS Transform MGN.
