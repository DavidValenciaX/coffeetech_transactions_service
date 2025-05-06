from models.models import (
    TransactionCategories, Transactions, TransactionTypes, TransactionStates
)
from utils.response import session_token_invalid_response, create_response
from utils.state import get_state
from fastapi.encoders import jsonable_encoder
from endpoints.transactions import TransactionResponse
import logging

logger = logging.getLogger(__name__)

def create_transaction_use_case(request, session_token, db):
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # 3. Verificar que el usuario tenga permiso 'add_transaction'
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("Estado 'Activo' para user_role_farm no encontrado")
        return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=400)
    
    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
    ).first()
    
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con ninguna finca activa")
        return create_response("error", "No tienes permisos para agregar transacciones", status_code=403)
    
    # Verificar permiso 'add_transaction'
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "add_transaction"
    ).first()
    
    if not role_permission:
        logger.warning(f"El rol {user_role_farm.role_id} del usuario no tiene permiso para agregar transacciones")
        return create_response("error", "No tienes permiso para agregar transacciones", status_code=403)
    
    # 4. Verificar que el lote existe y está activo
    active_plot_state = get_state(db, "Activo", "Plots")
    if not active_plot_state:
        logger.error("Estado 'Activo' para Plots no encontrado")
        return create_response("error", "Estado 'Activo' para Plots no encontrado", status_code=500)
    
    plot = db.query(Plots).filter(
        Plots.plot_id == request.plot_id,
        Plots.plot_state_id == active_plot_state.plot_state_id
    ).first()
    
    if not plot:
        logger.warning(f"El lote con ID {request.plot_id} no existe o no está activo")
        return create_response("error", "El lote especificado no existe o no está activo", status_code=404)
    
    # 6. Verificar que el tipo de transacción existe
    transaction_type = db.query(TransactionTypes).filter(TransactionTypes.name == request.transaction_type_name).first()
    if not transaction_type:
        logger.warning(f"El tipo de transacción '{request.transaction_type_name}' no existe")
        return create_response("error", "El tipo de transacción especificado no existe", status_code=400)
    
    # 7. Verificar que el valor sea positivo
    if request.value <= 0:
        logger.warning("El valor de la transacción debe ser positivo")
        return create_response("error", "El valor de la transacción debe ser positivo", status_code=400)
    
    # 8. Verificar que la categoría de transacción existe para el tipo de transacción
    transaction_category = db.query(TransactionCategories).filter(
        TransactionCategories.name == request.transaction_category_name,
        TransactionCategories.transaction_type_id == transaction_type.transaction_type_id
    ).first()
    if not transaction_category:
        logger.warning(f"La categoría de transacción '{request.transaction_category_name}' no existe para el tipo '{request.transaction_type_name}'")
        return create_response("error", "La categoría de transacción especificada no existe para el tipo de transacción proporcionado", status_code=400)
    
    # 9. Obtener el estado 'Activo' para Transactions
    active_transaction_state = get_state(db, "Activo", "Transactions")
    if not active_transaction_state:
        logger.error("Estado 'Activo' para Transactions no encontrado")
        return create_response("error", "Estado 'Activo' para Transactions no encontrado", status_code=500)
    
    # 10. Crear la transacción
    try:
        new_transaction = Transactions(
            plot_id=request.plot_id,
            transaction_type_id=transaction_type.transaction_type_id,
            transaction_category_id=transaction_category.transaction_category_id,
            description=request.description,
            value=request.value,
            transaction_date=request.transaction_date,
            transaction_state_id=active_transaction_state.transaction_state_id,
            creador_id=user.user_id
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
            value=new_transaction.value,
            transaction_date=new_transaction.transaction_date,
            transaction_state=active_transaction_state.name
        )
        
        response_dict = jsonable_encoder(response_data.dict())
        
        return create_response("success", "Transacción creada correctamente", data=response_dict)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear la transacción: {str(e)}")
        return create_response("error", f"Error al crear la transacción: {str(e)}", status_code=500)
