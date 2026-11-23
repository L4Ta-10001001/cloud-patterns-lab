#!/usr/bin/env bash
# Demostracion reproducible del patron Retry.
#
# Uso local:
#   bash scripts/demo.sh
#
# Uso contra AWS:
#   BASE_URL=http://IP_PUBLICA:8000 bash scripts/demo.sh
#
# Genera las evidencias 03 a 08 en 02-retry/evidencias/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVID="${EVID_DIR:-$ROOT/evidencias}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8092}"
RUN_PREFIX="${RUN_PREFIX:-demo-$(date +%Y%m%d-%H%M%S)}"

mkdir -p "$EVID"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

HTTP_CODE=""

wait_for_health() {
  local url="$1"
  local i
  for i in $(seq 1 40); do
    if curl -fsS --max-time 3 "$url/health" >/dev/null 2>&1; then
      echo "Cliente listo en $url (intento $i)"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $url/health no respondio" >&2
  return 1
}

http_get() {
  local url="$1"
  local out="$2"
  HTTP_CODE="$(curl -sS --max-time 30 -o "$out" -w '%{http_code}' "$url")"
}

assert_eq() {
  local actual="$1"
  local expected="$2"
  local message="$3"
  if [ "$actual" != "$expected" ]; then
    echo "ERROR: $message (esperado=$expected, actual=$actual)" >&2
    exit 1
  fi
}

assert_response() {
  local file="$1"
  local expected_status="$2"
  local expected_attempts="$3"
  local expected_retries="$4"
  local expected_recovered="$5"
  python3 - "$file" "$expected_status" "$expected_attempts" "$expected_retries" "$expected_recovered" <<'PY'
import json
import sys

path, status, attempts, retries, recovered = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

assert data["http_status"] == int(status), data
assert data["attempts"] == int(attempts), data
assert data["retries"] == int(retries), data
assert str(data["recovered"]).lower() == recovered.lower(), data
print(
    "OK: "
    f"http_status={data['http_status']} "
    f"attempts={data['attempts']} "
    f"retries={data['retries']} "
    f"recovered={data['recovered']} "
    f"waits={data['waits']}"
)
PY
}

assert_stats() {
  local file="$1"
  local expected_total="$2"
  local expected_failed="$3"
  local expected_success="$4"
  local expected_statuses="$5"
  python3 - "$file" "$expected_total" "$expected_failed" "$expected_success" "$expected_statuses" <<'PY'
import json
import sys

path, total, failed, success, statuses = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

expected_codes = [int(code) for code in statuses.split(",")]
actual_codes = [attempt["status_code"] for attempt in data["attempts"]]
assert data["total_requests"] == int(total), data
assert data["failed_requests"] == int(failed), data
assert data["successful_requests"] == int(success), data
assert actual_codes == expected_codes, data
assert data["total_requests"] == len(data["attempts"]), data
print(
    "OK: "
    f"total={data['total_requests']} "
    f"failed={data['failed_requests']} "
    f"successful={data['successful_requests']} "
    f"statuses={actual_codes}"
)
PY
}

wait_for_health "$BASE_URL"

RUN_NORMAL="$RUN_PREFIX-normal"
RUN_TRANSIENT="$RUN_PREFIX-transient"
RUN_PERMANENT="$RUN_PREFIX-permanent"
RUN_BAD="$RUN_PREFIX-bad"
RUN_BACKOFF="$RUN_PREFIX-backoff"

# ---------------------------------------------------------------------------
# 03 - Operacion normal
# ---------------------------------------------------------------------------
http_get "$BASE_URL/request?scenario=success&run_id=$RUN_NORMAL" "$TMP_DIR/03.json"
{
  echo "# 03 - Operacion normal: un solo intento, sin reintentos"
  echo "Fecha: $(date -Is)"
  echo "URL base: $BASE_URL"
  echo
  echo "\$ curl -sS \"$BASE_URL/request?scenario=success&run_id=$RUN_NORMAL\""
  echo "HTTP $HTTP_CODE"
  python3 -m json.tool "$TMP_DIR/03.json"
  echo
  echo "\$ curl -sS \"$BASE_URL/backend/stats?run_id=$RUN_NORMAL\""
  curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_NORMAL" \
    | python3 -m json.tool
} | tee "$EVID/03-normal-operation.txt"

assert_eq "$HTTP_CODE" "200" "03 deberia devolver HTTP 200"
assert_response "$TMP_DIR/03.json" 200 1 0 false

# ---------------------------------------------------------------------------
# 04 - Recuperacion tras dos fallos transitorios
# ---------------------------------------------------------------------------
http_get "$BASE_URL/request?scenario=transient&run_id=$RUN_TRANSIENT" "$TMP_DIR/04.json"
{
  echo "# 04 - Recuperacion: 503, 503 y 200 en el tercer intento"
  echo "Fecha: $(date -Is)"
  echo "URL base: $BASE_URL"
  echo
  echo "\$ curl -sS \"$BASE_URL/request?scenario=transient&run_id=$RUN_TRANSIENT\""
  echo "HTTP $HTTP_CODE"
  python3 -m json.tool "$TMP_DIR/04.json"
  echo
  echo "\$ curl -sS \"$BASE_URL/backend/stats?run_id=$RUN_TRANSIENT\""
  curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_TRANSIENT" \
    | python3 -m json.tool
} | tee "$EVID/04-retry-recovery.txt"

assert_eq "$HTTP_CODE" "200" "04 deberia devolver HTTP 200"
assert_response "$TMP_DIR/04.json" 200 3 2 true

# ---------------------------------------------------------------------------
# 05 - Agotamiento de intentos con error permanente
# ---------------------------------------------------------------------------
http_get "$BASE_URL/request?scenario=permanent&run_id=$RUN_PERMANENT" "$TMP_DIR/05.json"
{
  echo "# 05 - Agotamiento: tres intentos y error final controlado"
  echo "Fecha: $(date -Is)"
  echo "URL base: $BASE_URL"
  echo
  echo "\$ curl -sS \"$BASE_URL/request?scenario=permanent&run_id=$RUN_PERMANENT\""
  echo "HTTP $HTTP_CODE"
  python3 -m json.tool "$TMP_DIR/05.json"
  echo
  echo "\$ curl -sS \"$BASE_URL/backend/stats?run_id=$RUN_PERMANENT\""
  curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_PERMANENT" \
    | python3 -m json.tool
} | tee "$EVID/05-retry-exhausted.txt"

assert_eq "$HTTP_CODE" "503" "05 deberia devolver HTTP 503"
assert_response "$TMP_DIR/05.json" 503 3 2 false

# ---------------------------------------------------------------------------
# 06 - HTTP 400 no se reintenta
# ---------------------------------------------------------------------------
http_get "$BASE_URL/request?scenario=bad_request&run_id=$RUN_BAD" "$TMP_DIR/06.json"
{
  echo "# 06 - Error no reintentable: HTTP 400 con un solo intento"
  echo "Fecha: $(date -Is)"
  echo "URL base: $BASE_URL"
  echo
  echo "\$ curl -sS \"$BASE_URL/request?scenario=bad_request&run_id=$RUN_BAD\""
  echo "HTTP $HTTP_CODE"
  python3 -m json.tool "$TMP_DIR/06.json"
  echo
  echo "\$ curl -sS \"$BASE_URL/backend/stats?run_id=$RUN_BAD\""
  curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_BAD" \
    | python3 -m json.tool
} | tee "$EVID/06-no-retry-400.txt"

assert_eq "$HTTP_CODE" "400" "06 deberia devolver HTTP 400"
assert_response "$TMP_DIR/06.json" 400 1 0 false

# ---------------------------------------------------------------------------
# 07 - Exponential Backoff
# ---------------------------------------------------------------------------
http_get "$BASE_URL/request?scenario=transient&run_id=$RUN_BACKOFF" "$TMP_DIR/07.json"
{
  echo "# 07 - Exponential Backoff: esperas progresivas entre intentos"
  echo "Fecha: $(date -Is)"
  echo "URL base: $BASE_URL"
  echo
  echo "\$ curl -sS \"$BASE_URL/request?scenario=transient&run_id=$RUN_BACKOFF\""
  echo "HTTP $HTTP_CODE"
  python3 -m json.tool "$TMP_DIR/07.json"
  echo
  python3 - "$TMP_DIR/07.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)

timestamps = [attempt["timestamp"] for attempt in data["attempt_details"]]
deltas = [
    round(timestamps[index + 1] - timestamps[index], 3)
    for index in range(len(timestamps) - 1)
]
print("Esperas configuradas (waits):", data["waits"])
print("Intervalos reales entre intentos (s):", deltas)
assert data["waits"] == [0.5, 1.0], data["waits"]
assert len(deltas) == 2, deltas
assert deltas[0] >= 0.45, deltas
assert deltas[1] >= 0.95, deltas
print("OK: el intervalo crece de ~0.5 s a ~1.0 s")
PY
} | tee "$EVID/07-exponential-backoff.txt"

assert_eq "$HTTP_CODE" "200" "07 deberia devolver HTTP 200"
assert_response "$TMP_DIR/07.json" 200 3 2 true

# ---------------------------------------------------------------------------
# 08 - Contadores del backend
# ---------------------------------------------------------------------------
curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_NORMAL" > "$TMP_DIR/08-normal.json"
curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_TRANSIENT" > "$TMP_DIR/08-transient.json"
curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_PERMANENT" > "$TMP_DIR/08-permanent.json"
curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_BAD" > "$TMP_DIR/08-bad.json"
curl -sS --max-time 10 "$BASE_URL/backend/stats?run_id=$RUN_BACKOFF" > "$TMP_DIR/08-backoff.json"

{
  echo "# 08 - Contadores del backend por run_id"
  echo "Fecha: $(date -Is)"
  echo
  for item in \
    "normal:$RUN_NORMAL:$TMP_DIR/08-normal.json" \
    "transient:$RUN_TRANSIENT:$TMP_DIR/08-transient.json" \
    "permanent:$RUN_PERMANENT:$TMP_DIR/08-permanent.json" \
    "bad_request:$RUN_BAD:$TMP_DIR/08-bad.json" \
    "backoff:$RUN_BACKOFF:$TMP_DIR/08-backoff.json"; do
    name="${item%%:*}"
    rest="${item#*:}"
    run_id="${rest%%:*}"
    file="${rest#*:}"
    echo "## $name ($run_id)"
    python3 -m json.tool "$file"
    echo
  done
  echo "## Verificacion"
  python3 - "$TMP_DIR" <<'PY'
import json
import pathlib
import sys

tmp = pathlib.Path(sys.argv[1])
expected = {
    "08-normal.json": (1, 0, 1, [200]),
    "08-transient.json": (3, 2, 1, [503, 503, 200]),
    "08-permanent.json": (3, 3, 0, [503, 503, 503]),
    "08-bad.json": (1, 1, 0, [400]),
    "08-backoff.json": (3, 2, 1, [503, 503, 200]),
}
for filename, (total, failed, success, codes) in expected.items():
    data = json.loads((tmp / filename).read_text(encoding="utf-8"))
    actual_codes = [attempt["status_code"] for attempt in data["attempts"]]
    assert data["total_requests"] == total, (filename, data)
    assert data["failed_requests"] == failed, (filename, data)
    assert data["successful_requests"] == success, (filename, data)
    assert actual_codes == codes, (filename, data)
    assert data["total_requests"] == len(data["attempts"]), (filename, data)
    print(f"OK {filename}: total={total} statuses={actual_codes}")
PY
} | tee "$EVID/08-backend-stats.txt"

assert_stats "$TMP_DIR/08-normal.json" 1 0 1 "200"
assert_stats "$TMP_DIR/08-transient.json" 3 2 1 "503,503,200"
assert_stats "$TMP_DIR/08-permanent.json" 3 3 0 "503,503,503"
assert_stats "$TMP_DIR/08-bad.json" 1 1 0 "400"
assert_stats "$TMP_DIR/08-backoff.json" 3 2 1 "503,503,200"

echo
echo "Demostracion completada. Evidencias generadas en $EVID/"
