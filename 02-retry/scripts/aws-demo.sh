#!/usr/bin/env bash
# Ejecuta la demostracion del patron Retry contra ECS Fargate y guarda las
# evidencias 13 (demo AWS) y 14 (CloudWatch).
#
# Requisitos:
#   - AWS CLI configurado con permisos ECS/EC2/CloudWatch.
#   - La tarea Fargate en ejecucion.
#
# Uso:
#   bash scripts/aws-demo.sh
#   BASE_URL=http://IP:8000 bash scripts/aws-demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVID="${EVID_DIR:-$ROOT/evidencias}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
PROJECT_PREFIX="${PROJECT_PREFIX:-cloudlab-erik}"
CLUSTER="${ECS_CLUSTER:-${PROJECT_PREFIX}-retry-cluster}"
SERVICE="${ECS_SERVICE:-${PROJECT_PREFIX}-retry-service}"
RUN_PREFIX="${RUN_PREFIX:-aws-$(date +%Y%m%d-%H%M%S)}"
FETCH_LOGS="${FETCH_LOGS:-1}"

mkdir -p "$EVID"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

export AWS_DEFAULT_REGION="$AWS_REGION"

echo "=== Descubriendo la tarea ECS ==="
TASK_ARN="$(aws ecs list-tasks \
  --cluster "$CLUSTER" \
  --service-name "$SERVICE" \
  --desired-status RUNNING \
  --query 'taskArns[0]' \
  --output text)"

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" = "None" ]; then
  echo "ERROR: no hay una tarea RUNNING para $CLUSTER/$SERVICE" >&2
  exit 1
fi

ENI="$(aws ecs describe-tasks \
  --cluster "$CLUSTER" \
  --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)"

PUBLIC_IP="$(aws ec2 describe-network-interfaces \
  --network-interface-ids "$ENI" \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)"

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" = "None" ]; then
  echo "ERROR: la tarea no tiene IP publica" >&2
  exit 1
fi

BASE_URL="${BASE_URL:-http://$PUBLIC_IP:8000}"

echo "Tarea: $TASK_ARN"
echo "IP publica: $PUBLIC_IP"
echo "URL base: $BASE_URL"

echo "=== Esperando disponibilidad HTTP ==="
for i in $(seq 1 40); do
  if curl -fsS --max-time 3 "$BASE_URL/health" >/dev/null 2>&1; then
    echo "Cliente disponible (intento $i)"
    break
  fi
  if [ "$i" = 40 ]; then
    echo "ERROR: $BASE_URL/health no respondio" >&2
    exit 1
  fi
  sleep 2
done

echo "=== Ejecutando la demostracion ==="
mkdir -p "$TMP_DIR/evidencias"
BASE_URL="$BASE_URL" \
  EVID_DIR="$TMP_DIR/evidencias" \
  RUN_PREFIX="$RUN_PREFIX" \
  bash "$ROOT/scripts/demo.sh" | tee "$TMP_DIR/demo.log"

{
  echo "# 13 - Demostracion del patron Retry en AWS ECS Fargate"
  echo "Fecha: $(date -Is)"
  echo "Region: $AWS_REGION"
  echo "Cluster: $CLUSTER"
  echo "Servicio: $SERVICE"
  echo "Tarea: $TASK_ARN"
  echo "IP publica: $PUBLIC_IP"
  echo "URL base: $BASE_URL"
  echo
  echo "## Servicio ECS"
  aws ecs describe-services \
    --cluster "$CLUSTER" \
    --services "$SERVICE" \
    --query 'services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount,taskDefinition:taskDefinition,launchType:launchType}' \
    --output json
  echo
  echo "## Tarea ECS"
  aws ecs describe-tasks \
    --cluster "$CLUSTER" \
    --tasks "$TASK_ARN" \
    --query 'tasks[0].{lastStatus:lastStatus,healthStatus:healthStatus,containers:containers[].{name:name,lastStatus:lastStatus,healthStatus:healthStatus}}' \
    --output json
  echo
  echo "## Salida de scripts/demo.sh"
  cat "$TMP_DIR/demo.log"
  echo
  for file in \
    03-normal-operation.txt \
    04-retry-recovery.txt \
    05-retry-exhausted.txt \
    06-no-retry-400.txt \
    07-exponential-backoff.txt \
    08-backend-stats.txt; do
    echo "## $file"
    cat "$TMP_DIR/evidencias/$file"
    echo
  done
} | tee "$EVID/13-aws-demo.txt"

if [ "$FETCH_LOGS" = "1" ]; then
  echo "=== Esperando ingestion de logs en CloudWatch ==="
  sleep 8

  LOG_CLIENT="/ecs/${PROJECT_PREFIX}-retry-client"
  LOG_BACKEND="/ecs/${PROJECT_PREFIX}-retry-backend"
  START_TIME="$(( ( $(date +%s) - 900 ) * 1000 ))"

  aws logs filter-log-events \
    --log-group-name "$LOG_CLIENT" \
    --start-time "$START_TIME" \
    --query 'events[].message' \
    --output text > "$TMP_DIR/client.log"

  aws logs filter-log-events \
    --log-group-name "$LOG_BACKEND" \
    --start-time "$START_TIME" \
    --query 'events[].message' \
    --output text > "$TMP_DIR/backend.log"

  {
    echo "# 14 - Logs de CloudWatch de la ejecucion en ECS"
    echo "Fecha: $(date -Is)"
    echo "Region: $AWS_REGION"
    echo "Log group cliente: $LOG_CLIENT"
    echo "Log group backend: $LOG_BACKEND"
    echo
    echo "## Cliente (intentos, esperas y recuperacion)"
    cat "$TMP_DIR/client.log"
    echo
    echo "## Backend (peticiones recibidas por run_id)"
    cat "$TMP_DIR/backend.log"
  } | tee "$EVID/14-cloudwatch.txt"
else
  echo "FETCH_LOGS=0: se omite 14-cloudwatch.txt"
fi

echo
echo "Evidencias AWS generadas en $EVID/"
