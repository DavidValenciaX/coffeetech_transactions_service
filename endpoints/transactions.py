from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models.models import (
    TransactionCategories, Transactions, TransactionTypes, TransactionStates
)
from utils.security import verify_session_token
from dataBase import get_db_session
from typing import Optional
from utils.response import session_token_invalid_response, create_response
from utils.state import get_state
from datetime import date
from fastapi.encoders import jsonable_encoder
import pytz
import logging
from use_cases.create_transaction_use_case import create_transaction_use_case
from use_cases.edit_transaction_use_case import edit_transaction_use_case

router = APIRouter()

logger = logging.getLogger(__name__)

bogota_tz = pytz.timezone("America/Bogota")

# Pydantic Models for Transactions Endpoints

class CreateTransactionRequest(BaseModel):
    entity_type: str = Field(..., description="Tipo de entidad asociada a la transacción (ej. 'plot', 'farm')")
    entity_id: int = Field(..., description="ID de la entidad asociada a la transacción")
    transaction_type_name: str = Field(..., description="Nombre del tipo de transacción")
    transaction_category_name: str = Field(..., description="Nombre de la categoría de la transacción")
    description: Optional[str] = Field(None, max_length=255, description="Descripción de la transacción (máximo 255 caracteres)")
    value: float = Field(..., description="Valor de la transacción")
    transaction_date: date = Field(..., description="Fecha de la transacción")

class UpdateTransactionRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción a actualizar")
    transaction_type_name: Optional[str] = Field(None, description="Nuevo nombre del tipo de transacción")
    transaction_category_name: Optional[str] = Field(None, description="Nuevo nombre de la categoría de la transacción")
    description: Optional[str] = Field(None, max_length=255, description="Nueva descripción de la transacción (máximo 255 caracteres)")
    value: Optional[float] = Field(None, description="Nuevo valor de la transacción")
    transaction_date: Optional[date] = Field(None, description="Nueva fecha de la transacción")

class DeleteTransactionRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción a eliminar")

class TransactionResponse(BaseModel):
    transaction_id: int
    entity_type: str
    entity_id: int
    transaction_type_name: str
    transaction_category_name: str
    description: Optional[str]
    value: float
    transaction_date: date
    transaction_state: str

# Endpoint to Create a Transactions
@router.post("/create-transaction")
def create_transaction(
    request: CreateTransactionRequest,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Crear una nueva transacción para un lote en una finca.

    - **farm_id**: ID de la finca
    - **plot_id**: ID del lote
    - **transaction_type**: Tipo de transacción (Ej. 'ingreso', 'gasto')
    - **category**: Categoría de la transacción (Ej. 'fertilizante', 'mano de obra')
    - **value**: Valor monetario de la transacción
    - **description**: Descripción detallada de la transacción
    """
    return create_transaction_use_case(request, session_token, db)

# Endpoint to Edit a Transactions
@router.post("/edit-transaction")
def edit_transaction(
    request: UpdateTransactionRequest,
    session_token: str ,
    db: Session = Depends(get_db_session)
):
    """
    Editar una transacción existente para un lote en una finca.

    - **transaction_id**: ID de la transacción
    - **transaction_type**: Nuevo tipo de transacción
    - **category**: Nueva categoría de la transacción
    - **value**: Nuevo valor monetario de la transacción
    - **description**: Nueva descripción de la transacción
    """
    return edit_transaction_use_case(request, session_token, db)

# Endpoint to Delete a Transactions
@router.post("/delete-transaction")
def delete_transaction(
    request: DeleteTransactionRequest,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Eliminar una transacción existente para un lote.

    - **transaction_id**: ID de la transacción a eliminar
    - **session_token**: Token de sesión del usuario para verificar permisos y autenticación
    """
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Obtener la transacción a eliminar
    transaction = db.query(Transactions).filter(Transactions.transaction_id == request.transaction_id).first()
    if not transaction:
        logger.warning(f"La transacción con ID {request.transaction_id} no existe")
        return create_response("error", "La transacción especificada no existe", status_code=404)
    
    # 4. Verificar que la transacción no esté ya inactiva
    inactive_transaction_state = get_state(db, "Inactivo", "Transactions")
    if not inactive_transaction_state:
        logger.error("Estado 'Inactivo' para Transactions no encontrado")
        return create_response("error", "Estado 'Inactivo' para Transactions no encontrado", status_code=500)
    
    if transaction.transaction_state_id == inactive_transaction_state.transaction_state_id:
        logger.warning(f"La transacción con ID {request.transaction_id} ya está inactiva")
        return create_response("error", "La transacción ya está eliminada", status_code=400)
    
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

# Endpoint to Read Transactions for a Plots
@router.get("/list-transactions/{plot_id}")
def read_transactions(
    plot_id: int,
    session_token: str ,
    db: Session = Depends(get_db_session)
):
    """
    Obtener la lista de transacciones de un lote específico.

    - **plot_id**: ID del lote del que se desea obtener las transacciones
    - **session_token**: Token de sesión del usuario para verificar permisos y autenticación
    """
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
