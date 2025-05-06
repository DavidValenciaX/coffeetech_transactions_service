from utils.response import create_response, session_token_invalid_response
from utils.state import get_state
from models.models import (
    Transactions, TransactionTypes, TransactionCategories, TransactionStates
)
import logging

logger = logging.getLogger(__name__)

def list_transactions_use_case(plot_id, session_token, db):

    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Verificar que el lote exista y esté activo
    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        logger.error("Estado 'Activo' para Plots no encontrado")
        return create_response("error", "Estado 'Activo' para Plots no encontrado", status_code=400)
    
    plot = db.query(Plots).filter(
        Plots.plot_id == plot_id,
        Plots.plot_state_id == active_plot_state.plot_state_id
    ).first()
    if not plot:
        logger.warning(f"El lote con ID {plot_id} no existe o no está activo")
        return create_response("error", "El lote no existe o no está activo", status_code=404)
    
    # 4. Verificar que el usuario esté asociado con la finca del lote
    farm = db.query(Farms).filter(Farms.farm_id == plot.farm_id).first()
    if not farm:
        logger.warning("La finca asociada al lote no existe")
        return create_response("error", "La finca asociada al lote no existe", status_code=404)
    
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        logger.warning(f"El usuario no está asociado con la finca con ID {farm.farm_id}")
        return create_response("error", "No tienes permiso para ver las transacciones en esta finca", status_code=403)
    
    # 5. Verificar permiso 'read_transaction'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "read_transaction"
    ).first()
    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para leer transacciones")
        return create_response("error", "No tienes permiso para ver las transacciones en esta finca", status_code=403)
    
    # 6. Obtener el estado "Inactivo" para Transactions
    inactive_transaction_state = get_state(db, "Inactivo", "Transactions")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    # 7. Consultar las transacciones del lote que no están inactivas
    transactions = db.query(Transactions).filter(
        Transactions.plot_id == plot_id,
        Transactions.transaction_state_id != inactive_transaction_state.transaction_state_id
    ).all()
    
    # 8. Preparar la lista de transacciones
    transaction_list = []
    for txn in transactions:
        # Obtener el tipo de transacción
        txn_type = db.query(TransactionTypes).filter(TransactionTypes.transaction_type_id == txn.transaction_type_id).first()
        txn_type_name = txn_type.name if txn_type else "Desconocido"
        
        # Obtener la categoría de la transacción
        txn_category = db.query(TransactionCategories).filter(TransactionCategories.transaction_category_id == txn.transaction_category_id).first()
        txn_category_name = txn_category.name if txn_category else "Desconocido"
        
        # Obtener el estado de la transacción
        transaction_state = db.query(TransactionStates).filter(TransactionStates.transaction_state_id == txn.transaction_state_id).first()
        transaction_state_name = transaction_state.name if transaction_state else "Desconocido"
        
        transaction_list.append({
            "transaction_id": txn.transaction_id,
            "plot_id": txn.plot_id,
            "transaction_type_name": txn_type_name,
            "transaction_category_name": txn_category_name,
            "description": txn.description,
            "value": txn.value,
            "transaction_date": txn.transaction_date.isoformat(),
            "transaction_state": transaction_state_name
        })
    
    if not transaction_list:
        return create_response("success", "El lote no tiene transacciones registradas", {"transactions": []})
    
    return create_response("success", "Transacciones obtenidas exitosamente", {"transactions": transaction_list})
