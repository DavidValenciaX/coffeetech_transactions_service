from fastapi import Depends
from models.models import (
    Transactions, TransactionCategories, TransactionStates
)
from utils.response import session_token_invalid_response, create_response
from utils.state import get_transaction_state
from domain.schemas import TransactionResponse, UpdateTransactionRequest
from adapters.user_client import verify_session_token, get_role_permissions_for_user_role
from adapters.farm_client import get_user_role_farm_state_by_name, get_user_role_farm, verify_plot
import logging
from sqlalchemy.orm import joinedload, Session
from dataBase import get_db_session

logger = logging.getLogger(__name__)

def _validate_session_token(session_token: str):
    """Validate session token and return user or error response."""
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return None, create_response("error", "Token de sesión faltante", status_code=401)
    
    user = verify_session_token(session_token)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return None, session_token_invalid_response()
    
    return user, None

def _validate_transaction_exists_and_active(db: Session, transaction_id: int):
    """Validate transaction exists and is not inactive."""
    transaction = db.query(Transactions).filter(Transactions.transaction_id == transaction_id).first()
    if not transaction:
        logger.warning(f"La transacción con ID {transaction_id} no existe")
        return None, create_response("error", "La transacción especificada no existe", status_code=404)
    
    inactive_state = get_transaction_state(db, "Inactivo")
    if not inactive_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return None, create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    if transaction.transaction_state_id == inactive_state.transaction_state_id:
        logger.warning(f"La transacción con ID {transaction_id} está inactiva y no puede ser modificada")
        return None, create_response("error", "La transacción está inactiva y no puede ser modificada", status_code=403)
    
    return transaction, None

def _validate_user_permissions(user, transaction):
    """Validate user has permissions to edit transaction."""
    active_urf_state = get_user_role_farm_state_by_name("Activo")
    if not active_urf_state or not active_urf_state.get("user_role_farm_state_id"):
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    plot_info = verify_plot(transaction.plot_id)
    if not plot_info:
        logger.warning(f"El lote con ID {transaction.plot_id} no existe o no está activo")
        return create_response("error", "El lote asociado a esta transacción no existe o no está activo", status_code=404)
    
    user_role_farm = get_user_role_farm(user.user_id, plot_info.farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {plot_info.farm_id}")
        return create_response("error", "No tienes permisos para editar transacciones en esta finca", status_code=403)
    
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if not permissions or "edit_transaction" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para editar transacciones")
        return create_response("error", "No tienes permiso para editar transacciones", status_code=403)
    
    return None

def _update_transaction_fields(db: Session, transaction, request: UpdateTransactionRequest):
    """Update transaction fields based on request."""
    if request.transaction_category_id is not None:
        transaction_category = db.query(TransactionCategories).filter(
            TransactionCategories.transaction_category_id == request.transaction_category_id
        ).first()
        if not transaction_category:
            logger.warning(f"La categoría de transacción con ID '{request.transaction_category_id}' no existe")
            return create_response("error", "La categoría de transacción especificada no existe", status_code=400)
        transaction.transaction_category_id = transaction_category.transaction_category_id

    if request.description is not None:
        transaction.description = request.description
    
    if request.value is not None:
        if request.value <= 0:
            logger.warning("El valor de la transacción debe ser positivo")
            return create_response("error", "El valor de la transacción debe ser positivo", status_code=400)
        transaction.value = request.value
    
    if request.transaction_date is not None:
        transaction.transaction_date = request.transaction_date
    
    return None

def _build_transaction_response(db: Session, transaction):
    """Build transaction response with related data."""
    transaction_current_state = db.query(TransactionStates).filter(
        TransactionStates.transaction_state_id == transaction.transaction_state_id
    ).first()
    transaction_state_name = transaction_current_state.name if transaction_current_state else "Desconocido"
    
    txn_category = db.query(TransactionCategories).options(
        joinedload(TransactionCategories.transaction_type)
    ).filter(TransactionCategories.transaction_category_id == transaction.transaction_category_id).first()
    
    txn_category_name = "Desconocido"
    txn_type_name = "Desconocido"

    if txn_category:
        txn_category_name = txn_category.name
        if txn_category.transaction_type:
            txn_type_name = txn_category.transaction_type.name
    
    return TransactionResponse(
        transaction_id=transaction.transaction_id,
        plot_id=transaction.plot_id,
        transaction_type_name=txn_type_name,
        transaction_category_name=txn_category_name,
        description=transaction.description,
        value=transaction.value,
        transaction_date=transaction.transaction_date,
        transaction_state=transaction_state_name
    )

def edit_transaction_use_case(request: UpdateTransactionRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Editar una transacción existente para un lote en una finca.
    - **transaction_id**: ID de la transacción a editar
    - **transaction_category_id**: Nuevo ID de la categoría de la transacción
    - **value**: Nuevo valor monetario de la transacción
    - **description**: Nueva descripción de la transacción
    """
    # Validate session token
    user, error_response = _validate_session_token(session_token)
    if error_response:
        return error_response
    
    # Validate transaction exists and is active
    transaction, error_response = _validate_transaction_exists_and_active(db, request.transaction_id)
    if error_response:
        return error_response
    
    # Validate user permissions
    error_response = _validate_user_permissions(user, transaction)
    if error_response:
        return error_response
    
    # Update transaction
    try:
        error_response = _update_transaction_fields(db, transaction, request)
        if error_response:
            return error_response
        
        db.commit()
        db.refresh(transaction)
        
        response_data = _build_transaction_response(db, transaction)
        
        logger.info(f"Transacción con ID {transaction.transaction_id} actualizada exitosamente")
        return create_response("success", "Transacción actualizada correctamente", data=response_data)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar la transacción: {str(e)}")
        return create_response("error", f"Error al actualizar la transacción: {str(e)}", status_code=500)
