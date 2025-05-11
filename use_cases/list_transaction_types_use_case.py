from sqlalchemy.orm import Session
from models.models import TransactionTypes
from utils.response import create_response
from domain.schemas import TransactionTypeResponse

def list_transaction_types_use_case(db: Session):
    """
    Lista todos los tipos de transacción.
    """
    types = db.query(TransactionTypes).all()
    result = [
        TransactionTypeResponse(
            transaction_type_id=tt.transaction_type_id,
            name=tt.name
        )
        for tt in types
    ]
    return create_response("success", "Tipos de transacción obtenidos correctamente", data={"transaction_types": result})
