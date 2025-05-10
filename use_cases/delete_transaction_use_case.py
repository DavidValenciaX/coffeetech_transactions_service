from models.models import Transactions
from utils.response import create_response, session_token_invalid_response
from utils.state import get_transaction_state
from adapters.user_client import verify_session_token, get_role_permissions_for_user_role
from adapters.farm_client import get_user_role_farm_state_by_name, get_user_role_farm, verify_plot
import logging

logger = logging.getLogger(__name__)

def delete_transaction_use_case(request, session_token, db):
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Obtener la transacción a eliminar
    transaction = db.query(Transactions).filter(Transactions.transaction_id == request.transaction_id).first()
    if not transaction:
        logger.warning(f"La transacción con ID {request.transaction_id} no existe")
        return create_response("error", "La transacción especificada no existe", status_code=404)
    
    # 4. Verificar que la transacción no esté ya inactiva
    inactive_transaction_state = get_transaction_state(db, "Inactivo")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    if transaction.transaction_state_id == inactive_transaction_state.transaction_state_id:
        logger.warning(f"La transacción con ID {request.transaction_id} ya está inactiva")
        return create_response("error", "La transacción ya está eliminada", status_code=400)
    
    # 5. Determinar el farm_id según el tipo de entidad de la transacción
    farm_id = None
    if transaction.entity_type == "farm":
        farm_id = transaction.entity_id
    elif transaction.entity_type == "plot":
        # Verificar si el lote existe y obtener su farm_id
        plot_info = verify_plot(transaction.entity_id)
        if not plot_info:
            logger.warning(f"El lote con ID {transaction.entity_id} no existe o no está activo")
            return create_response("error", "El lote asociado a esta transacción no existe o no está activo", status_code=404)
        farm_id = plot_info.farm_id
    else:
        logger.error(f"Tipo de entidad no soportado: {transaction.entity_type}")
        return create_response("error", "Tipo de entidad no soportado", status_code=400)
    
    # 6. Verificar que el usuario esté asociado con la finca
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {farm_id}")
        return create_response("error", "No tienes permisos para eliminar transacciones en esta finca", status_code=403)
    
    # 7. Verificar permiso 'delete_transaction' usando el cliente del servicio de usuarios
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if not permissions or "delete_transaction" not in permissions:
        logger.warning(f"El rol del usuario no tiene permiso para eliminar transacciones")
        return create_response("error", "No tienes permiso para eliminar transacciones", status_code=403)
    
    # 8. Cambiar el estado de la transacción a 'Inactivo'
    try:
        transaction.transaction_state_id = inactive_transaction_state.transaction_state_id
        db.commit()
        logger.info(f"Transacción con ID {transaction.transaction_id} eliminada exitosamente")
        return create_response("success", "Transacción eliminada correctamente", data={"transaction_id": transaction.transaction_id})
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar la transacción: {str(e)}")
        return create_response("error", f"Error al eliminar la transacción: {str(e)}", status_code=500)
