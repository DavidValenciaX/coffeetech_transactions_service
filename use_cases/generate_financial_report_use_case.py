from models.models import Transactions, TransactionCategories
from adapters.user_client import get_role_permissions_for_user_role, get_user_by_id
from adapters.farm_client import verify_plot, get_farm_by_id, get_user_role_farm
from utils.response import create_response
from utils.state import get_transaction_state
from fastapi.encoders import jsonable_encoder
from collections import defaultdict
from typing import Dict, List, Tuple
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

def _validate_and_get_plots(plot_ids: List[int]) -> Tuple[List, Dict[int, str], int]:
    """Validate plots and return plots, plot names, and farm_id."""
    plots = []
    plot_names = {}
    farm_ids = set()
    
    for plot_id in plot_ids:
        plot = verify_plot(plot_id)
        if not plot:
            logger.warning(f"El lote con ID {plot_id} no existe o no está activo")
            continue
        plots.append(plot)
        plot_names[plot.plot_id] = plot.name
        farm_ids.add(plot.farm_id)
    
    if not plots:
        raise ValueError("No se encontraron lotes activos con los IDs proporcionados")
    
    if len(farm_ids) != 1:
        raise ValueError("Los lotes seleccionados pertenecen a diferentes fincas")
    
    return plots, plot_names, farm_ids.pop()

def _validate_user_permissions(user, farm_id: int):
    """Validate user has permissions for the farm."""
    user_role_farm = get_user_role_farm(user.user_id, farm_id)
    if not user_role_farm:
        raise PermissionError(f"El usuario {user.user_id} no está asociado con la finca {farm_id}")
    
    permissions = get_role_permissions_for_user_role(user_role_farm.user_role_id)
    if "read_financial_report" not in permissions:
        raise PermissionError("No tienes permiso para ver reportes financieros")

def _get_transactions_and_categories(db: Session, request: FinancialReportRequest) -> Tuple[List, Dict]:
    """Get transactions and their categories map."""
    active_transaction_state = get_transaction_state(db, "Activo")
    if not active_transaction_state:
        raise ValueError("Estado 'Activo' para Transactions no encontrado")
    
    transactions = db.query(Transactions).filter(
        Transactions.plot_id.in_(request.plot_ids),
        Transactions.transaction_date >= request.fechaInicio,
        Transactions.transaction_date <= request.fechaFin,
        Transactions.transaction_state_id == active_transaction_state.transaction_state_id
    ).all()
    
    categories_map = {}
    if transactions:
        category_ids = list(set([t.transaction_category_id for t in transactions]))
        categories_with_types_query = db.query(TransactionCategories).options(
            joinedload(TransactionCategories.transaction_type)
        ).filter(TransactionCategories.transaction_category_id.in_(category_ids)).all()
        categories_map = {cat.transaction_category_id: cat for cat in categories_with_types_query}
    
    return transactions, categories_map

def _process_transaction(txn, categories_map: Dict, plot_financials: Dict, farm_totals: Dict):
    """Process a single transaction and update financial data."""
    plot_id = txn.plot_id
    if plot_id not in plot_financials:
        logger.warning(f"Transacción asociada a un lote no incluido en el reporte: {plot_id}")
        return
        
    txn_category_obj = categories_map.get(txn.transaction_category_id)
    if not txn_category_obj or not txn_category_obj.transaction_type:
        logger.warning(f"Transacción con ID {txn.transaction_id} tiene categoría o tipo de transacción inválidos")
        return
    
    txn_type_obj = txn_category_obj.transaction_type
    category_name = txn_category_obj.name
    monto = float(txn.value)
    
    if txn_type_obj.name.lower() in ["ingreso", "income", "revenue"]:
        plot_financials[plot_id]["ingresos"] += monto
        plot_financials[plot_id]["ingresos_por_categoria"][category_name] += monto
        farm_totals["ingresos"] += monto
        farm_totals["ingresos_categorias"][category_name] += monto
    elif txn_type_obj.name.lower() in ["gasto", "expense", "cost"]:
        plot_financials[plot_id]["gastos"] += monto
        plot_financials[plot_id]["gastos_por_categoria"][category_name] += monto
        farm_totals["gastos"] += monto
        farm_totals["gastos_categorias"][category_name] += monto
    else:
        logger.warning(f"Transacción con ID {txn.transaction_id} tiene un tipo desconocido '{txn_type_obj.name}'")

def _build_plot_financials_list(plot_financials: Dict) -> List[PlotFinancialData]:
    """Convert plot financials dict to list of PlotFinancialData objects."""
    plot_financials_list = []
    for plot_id, data in plot_financials.items():
        data["balance"] = data["ingresos"] - data["gastos"]
        data["ingresos_por_categoria"] = [
            FinancialCategoryBreakdown(category_name=k, monto=v) 
            for k, v in data["ingresos_por_categoria"].items()
        ]
        data["gastos_por_categoria"] = [
            FinancialCategoryBreakdown(category_name=k, monto=v) 
            for k, v in data["gastos_por_categoria"].items()
        ]
        plot_financials_list.append(PlotFinancialData(**data))
    return plot_financials_list

def _build_transaction_history(transactions: List, categories_map: Dict, plot_names: Dict, farm_name: str) -> List[TransactionHistoryItem]:
    """Build transaction history list."""
    transaction_history = []
    creator_cache: Dict[int, any] = {}
    
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
                farm_name=farm_name,
                transaction_type=txn_type_obj.name,
                transaction_category=txn_category_obj.name,
                creator_name=creator_name,
                value=float(txn.value)
            )
            transaction_history.append(history_item)
        except Exception as e:
            logger.warning(f"Error al procesar la transacción ID {txn.transaction_id}: {str(e)}")
            continue
    
    return transaction_history

def generate_financial_report(request: FinancialReportRequest, user, db: Session = Depends(get_db_session)):
    """
    Generar un reporte financiero para los lotes seleccionados en una finca.
    - **plot_ids**: Lista de IDs de lotes para los cuales se desea generar el reporte
    - **fechaInicio**: Fecha de inicio del periodo del reporte
    - **fechaFin**: Fecha de fin del periodo del reporte
    - **include_transaction_history**: Indica si se debe incluir el historial de transacciones
    """
    
    try:
        # Validate plots and get basic info
        plots, plot_names, farm_id = _validate_and_get_plots(request.plot_ids)
        
        # Get farm info
        farm = get_farm_by_id(farm_id)
        if not farm:
            return create_response("error", "La finca asociada a los lotes no existe o no está disponible", status_code=404)
        
        # Validate user permissions
        _validate_user_permissions(user, farm_id)
        
        # Get transactions and categories
        transactions, categories_map = _get_transactions_and_categories(db, request)
        
        # Initialize data structures
        plot_financials = {}
        farm_totals = {
            "ingresos": 0.0,
            "gastos": 0.0,
            "ingresos_categorias": defaultdict(float),
            "gastos_categorias": defaultdict(float)
        }
        
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
        
        # Process transactions
        for txn in transactions:
            _process_transaction(txn, categories_map, plot_financials, farm_totals)
        
        # Build response data
        plot_financials_list = _build_plot_financials_list(plot_financials)
        
        farm_balance = farm_totals["ingresos"] - farm_totals["gastos"]
        farm_summary = FarmFinancialSummary(
            total_ingresos=farm_totals["ingresos"],
            total_gastos=farm_totals["gastos"],
            balance_financiero=farm_balance,
            ingresos_por_categoria=[
                FinancialCategoryBreakdown(category_name=k, monto=v) 
                for k, v in farm_totals["ingresos_categorias"].items()
            ],
            gastos_por_categoria=[
                FinancialCategoryBreakdown(category_name=k, monto=v) 
                for k, v in farm_totals["gastos_categorias"].items()
            ]
        )
        
        report_response = FinancialReportResponse(
            finca_nombre=farm.name,
            lotes_incluidos=[plot_names[plot.plot_id] for plot in plots],
            periodo=f"{request.fechaInicio.isoformat()} a {request.fechaFin.isoformat()}",
            plot_financials=plot_financials_list,
            farm_summary=farm_summary,
            analysis=None
        )
        
        # Add transaction history if requested
        if request.include_transaction_history:
            report_response.transaction_history = _build_transaction_history(
                transactions, categories_map, plot_names, farm.name
            )

        logger.info(f"Reporte financiero generado para el usuario {user.user_id} en la finca '{farm.name}'")
        return create_response("success", "Reporte financiero generado correctamente", data=jsonable_encoder(report_response))
        
    except ValueError as e:
        return create_response("error", str(e), status_code=404 if "no encontrado" in str(e) else 400)
    except PermissionError as e:
        return create_response("error", str(e), status_code=403)
    except Exception as e:
        logger.error(f"Error inesperado al generar reporte financiero: {str(e)}")
        return create_response("error", "Error interno del servidor", status_code=500)
