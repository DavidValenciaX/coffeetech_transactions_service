from fastapi.responses import ORJSONResponse
from datetime import datetime, date, time
from uuid import UUID
from typing import Any, Optional
from pydantic import BaseModel
from decimal import Decimal

def process_data_for_json(value: Any) -> Any:
    """
    Procesa datos para serialización JSON, manejando tipos especiales:
      - BaseModel (Pydantic)
      - Decimal
      - datetime, date, time
      - UUID
      - colecciones anidadas (dict, list, tuple, set)

    Args:
        value (Any): Valor a procesar para serialización JSON

    Returns:
        Any: Valor procesado compatible con JSON
    """
    # BaseModel -> dict
    if isinstance(value, BaseModel):
        return value.model_dump()
    # Decimal -> float
    if isinstance(value, Decimal):
        return float(value)
    # datetime types -> ISO string
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    # UUID -> str
    if isinstance(value, UUID):
        return str(value)
    # Collections -> process recursively
    if isinstance(value, dict):
        return {k: process_data_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [process_data_for_json(item) for item in value]
    # Leave other types as-is
    return value

def create_response(
    status: str,
    message: str,
    data: Optional[Any] = None,
    status_code: int = 200
) -> ORJSONResponse:
    """
    Crea una respuesta JSON rápida y robusta con ORJSON,
    procesando tipos especiales y permitiendo serializar:
      - BaseModel (Pydantic)
      - Decimal
      - datetime, date, time
      - UUID
      - dict, list, tuple, set anidados

    Args:
        status (str): "success" o "error".
        message (str): Mensaje descriptivo.
        data (Optional[Any]): Cualquier dato JSON-like o modelo/Decimal.
        status_code (int): Código HTTP (por defecto 200).

    Returns:
        ORJSONResponse: Respuesta con JSON ultra-rápido.
    """
    
    processed = process_data_for_json(data) if data is not None else {}

    return ORJSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "message": message,
            "data": processed
        }
    )


def session_token_invalid_response() -> ORJSONResponse:
    """
    Crea una respuesta para cuando el token de sesión es inválido.

    Returns:
        JSONResponse: Respuesta en formato JSON que indica que las credenciales han expirado.
    """
    return create_response(
        status="error",
        message="Credenciales expiradas, cerrando sesión.",
        data={},
        status_code=401
    )