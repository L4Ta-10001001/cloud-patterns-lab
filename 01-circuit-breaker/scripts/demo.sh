#!/usr/bin/env bash
# Demostracion reproducible del Circuit Breaker.
# Uso local:  bash scripts/demo.sh
# Uso en AWS: CLIENT_URL=http://IP:8000 bash scripts/demo.sh
set -euo pipefail

URL="${CLIENT_URL:-http://127.0.0.1:8091}"
DIR="${EVID_DIR:-evidencias}"

mkdir -p "$DIR"

peticion() {
  local scenario="$1"
  echo "\$ curl -sS -w '\\nHTTP %{http_code}\\n' \"$URL/request?scenario=$scenario\""
  curl -sS --max-time 10 -w '\nHTTP %{http_code}\n' "$URL/request?scenario=$scenario"
  echo
}

estado() {
  curl -sS --max-time 10 "$URL/breaker/status" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])'
}

total_backend() {
  curl -sS --max-time 10 "$URL/backend/stats" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])'
}

echo "Esperando a $URL/health ..."
for i in $(seq 1 40); do
  if curl -fsS --max-time 3 "$URL/health" >/dev/null 2>&1; then
    echo "Cliente listo (intento $i)"
    break
  fi
  if [ "$i" = 40 ]; then
    echo "ERROR: el cliente no respondio /health" >&2
    exit 1
  fi
  sleep 1
done

{
  echo "# 03 - Operacion normal (circuito CLOSED)"
  echo "URL base: $URL"
  echo
  echo "\$ curl -sS \"$URL/health\""
  curl -sS --max-time 10 "$URL/health"
  echo
  echo
  peticion ok
  echo "\$ curl -sS \"$URL/breaker/status\""
  curl -sS --max-time 10 "$URL/breaker/status"
  echo
  echo
  echo "\$ curl -sS \"$URL/backend/stats\""
  curl -sS --max-time 10 "$URL/backend/stats"
  echo
} | tee "$DIR/03-normal-operation.txt"

[ "$(estado)" = "CLOSED" ] || { echo "ERROR: el circuito deberia estar CLOSED" >&2; exit 1; }

{
  echo "# 04 - Tres fallos consecutivos abren el circuito"
  echo
  for i in 1 2 3; do
    echo "--- fallo $i ---"
    peticion fail
    echo "estado del circuito: $(estado)"
    echo
  done
  echo "\$ curl -sS \"$URL/backend/stats\""
  curl -sS --max-time 10 "$URL/backend/stats"
  echo
} | tee "$DIR/04-circuit-open.txt"

[ "$(estado)" = "OPEN" ] || { echo "ERROR: el circuito deberia estar OPEN" >&2; exit 1; }

antes="$(total_backend)"
{
  echo "# 05 - Rechazo inmediato: el backend NO recibe la peticion"
  echo
  echo "peticiones al backend antes: $antes"
  echo
  peticion ok
  echo "peticiones al backend despues: $(total_backend)"
  echo
  echo "\$ curl -sS \"$URL/breaker/status\""
  curl -sS --max-time 10 "$URL/breaker/status"
  echo
} | tee "$DIR/05-fast-fail.txt"

despues="$(total_backend)"
[ "$despues" = "$antes" ] || { echo "ERROR: el backend recibio peticiones con el circuito OPEN" >&2; exit 1; }

echo "Esperando 11 segundos (reset_timeout=10 s) para la prueba HALF-OPEN ..."
sleep 11

{
  echo "# 06 - Recuperacion mediante HALF-OPEN"
  echo
  peticion ok
  echo "estado final del circuito: $(estado)"
  echo
  echo "\$ curl -sS \"$URL/breaker/status\""
  curl -sS --max-time 10 "$URL/breaker/status"
  echo
  echo
  echo "\$ curl -sS \"$URL/backend/stats\""
  curl -sS --max-time 10 "$URL/backend/stats"
  echo
} | tee "$DIR/06-circuit-recovery.txt"

[ "$(estado)" = "CLOSED" ] || { echo "ERROR: el circuito deberia estar CLOSED" >&2; exit 1; }

echo "Demostracion completada. Evidencias en $DIR/"
