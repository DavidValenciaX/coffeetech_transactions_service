from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dataBase import get_db_session
import pytz
import logging
from domain.schemas import (
    CreateTransactionRequest,
    TransactionCategoryResponse,
    TransactionTypeResponse,
    UpdateTransactionRequest,
    DeleteTransactionRequest,
    TransactionResponse
)
from use_cases.create_transaction_use_case import create_transaction_use_case
from use_cases.edit_transaction_use_case import edit_transaction_use_case
from use_cases.list_transactions_use_case import list_transactions_use_case
from use_cases.delete_transaction_use_case import delete_transaction_use_case
from domain.services.list_transaction_types_service import list_transaction_types_use_case
from domain.services.list_transaction_categories_service import list_transaction_categories_use_case

router = APIRouter()

logger = logging.getLogger(__name__)

bogota_tz = pytz.timezone("America/Bogota")

# Endpoint to Create a Transactions
@router.post("/create-transaction", response_model=TransactionResponse)
def create_transaction(
    request: CreateTransactionRequest,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Crear una nueva transacción para un lote en una finca.

    - **plot_id**: ID del lote asociado a la transacción
    - **transaction_category_id**: ID de la categoría de la transacción
    - **value**: Valor monetario de la transacción
    - **description**: Descripción detallada de la transacción
    """
    return create_transaction_use_case(request, session_token, db)

# Endpoint to Edit a Transactions
@router.post("/edit-transaction", response_model=TransactionResponse)
def edit_transaction(
    request: UpdateTransactionRequest,
    session_token: str ,
    db: Session = Depends(get_db_session)
):
    """
    Editar una transacción existente para un lote en una finca.

    - **transaction_id**: ID de la transacción
    - **transaction_category_id**: Nuevo ID de la categoría de la transacción
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
@router.get("/list-transactions/{plot_id}", response_model=list[TransactionResponse])
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

@router.get("/transaction-types", response_model = TransactionTypeResponse)
def get_transaction_types(db: Session = Depends(get_db_session)):
    """
    Lista todos los tipos de transacción disponibles.
    """
    return list_transaction_types_use_case(db)

@router.get("/transaction-categories", response_model = TransactionCategoryResponse)
def get_transaction_categories(db: Session = Depends(get_db_session)):
    """
    Lista todas las categorías de transacción disponibles.
    """
    return list_transaction_categories_use_case(db)
