from fastapi import Depends
from models.models import (
    TransactionCategories, Transactions, TransactionTypes
)
from adapters.user_client import get_role_permissions_for_user_role, verify_session_token
from utils.response import session_token_invalid_response, create_response
from utils.state import get_transaction_state
from fastapi.encoders import jsonable_encoder
from domain.schemas import CreateTransactionRequest, TransactionResponse
import logging
from adapters.farm_client import get_user_role_farm, get_user_role_farm_state_by_name, verify_plot
from sqlalchemy.orm import Session
from dataBase import get_db_session

logger = logging.getLogger(__name__)

def create_transaction_use_case(request: CreateTransactionRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Crear una nueva transacción para un lote en una finca.
    - **plot_id**: ID del lote asociado a la transacción
    - **transaction_category_id**: ID de la categoría de la transacción
    - **value**: Valor monetario de la transacción
    - **description**: Descripción detallada de la transacción
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
    
    # 3. Verificar que el usuario tenga permiso 'add_transaction'
    active_urf_state = get_user_role_farm_state_by_name("Activo")
    if not active_urf_state or not active_urf_state.get("user_role_farm_state_id"):
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    # Verificar que el lote existe y obtener su farm_id
    plot = verify_plot(request.plot_id)
    if not plot:
        logger.warning(f"El lote con ID {request.plot_id} no existe o no está activo")
        return create_response("error", "El lote especificado no existe o no está activo", status_code=404)
    farm_id = plot.farm_id
    
    # Verificar permisos de usuario en la finca
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca ID {farm_id}")
        return create_response("error", "No tienes permisos para agregar transacciones", status_code=403)
    
    # Verificar permiso 'add_transaction' usando el servicio de usuarios
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if "add_transaction" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para agregar transacciones")
        return create_response("error", "No tienes permiso para agregar transacciones", status_code=403)
    
    # 6. Verificar que la categoría de transacción existe y obtener el tipo de transacción
    transaction_category = db.query(TransactionCategories).filter(
        TransactionCategories.transaction_category_id == request.transaction_category_id
    ).first()
    if not transaction_category:
        logger.warning(f"La categoría de transacción con ID '{request.transaction_category_id}' no existe")
        return create_response("error", "La categoría de transacción especificada no existe", status_code=400)

    # Obtener el tipo de transacción a partir de la categoría
    transaction_type = db.query(TransactionTypes).filter(
        TransactionTypes.transaction_type_id == transaction_category.transaction_type_id
    ).first()
    if not transaction_type:
        logger.warning(f"El tipo de transacción asociado a la categoría ID '{request.transaction_category_id}' no existe")
        return create_response("error", "El tipo de transacción asociado a la categoría no existe", status_code=400)

    # 7. Verificar que el valor sea positivo
    if request.value <= 0:
        logger.warning("El valor de la transacción debe ser positivo")
        return create_response("error", "El valor de la transacción debe ser positivo", status_code=400)
    
    # 8. Obtener el estado 'Activo' para Transactions
    active_transaction_state = get_transaction_state(db, "Activo")
    if not active_transaction_state:
        logger.error("Estado 'Activo' para Transactions no encontrado")
        return create_response("error", "Estado 'Activo' para Transactions no encontrado", status_code=500)
    
    # 9. Crear la transacción
    try:
        new_transaction = Transactions(
            plot_id=request.plot_id,
            transaction_category_id=transaction_category.transaction_category_id,
            description=request.description,
            value=request.value,
            transaction_date=request.transaction_date,
            transaction_state_id=active_transaction_state.transaction_state_id,
            creator_id=user.user_id
        )
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        
        logger.info(f"Transacción creada exitosamente con ID: {new_transaction.transaction_id}")
        
        response_data = TransactionResponse(
            transaction_id=new_transaction.transaction_id,
            plot_id=new_transaction.plot_id,
            transaction_type_name=transaction_type.name,
            transaction_category_name=transaction_category.name,
            description=new_transaction.description,
            value=float(new_transaction.value),
            transaction_date=new_transaction.transaction_date,
            transaction_state=active_transaction_state.name
        )
        
        response_dict = jsonable_encoder(response_data)
        
        return create_response("success", "Transacción creada correctamente", data=response_dict)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear la transacción: {str(e)}")
        return create_response("error", f"Error al crear la transacción: {str(e)}", status_code=500)
