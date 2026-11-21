"""AWS Lambda handler sin dependencias externas."""
import json


def lambda_handler(event, context):
    path = event.get("rawPath") or event.get("path") or "/"

    if path == "/health":
        payload = {"status": "ok"}
        status = 200
    elif path == "/":
        payload = {
            "message": "Hola desde AWS Lambda",
            "runtime": "lambda",
            "project": "cloud-patterns-lab",
        }
        status = 200
    else:
        payload = {"error": "Ruta no encontrada", "path": path}
        status = 404

    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }
