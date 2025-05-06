from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dataBase import get_db_session
from typing import Optional
from datetime import date
from use_cases.create_transaction_use_case import create_transaction_use_case
from use_cases.edit_transaction_use_case import edit_transaction_use_case
from use_cases.list_transactions_use_case import list_transactions_use_case
from use_cases.delete_transaction_use_case import delete_transaction_use_case
import pytz
import logging

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
    return delete_transaction_use_case(request, session_token, db)

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
    return list_transactions_use_case(plot_id, session_token, db)
