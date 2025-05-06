from sqlalchemy.orm import Session
from models.models import TransactionStates
import logging

logger = logging.getLogger(__name__)

def get_transaction_state(db: Session, state_name: str):
    """
    Obtiene el estado para transacciones.

    Args:
        db (Session): Sesión de la base de datos.
        state_name (str): Nombre del estado a obtener (e.g., "Activo", "Inactivo").

    Returns:
        El objeto de estado si se encuentra, None en caso contrario.
    """
    try:
        return db.query(TransactionStates).filter(TransactionStates.name == state_name).first()
    except Exception as e:
        logger.error(f"Error al obtener el estado '{state_name}' para transacciones: {str(e)}")
        return None
