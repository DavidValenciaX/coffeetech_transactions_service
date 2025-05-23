from fastapi import Depends
from models.models import (
    Transactions, TransactionCategories, TransactionStates
)
from utils.response import session_token_invalid_response, create_response
from utils.state import get_transaction_state
from fastapi.encoders import jsonable_encoder
from domain.schemas import TransactionResponse, UpdateTransactionRequest
from adapters.user_client import verify_session_token, get_role_permissions_for_user_role
from adapters.farm_client import get_user_role_farm_state_by_name, get_user_role_farm, verify_plot
import logging
from sqlalchemy.orm import joinedload, Session
from dataBase import get_db_session

logger = logging.getLogger(__name__)

def edit_transaction_use_case(request: UpdateTransactionRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Editar una transacción existente para un lote en una finca.
    - **transaction
    - **transaction
    - **transaction_category_id**: Nuevo ID de la categoría de la transacción
    - **value**: Nuevo valor monetario de la transacción
    - **description**: Nueva descripción de la transacción
    """
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Obtener la transacción a actualizar
    transaction = db.query(Transactions).filter(Transactions.transaction_id == request.transaction_id).first()
    if not transaction:
        logger.warning(f"La transacción con ID {request.transaction_id} no existe")
        return create_response("error", "La transacción especificada no existe", status_code=404)
    
    # 4. Verificar que la transacción no esté inactiva
    inactive_transaction_state = get_transaction_state(db, "Inactivo")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    if transaction.transaction_state_id == inactive_transaction_state.transaction_state_id:
        logger.warning(f"La transacción con ID {request.transaction_id} está inactiva y no puede ser modificada")
        return create_response("error", "La transacción está inactiva y no puede ser modificada", status_code=403)
 
    # 5. Verificar que el usuario esté asociado con la finca del lote/entidad de la transacción
    # Obtener el estado activo para user_role_farm usando el cliente del servicio de fincas
    active_urf_state = get_user_role_farm_state_by_name("Activo")
    if not active_urf_state or not active_urf_state.get("user_role_farm_state_id"):
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    # Determinar el farm_id según el lote de la transacción
    plot_info = verify_plot(transaction.plot_id)
    if not plot_info:
        logger.warning(f"El lote con ID {transaction.plot_id} no existe o no está activo")
        return create_response("error", "El lote asociado a esta transacción no existe o no está activo", status_code=404)
    farm_id = plot_info.farm_id
    
    # Utilizar el cliente del servicio de fincas para obtener la relación usuario-finca
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {farm_id}")
        return create_response("error", "No tienes permisos para editar transacciones en esta finca", status_code=403)
    
    # 6. Verificar permiso 'edit_transaction' usando el cliente del servicio de usuarios
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if not permissions or "edit_transaction" not in permissions:
        logger.warning(f"El rol del usuario no tiene permiso para editar transacciones")
        return create_response("error", "No tienes permiso para editar transacciones", status_code=403)
    
    # 7. Realizar las actualizaciones permitidas
    try:
        # Actualizar la categoría de transacción si se proporciona
        if request.transaction_category_id is not None:
            transaction_category = db.query(TransactionCategories).filter(
                TransactionCategories.transaction_category_id == request.transaction_category_id
            ).first()
            if not transaction_category:
                logger.warning(f"La categoría de transacción con ID '{request.transaction_category_id}' no existe")
                return create_response("error", "La categoría de transacción especificada no existe", status_code=400)
            transaction.transaction_category_id = transaction_category.transaction_category_id
            # Actualizar el tipo de transacción asociado a la categoría

        # Actualizar la descripción si se proporciona
        if request.description is not None:
            # if len(request.description) > 255:
            #     logger.warning("La descripción excede los 255 caracteres")
            #     return create_response("error", "La descripción no puede exceder los 255 caracteres", status_code=400)
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
        
        # Obtener la categoría de transacción actualizada y a través de ella el tipo
        txn_category = db.query(TransactionCategories).options(
            joinedload(TransactionCategories.transaction_type) # Cargar el tipo asociado
        ).filter(TransactionCategories.transaction_category_id == transaction.transaction_category_id).first()
        
        txn_category_name = "Desconocido"
        txn_type_name = "Desconocido"

        if txn_category:
            txn_category_name = txn_category.name
            if txn_category.transaction_type:
                txn_type_name = txn_category.transaction_type.name
        
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
        
        logger.info(f"Transacción con ID {transaction.transaction_id} actualizada exitosamente")
        
        return create_response("success", "Transacción actualizada correctamente", data=response_data)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar la transacción: {str(e)}")
        return create_response("error", f"Error al actualizar la transacción: {str(e)}", status_code=500)
