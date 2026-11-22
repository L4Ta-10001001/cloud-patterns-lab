import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "lambda" / "lambda_function.py"
spec = importlib.util.spec_from_file_location("lab04_lambda", MODULE_PATH)
lambda_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_module)


def test_lambda_root():
    response = lambda_module.lambda_handler({"rawPath": "/"}, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["runtime"] == "lambda"


def test_lambda_health():
    response = lambda_module.lambda_handler({"rawPath": "/health"}, None)
    assert json.loads(response["body"]) == {"status": "ok"}


def test_lambda_404():
    response = lambda_module.lambda_handler({"rawPath": "/inexistente"}, None)
    assert response["statusCode"] == 404
