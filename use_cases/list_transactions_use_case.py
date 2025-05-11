from fastapi import Depends
from requests import Session
from dataBase import get_db_session
from utils.response import create_response, session_token_invalid_response
from utils.state import get_transaction_state
from models.models import (
    Transactions, TransactionCategories
)
from adapters.user_client import verify_session_token, get_role_permissions_for_user_role
from adapters.farm_client import verify_plot, get_user_role_farm
from sqlalchemy.orm import joinedload, Session
from domain.schemas import TransactionResponse
from fastapi.encoders import jsonable_encoder
import logging

logger = logging.getLogger(__name__)

def list_transactions_use_case(plot_id, session_token: str, db: Session = Depends(get_db_session)):
    """
    Listar las transacciones de un lote específico en una finca.
    - **plot_id**: ID del lote para el cual se desean listar las transacciones
    - **session_token**: Token de sesión del usuario
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
    
    # 3. Verificar que el lote exista y esté activo usando el cliente de farms
    plot_info = verify_plot(plot_id)
    if not plot_info:
        logger.warning(f"El lote con ID {plot_id} no existe o no está activo")
        return create_response("error", "El lote no existe o no está activo", status_code=404)
    
    # 4. Obtener el farm_id del lote
    farm_id = plot_info.farm_id
    
    # 5. Verificar que el usuario esté asociado con la finca del lote usando el cliente de farms
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario no está asociado con la finca con ID {farm_id}")
        return create_response("error", "No tienes permiso para ver las transacciones en esta finca", status_code=403)
    
    # 6. Verificar permiso 'read_transaction' usando el cliente de usuarios
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if "read_transaction" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para leer transacciones")
        return create_response("error", "No tienes permiso para ver las transacciones en esta finca", status_code=403)
    
    # 7. Obtener el estado "Inactivo" para Transactions
    inactive_transaction_state = get_transaction_state(db, "Inactivo")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    # 8. Consultar las transacciones del lote que no están inactivas
    transactions = db.query(Transactions).options(
        joinedload(Transactions.transaction_category).joinedload(TransactionCategories.transaction_type),
        joinedload(Transactions.state)
    ).filter(
        Transactions.plot_id == plot_id,
        Transactions.transaction_state_id != inactive_transaction_state.transaction_state_id
    ).all()
    
    # 9. Preparar la lista de transacciones
    transaction_list = []
    for txn in transactions:
        txn_type_name = "Desconocido"
        txn_category_name = "Desconocido"
        
        if txn.transaction_category:
            txn_category_name = txn.transaction_category.name
            if txn.transaction_category.transaction_type:
                txn_type_name = txn.transaction_category.transaction_type.name
        
        transaction_state_name = txn.state.name if txn.state else "Desconocido"
        
        response_data = TransactionResponse(
            transaction_id=txn.transaction_id,
            plot_id=txn.plot_id,
            transaction_type_name=txn_type_name,
            transaction_category_name=txn_category_name,
            description=txn.description,
            value=float(txn.value),
            transaction_date=txn.transaction_date,
            transaction_state=transaction_state_name
        )
        transaction_list.append(jsonable_encoder(response_data))
    
    if not transaction_list:
        return create_response("success", "El lote no tiene transacciones registradas", {"transactions": []})
    
    return create_response("success", "Transacciones obtenidas exitosamente", {"transactions": transaction_list})
