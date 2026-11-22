#!/usr/bin/env bash
set -euo pipefail
if (( EUID != 0 )); then
  echo 'Ejecutar con sudo: sudo bash scripts/install-app.sh' >&2
  exit 1
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/app/server.py" ]] || { echo 'No existe app/server.py' >&2; exit 1; }
[[ -f "$ROOT/systemd/legacyapp.service" ]] || { echo 'No existe systemd/legacyapp.service' >&2; exit 1; }
if ! command -v python3 >/dev/null 2>&1; then
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3
fi
if ! id legacyapp >/dev/null 2>&1; then
  useradd --system --home-dir /opt/legacyapp --shell /usr/sbin/nologin legacyapp
fi
install -d -m 0755 -o legacyapp -g legacyapp /opt/legacyapp
install -m 0644 -o legacyapp -g legacyapp "$ROOT/app/server.py" /opt/legacyapp/server.py
install -m 0644 "$ROOT/systemd/legacyapp.service" /etc/systemd/system/legacyapp.service
systemctl daemon-reload
systemctl enable legacyapp
systemctl restart legacyapp
systemctl is-active legacyapp
sha256sum /opt/legacyapp/server.py
