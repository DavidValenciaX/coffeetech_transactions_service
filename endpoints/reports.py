from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from adapters.user_client import verify_session_token
from dataBase import get_db_session
from utils.response import create_response, session_token_invalid_response
import logging
from use_cases.generate_financial_report_use_case import generate_financial_report
from domain.schemas import FinancialReportRequest, FinancialReportResponse

router = APIRouter()

logger = logging.getLogger(__name__)

# Endpoint para generar el reporte financiero
@router.post("/financial-report", response_model=FinancialReportResponse)
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
    
    # 3. Llamar al use case para generar el reporte financiero
    try:
        return generate_financial_report(request, user, db)
    except Exception as e:
        logger.error(f"Error al generar el reporte financiero: {str(e)}")
        return create_response("error", f"Error al generar el reporte financiero: {str(e)}", status_code=500)