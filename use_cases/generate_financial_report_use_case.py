from models.models import Transactions, TransactionCategories
from adapters.user_client import get_role_permissions_for_user_role, get_user_by_id
from adapters.farm_client import verify_plot, get_farm_by_id, get_user_role_farm
from utils.response import create_response
from utils.state import get_transaction_state
from fastapi.encoders import jsonable_encoder
from collections import defaultdict
from typing import Dict
from sqlalchemy.orm import Session, joinedload
from fastapi import Depends
from dataBase import get_db_session
import logging

from domain.schemas import (
    FinancialReportRequest,
    FinancialCategoryBreakdown,
    PlotFinancialData,
    FarmFinancialSummary,
    TransactionHistoryItem,
    FinancialReportResponse
)

logger = logging.getLogger(__name__)

def generate_financial_report(request: FinancialReportRequest, user, db: Session = Depends(get_db_session)):
    """
    Generar un reporte financiero para los lotes seleccionados en una finca.
    - **plot_ids**: Lista de IDs de lotes para los cuales se desea generar el reporte
    - **fechaInicio**: Fecha de inicio del periodo del reporte
    - **fechaFin**: Fecha de fin del periodo del reporte
    - **include_transaction_history**: Indica si se debe incluir el historial de transacciones
    """
    
    # 3. Obtener los lotes seleccionados usando el cliente de farms
    plots = []
    plot_names = {}
    farm_ids = set()
    
    for plot_id in request.plot_ids:
        plot = verify_plot(plot_id)
        if not plot:
            logger.warning(f"El lote con ID {plot_id} no existe o no está activo")
            continue
        plots.append(plot)
        plot_names[plot.plot_id] = plot.name
        farm_ids.add(plot.farm_id)
    
    if not plots:
        logger.warning("No se encontraron lotes activos con los IDs proporcionados")
        return create_response("error", "No se encontraron lotes activos con los IDs proporcionados", status_code=404)
    
    # Asegurarse de que todos los lotes pertenezcan a la misma finca
    if len(farm_ids) != 1:
        logger.warning("Los lotes seleccionados pertenecen a diferentes fincas")
        return create_response("error", "Los lotes seleccionados pertenecen a diferentes fincas", status_code=400)
    
    farm_id = farm_ids.pop()
    
    # Obtener información de la finca usando el cliente de farms
    farm = get_farm_by_id(farm_id)
    if not farm:
        logger.warning(f"La finca con ID {farm_id} no existe o no está disponible")
        return create_response("error", "La finca asociada a los lotes no existe o no está disponible", status_code=404)
    
    # 4. Verificar que el usuario esté asociado con esta finca y tenga permisos
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        logger.warning(f"El usuario {user.user_id} no está asociado con la finca {farm_id}")
        return create_response("error", "No tienes permisos para ver reportes financieros de esta finca", status_code=403)
    
    # Verificar permiso 'read_financial_report' usando el cliente de usuarios
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if "read_financial_report" not in permissions:
        logger.warning("El rol del usuario no tiene permiso para ver reportes financieros")
        return create_response("error", "No tienes permiso para ver reportes financieros", status_code=403)
    
    # 5. Obtener el estado 'Activo' para Transactions
    active_transaction_state = get_transaction_state(db, "Activo")
    if not active_transaction_state:
        logger.error("Estado 'Activo' para Transactions no encontrado")
        return create_response("error", "Estado 'Activo' para Transactions no encontrado", status_code=500)
    
    # 6. Consultar las transacciones de los lotes seleccionados dentro del rango de fechas
    transactions = db.query(Transactions).filter(
        Transactions.plot_id.in_(request.plot_ids),
        Transactions.transaction_date >= request.fechaInicio,
        Transactions.transaction_date <= request.fechaFin,
        Transactions.transaction_state_id == active_transaction_state.transaction_state_id
    ).all()
    
    # Precargar categorías de transacciones y sus tipos asociados para las transacciones filtradas
    # para evitar múltiples consultas N+1 dentro del bucle.
    if transactions:
        category_ids = list(set([t.transaction_category_id for t in transactions]))
        
        categories_with_types_query = db.query(TransactionCategories).options(
            joinedload(TransactionCategories.transaction_type)
        ).filter(TransactionCategories.transaction_category_id.in_(category_ids)).all()
        
        # Crear un mapa para fácil acceso: category_id -> TransactionCategory (con su transaction_type cargado)
        categories_map = {cat.transaction_category_id: cat for cat in categories_with_types_query}
    else:
        categories_map = {}
        
    # 7. Procesar las transacciones para agregaciones
    plot_financials = {}
    farm_ingresos = 0.0
    farm_gastos = 0.0
    farm_ingresos_categorias = defaultdict(float)
    farm_gastos_categorias = defaultdict(float)
    
    # Inicializar estructuras de datos para cada lote
    for plot in plots:
        plot_financials[plot.plot_id] = {
            "plot_id": plot.plot_id,
            "plot_name": plot_names[plot.plot_id],
            "ingresos": 0.0,
            "gastos": 0.0,
            "balance": 0.0,
            "ingresos_por_categoria": defaultdict(float),
            "gastos_por_categoria": defaultdict(float)
        }
    
    # Procesar cada transacción
    for txn in transactions:
        plot_id = txn.plot_id
        if plot_id not in plot_financials:
            logger.warning(f"Transacción asociada a un lote no incluido en el reporte: {plot_id}")
            continue
            
        txn_category_obj = categories_map.get(txn.transaction_category_id)
        
        if not txn_category_obj or not txn_category_obj.transaction_type:
            logger.warning(f"Transacción con ID {txn.transaction_id} tiene categoría o tipo de transacción inválidos o no encontrados.")
            continue
        
        txn_type_obj = txn_category_obj.transaction_type
        category_name = txn_category_obj.name
        monto = float(txn.value)
        
        if txn_type_obj.name.lower() in ["ingreso", "income", "revenue"]:
            plot_financials[plot_id]["ingresos"] += monto
            plot_financials[plot_id]["ingresos_por_categoria"][category_name] += monto
            farm_ingresos += monto
            farm_ingresos_categorias[category_name] += monto
        elif txn_type_obj.name.lower() in ["gasto", "expense", "cost"]:
            plot_financials[plot_id]["gastos"] += monto
            plot_financials[plot_id]["gastos_por_categoria"][category_name] += monto
            farm_gastos += monto
            farm_gastos_categorias[category_name] += monto
        else:
            logger.warning(f"Transacción con ID {txn.transaction_id} tiene un tipo desconocido '{txn_type_obj.name}'")
    
    # Calcular balances por lote
    plot_financials_list = []
    for plot_id, data in plot_financials.items():
        data["balance"] = data["ingresos"] - data["gastos"]
        # Convertir defaultdict a list de FinancialCategoryBreakdown
        data["ingresos_por_categoria"] = [
            FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in data["ingresos_por_categoria"].items()
        ]
        data["gastos_por_categoria"] = [
            FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in data["gastos_por_categoria"].items()
        ]
        plot_financials_list.append(PlotFinancialData(**data))
    
    # Resumen financiero de la finca
    farm_balance = farm_ingresos - farm_gastos
    farm_summary = FarmFinancialSummary(
        total_ingresos=farm_ingresos,
        total_gastos=farm_gastos,
        balance_financiero=farm_balance,
        ingresos_por_categoria=[
            FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in farm_ingresos_categorias.items()
        ],
        gastos_por_categoria=[
            FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in farm_gastos_categorias.items()
        ]
    )
    
    # Preparar la respuesta
    report_response = FinancialReportResponse(
        finca_nombre=farm.name,
        lotes_incluidos=[plot_names[plot.plot_id] for plot in plots],
        periodo=f"{request.fechaInicio.isoformat()} a {request.fechaFin.isoformat()}",
        plot_financials=plot_financials_list,
        farm_summary=farm_summary,
        analysis=None
    )
    
    # Agregar historial de transacciones si se solicita
    if request.include_transaction_history:
        transaction_history = []
        
        # Crear un caché para evitar múltiples llamadas al servicio de usuarios
        creator_cache: Dict[int, any] = {}
        
        # Función auxiliar para obtener datos del creador
        def get_creator_info(creator_id: int) -> str:
            if creator_id not in creator_cache:
                user_obj = get_user_by_id(creator_id)
                if user_obj:
                    creator_cache[creator_id] = user_obj
                    return user_obj.name
                else:
                    return f"Usuario #{creator_id}"
            return creator_cache[creator_id].name
        
        for txn in transactions:
            try:
                plot_id = txn.plot_id
                plot_name = plot_names.get(plot_id, f"Lote #{plot_id}")
                
                txn_category_obj = categories_map.get(txn.transaction_category_id)
                
                if not txn_category_obj or not txn_category_obj.transaction_type:
                    logger.warning(f"Historial: Transacción ID {txn.transaction_id} con categoría/tipo inválido.")
                    continue
                
                txn_type_obj = txn_category_obj.transaction_type
                creator_name = get_creator_info(txn.creator_id)

                history_item = TransactionHistoryItem(
                    date=txn.transaction_date,
                    plot_name=plot_name,
                    farm_name=farm.name,
                    transaction_type=txn_type_obj.name,
                    transaction_category=txn_category_obj.name,
                    creator_name=creator_name,
                    value=float(txn.value)
                )
                transaction_history.append(history_item)
            except Exception as e:
                logger.warning(f"Error al procesar la transacción ID {txn.transaction_id}: {str(e)}")
                continue  # Omitir transacciones con errores
        
        report_response.transaction_history = transaction_history

    logger.info(f"Reporte financiero generado para el usuario {user.user_id} en la finca '{farm.name}'")
    
    return create_response("success", "Reporte financiero generado correctamente", data=jsonable_encoder(report_response))
