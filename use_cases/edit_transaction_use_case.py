from models.models import (
    Transactions, TransactionTypes, TransactionCategories, TransactionStates,
    UserRoleFarm, RolePermission, Permissions
)
from utils.security import verify_session_token
from utils.response import session_token_invalid_response, create_response
from utils.state import get_state
from fastapi.encoders import jsonable_encoder
from endpoints.transactions import TransactionResponse
import logging

logger = logging.getLogger(__name__)

def edit_transaction_use_case(request, session_token, db):
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Obtener la transacción a actualizar
    transaction = db.query(Transactions).filter(Transactions.transaction_id == request.transaction_id).first()
    if not transaction:
        logger.warning(f"La transacción con ID {request.transaction_id} no existe")
        return create_response("error", "La transacción especificada no existe", status_code=404)
    
    # 4. Verificar que la transacción no esté inactiva
    inactive_transaction_state = get_state(db, "Inactivo", "Transactions")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    if transaction.transaction_state_id == inactive_transaction_state.transaction_state_id:
        logger.warning(f"La transacción con ID {request.transaction_id} está inactiva y no puede ser modificada")
        return create_response("error", "La transacción está inactiva y no puede ser modificada", status_code=403)
 
    # 5. Verificar que el usuario esté asociado con la finca del lote de la transacción
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == transaction.plot.farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {transaction.plot.farm_id}")
        return create_response("error", "No tienes permisos para editar transacciones en esta finca", status_code=403)
    
    # 6. Verificar permiso 'edit_transaction'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "edit_transaction"
    ).first()
    
    if not role_permission:
        logger.warning(f"El rol {user_role_farm.role_id} del usuario no tiene permiso para editar transacciones")
        return create_response("error", "No tienes permiso para editar transacciones", status_code=403)
    
    # 7. Realizar las actualizaciones permitidas
    try:
        # Actualizar el tipo de transacción si se proporciona
        if request.transaction_type_name:
            transaction_type = db.query(TransactionTypes).filter(TransactionTypes.name == request.transaction_type_name).first()
            if not transaction_type:
                logger.warning(f"El tipo de transacción '{request.transaction_type_name}' no existe")
                return create_response("error", "El tipo de transacción especificado no existe", status_code=400)
            transaction.transaction_type_id = transaction_type.transaction_type_id
        
        # Actualizar la categoría de transacción si se proporciona
        if request.transaction_category_name:
            # Si el tipo de transacción se ha actualizado en este mismo request, usar el nuevo tipo
            current_transaction_type_id = request.transaction_type_name and transaction_type.transaction_type_id or transaction.transaction_type_id
            transaction_category = db.query(TransactionCategories).filter(
                TransactionCategories.name == request.transaction_category_name,
                TransactionCategories.transaction_type_id == current_transaction_type_id
            ).first()
            if not transaction_category:
                logger.warning(f"La categoría de transacción '{request.transaction_category_name}' no existe para el tipo de transacción actual")
                return create_response("error", "La categoría de transacción especificada no existe para el tipo de transacción actual", status_code=400)
            transaction.transaction_category_id = transaction_category.transaction_category_id
        
        # Actualizar la descripción si se proporciona
        if request.description is not None:
            if len(request.description) > 50:
                logger.warning("La descripción excede los 50 caracteres")
                return create_response("error", "La descripción no puede exceder los 50 caracteres", status_code=400)
            transaction.description = request.description
        
        # Actualizar el valor si se proporciona
        if request.value is not None:
            if request.value <= 0:
                logger.warning("El valor de la transacción debe ser positivo")
                return create_response("error", "El valor de la transacción debe ser positivo", status_code=400)
            transaction.value = request.value
        
        # Actualizar la fecha de la transacción si se proporciona
        if request.transaction_date is not None:
            transaction.transaction_date = request.transaction_date
        
        db.commit()
        db.refresh(transaction)
        
        # Obtener el estado actual directamente por ID
        transaction_current_state = db.query(TransactionStates).filter(TransactionStates.transaction_state_id == transaction.transaction_state_id).first()
        transaction_state_name = transaction_current_state.name if transaction_current_state else "Desconocido"
        
        # Obtener el tipo de transacción actualizado
        txn_type = db.query(TransactionTypes).filter(TransactionTypes.transaction_type_id == transaction.transaction_type_id).first()
        txn_type_name = txn_type.name if txn_type else "Desconocido"
        
        # Obtener la categoría de transacción actualizada
        txn_category = db.query(TransactionCategories).filter(TransactionCategories.transaction_category_id == transaction.transaction_category_id).first()
        txn_category_name = txn_category.name if txn_category else "Desconocido"
        
        response_data = TransactionResponse(
            transaction_id=transaction.transaction_id,
            plot_id=transaction.plot_id,
            transaction_type_name=txn_type_name,
            transaction_category_name=txn_category_name,
            description=transaction.description,
            value=transaction.value,
            transaction_date=transaction.transaction_date,
            transaction_state=transaction_state_name
        )
        
        response_dict = jsonable_encoder(response_data.dict())

        logger.info(f"Transacción con ID {transaction.transaction_id} actualizada exitosamente")
        
        return create_response("success", "Transacción actualizada correctamente", data=response_dict)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar la transacción: {str(e)}")
        return create_response("error", f"Error al actualizar la transacción: {str(e)}", status_code=500)
