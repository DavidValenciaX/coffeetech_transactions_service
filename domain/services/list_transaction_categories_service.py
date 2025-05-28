from sqlalchemy.orm import Session, joinedload
from models.models import TransactionCategories
from utils.response import create_response
from domain.schemas import TransactionCategoryResponse

def list_transaction_categories_use_case(db: Session):
    """
    Lista todas las categorías de transacción, incluyendo el nombre del tipo asociado.
    """
    categories = db.query(TransactionCategories).options(
        joinedload(TransactionCategories.transaction_type)
    ).all()
    result = [
        TransactionCategoryResponse(
            transaction_category_id=cat.transaction_category_id,
            name=cat.name,
            transaction_type_id=cat.transaction_type_id,
            transaction_type_name=cat.transaction_type.name if cat.transaction_type else "Desconocido"
        )
        for cat in categories
    ]
    return create_response("success", "Categorías de transacción obtenidas correctamente", data={"transaction_categories": result})
