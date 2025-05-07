from dotenv import load_dotenv
from pydantic import BaseModel
import os
import logging
import httpx
import time

load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

FARMS_SERVICE_URL = os.getenv("FARMS_SERVICE_URL", "http://localhost:8002")

class FarmDetailResponse(BaseModel):
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str
    farm_state_id: int
    farm_state: str

class UserRoleFarmResponse(BaseModel):
    user_role_farm_id: int
    user_role_id: int
    farm_id: int
    user_role_farm_state_id: int
    user_role_farm_state: str

def get_farm_by_id(farm_id: int):
    """
    Solicita la información de una finca al servicio de farms.
    """
    url = f"{FARMS_SERVICE_URL}/farms-service/get-farm/{farm_id}"
    start_time = time.monotonic() # Registrar tiempo de inicio
    logger.info(f"Consultando finca ID {farm_id} en {url}...")
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url)
            duration = time.monotonic() - start_time # Calcular duración
            logger.info(f"Consulta a {url} finalizada en {duration:.4f} segundos con estado {response.status_code}")
            response.raise_for_status()
            data = response.json()
            # Si la respuesta es un dict con los campos esperados, parsear con el modelo
            return FarmDetailResponse(**data)
    except httpx.TimeoutException as e: # Capturar específicamente Timeout
        duration = time.monotonic() - start_time
        logger.error(f"Timeout ({e}) al consultar finca {farm_id} en {url} después de {duration:.4f} segundos")
        return None
    except Exception as e:
        duration = time.monotonic() - start_time
        logger.error(f"Error ({type(e).__name__}: {e}) al consultar finca {farm_id} en {url} después de {duration:.4f} segundos")
        return None

def get_user_role_farm(user_id: int, farm_id: int):
    """
    Solicita la relación user_role_farm y su estado al servicio de farms.
    """
    url = f"{FARMS_SERVICE_URL}/farms-service/get-user-role-farm/{user_id}/{farm_id}"
    try:
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            if "status" in data and data["status"] == "error":
                return None
            return UserRoleFarmResponse(**data)
    except Exception as e:
        logger.error(f"Error al consultar user_role_farm: {e}")
        return None

def create_user_role_farm(user_role_id: int, farm_id: int, user_role_farm_state_id: int):
    """
    Crea la relación UserRoleFarm en el servicio de fincas.
    """
    url = f"{FARMS_SERVICE_URL}/farms-service/create-user-role-farm"
    payload = {
        "user_role_id": user_role_id,
        "farm_id": farm_id,
        "user_role_farm_state_id": user_role_farm_state_id
    }
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al crear user_role_farm: {e}")
        return {"status": "error", "message": f"Error al crear user_role_farm: {str(e)}"}

def get_user_role_farm_state_by_name(state_name: str):
    """
    Consulta el estado de UserRoleFarm por nombre en el servicio de fincas.
    """
    url = f"{FARMS_SERVICE_URL}/farms-service/get-user-role-farm-state/{state_name}"
    try:
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            if "status" in data and data["status"] == "error":
                return None
            return data
    except Exception as e:
        logger.error(f"Error al consultar user_role_farm_state: {e}")
        return None
