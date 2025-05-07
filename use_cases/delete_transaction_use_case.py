from models.models import Transactions
from utils.response import create_response, session_token_invalid_response
from utils.state import get_transaction_state
from adapters.user_client import verify_session_token
from adapters.farm_client import get_user_role_farm_state_by_name
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
    
    # 5. Verificar que el usuario esté asociado con la finca del lote de la transacción
    active_urf_state = get_user_role_farm_state_by_name("Activo")
    if not active_urf_state or not active_urf_state.get("user_role_farm_state_id"):
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == transaction.plot.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state["user_role_farm_state_id"]
    ).first()
    
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {transaction.plot.farm_id}")
        return create_response("error", "No tienes permisos para eliminar transacciones en esta finca", status_code=403)
    
    # 6. Verificar permiso 'delete_transaction'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "delete_transaction"
    ).first()
    
    if not role_permission:
        logger.warning(f"El rol {user_role_farm.role_id} del usuario no tiene permiso para eliminar transacciones")
        return create_response("error", "No tienes permiso para eliminar transacciones", status_code=403)
    
    # 7. Cambiar el estado de la transacción a 'Inactivo'
    try:
        transaction.transaction_state_id = inactive_transaction_state.transaction_state_id
        db.commit()
        logger.info(f"Transacción con ID {transaction.transaction_id} eliminada exitosamente")
        return create_response("success", "Transacción eliminada correctamente", data={"transaction_id": transaction.transaction_id})
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar la transacción: {str(e)}")
        return create_response("error", f"Error al eliminar la transacción: {str(e)}", status_code=500)
