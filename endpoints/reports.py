from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.models import Transactions, TransactionTypes, TransactionCategories, TransactionStates
from adapters.user_client import verify_session_token, get_role_permissions_for_user_role, user_verification_by_email, UserResponse, get_user_by_id
from adapters.farm_client import verify_plot, get_farm_by_id, get_user_role_farm, get_user_role_farm_state_by_name
from dataBase import get_db_session
from typing import List, Optional, Dict
from utils.response import create_response, session_token_invalid_response
from utils.state import get_transaction_state
from pydantic import BaseModel, Field, conlist
from datetime import date
from fastapi.encoders import jsonable_encoder
from collections import defaultdict
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

# Modelos de Pydantic

class FinancialReportRequest(BaseModel):
    plot_ids: conlist(int) = Field(..., description="Lista de IDs de lotes (puede ser un solo ID)")
    fechaInicio: date = Field(..., description="Fecha de inicio del periodo")
    fechaFin: date = Field(..., description="Fecha de fin del periodo")
    include_transaction_history: bool = Field(False, description="Indica si se debe incluir el historial de transacciones")


class FinancialCategoryBreakdown(BaseModel):
    category_name: str
    monto: float

class PlotFinancialData(BaseModel):
    plot_id: int
    plot_name: str
    ingresos: float
    gastos: float
    balance: float
    ingresos_por_categoria: List[FinancialCategoryBreakdown]
    gastos_por_categoria: List[FinancialCategoryBreakdown]

class FarmFinancialSummary(BaseModel):
    total_ingresos: float
    total_gastos: float
    balance_financiero: float
    ingresos_por_categoria: List[FinancialCategoryBreakdown]
    gastos_por_categoria: List[FinancialCategoryBreakdown]


class TransactionHistoryItem(BaseModel):
    date: date
    plot_name: str
    farm_name: str
    transaction_type: str
    transaction_category: str
    creator_name: str
    value: float
    
class FinancialReportResponse(BaseModel):
    finca_nombre: str
    lotes_incluidos: List[str]
    periodo: str
    plot_financials: List[PlotFinancialData]
    farm_summary: FarmFinancialSummary
    analysis: Optional[str] = None
    transaction_history: Optional[List[TransactionHistoryItem]] = None

# Endpoint para generar el reporte financiero
@router.post("/financial-report")
def financial_report(
    request: FinancialReportRequest,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Genera un reporte financiero detallado de los lotes seleccionados en una finca específica.

    - **request**: Contiene los IDs de los lotes, el rango de fechas y si se debe incluir el historial de transacciones.
    - **session_token**: Token de sesión del usuario para validar su autenticación.
    - **db**: Sesión de base de datos proporcionada automáticamente por FastAPI.

    El reporte incluye ingresos, gastos y balance financiero de los lotes y la finca en general.
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
    
    try:
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
            logger.warning(f"El rol del usuario no tiene permiso para ver reportes financieros")
            return create_response("error", "No tienes permiso para ver reportes financieros", status_code=403)
        
        # 5. Obtener el estado 'Activo' para Transactions
        active_transaction_state = get_transaction_state(db, "Activo")
        if not active_transaction_state:
            logger.error("Estado 'Activo' para Transactions no encontrado")
            return create_response("error", "Estado 'Activo' para Transactions no encontrado", status_code=500)
        
        # 6. Consultar las transacciones de los lotes seleccionados dentro del rango de fechas
        transactions = db.query(Transactions).filter(
            Transactions.entity_type == "plot",
            Transactions.entity_id.in_(request.plot_ids),
            Transactions.transaction_date >= request.fechaInicio,
            Transactions.transaction_date <= request.fechaFin,
            Transactions.transaction_state_id == active_transaction_state.transaction_state_id
        ).all()
        
        # Precargar tipos y categorías de transacciones para evitar múltiples consultas
        transaction_ids = [txn.transaction_id for txn in transactions]
        transaction_types = {}
        transaction_categories = {}
        
        # Cargar los tipos de transacción
        type_results = db.query(TransactionTypes).join(
            Transactions, Transactions.transaction_type_id == TransactionTypes.transaction_type_id
        ).filter(Transactions.transaction_id.in_(transaction_ids)).all()
        
        for t_type in type_results:
            transaction_types[t_type.transaction_type_id] = t_type
            
        # Cargar las categorías de transacción
        category_results = db.query(TransactionCategories).join(
            Transactions, Transactions.transaction_category_id == TransactionCategories.transaction_category_id
        ).filter(Transactions.transaction_id.in_(transaction_ids)).all()
        
        for category in category_results:
            transaction_categories[category.transaction_category_id] = category
        
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
            plot_id = txn.entity_id
            if plot_id not in plot_financials:
                logger.warning(f"Transacción asociada a un lote no incluido en el reporte: {plot_id}")
                continue
                
            txn_type = transaction_types.get(txn.transaction_type_id)
            txn_category = transaction_categories.get(txn.transaction_category_id)
            
            if not txn_type or not txn_category:
                logger.warning(f"Transacción con ID {txn.transaction_id} tiene tipo o categoría inválidos")
                continue  # Omitir transacciones incompletas
            
            category = txn_category.name
            monto = float(txn.value)
            
            if txn_type.name.lower() in ["ingreso", "income", "revenue"]:
                plot_financials[plot_id]["ingresos"] += monto
                plot_financials[plot_id]["ingresos_por_categoria"][category] += monto
                farm_ingresos += monto
                farm_ingresos_categorias[category] += monto
            elif txn_type.name.lower() in ["gasto", "expense", "cost"]:
                plot_financials[plot_id]["gastos"] += monto
                plot_financials[plot_id]["gastos_por_categoria"][category] += monto
                farm_gastos += monto
                farm_gastos_categorias[category] += monto
            else:
                logger.warning(f"Transacción con ID {txn.transaction_id} tiene un tipo desconocido '{txn_type.name}'")
        
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
            creator_cache: Dict[int, UserResponse] = {}
            
            # Función auxiliar para obtener datos del creador
            def get_creator_info(creator_id: int) -> str:
                if creator_id not in creator_cache:
                    # Utilizar el nuevo método para obtener usuario por ID
                    user = get_user_by_id(creator_id)
                    if user:
                        creator_cache[creator_id] = user
                        return user.name
                    else:
                        # Si no se puede obtener el usuario, mostrar ID como fallback
                        return f"Usuario #{creator_id}"
                
                return creator_cache[creator_id].name
            
            for txn in transactions:
                try:
                    plot_id = txn.entity_id
                    plot_name = plot_names.get(plot_id, f"Lote #{plot_id}")
                    
                    # Obtener información del tipo y categoría
                    txn_type = transaction_types.get(txn.transaction_type_id)
                    txn_category = transaction_categories.get(txn.transaction_category_id)
                    
                    if not txn_type or not txn_category:
                        continue
                    
                    # Obtener el nombre del creador
                    creator_name = get_creator_info(txn.creator_id)

                    history_item = TransactionHistoryItem(
                        date=txn.transaction_date,
                        plot_name=plot_name,
                        farm_name=farm.name,
                        transaction_type=txn_type.name,
                        transaction_category=txn_category.name,
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
    
    except Exception as e:
        logger.error(f"Error al generar el reporte financiero: {str(e)}")
        return create_response("error", f"Error al generar el reporte financiero: {str(e)}", status_code=500)