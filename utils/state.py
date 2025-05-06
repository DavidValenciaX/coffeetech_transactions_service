from sqlalchemy.orm import Session
from models.models import TransactionStates
import logging

logger = logging.getLogger(__name__)

def get_state(db: Session, state_name: str, entity_type: str):
    """
    Obtiene el estado para diferentes entidades.
    
    Args:
        db (Session): Sesión de la base de datos.
        state_name (str): Nombre del estado a obtener (e.g., "Activo", "Inactivo").
        entity_type (str): Tipo de entidad (e.g., "Farms", "Users", "Plots").
        
    Returns:
        El objeto de estado si se encuentra, None en caso contrario.
    """
    try:
        if entity_type.lower() == "transactions":
            return db.query(TransactionStates).filter(TransactionStates.name == state_name).first()
        else:
            logger.error(f"Tipo de entidad desconocido: {entity_type}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener el estado '{state_name}' para '{entity_type}': {str(e)}")
        return None
