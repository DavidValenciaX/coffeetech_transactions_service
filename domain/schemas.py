from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class CreateTransactionRequest(BaseModel):
    plot_id: int = Field(..., description="ID del lote asociado a la transacción")
    transaction_category_id: int = Field(..., description="ID de la categoría de la transacción")
    description: Optional[str] = Field(None, max_length=255, description="Descripción de la transacción (máximo 255 caracteres)")
    value: float = Field(..., description="Valor de la transacción")
    transaction_date: date = Field(..., description="Fecha de la transacción")

class UpdateTransactionRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción a actualizar")
    transaction_category_id: Optional[int] = Field(None, description="Nuevo ID de la categoría de la transacción")
    description: Optional[str] = Field(None, max_length=255, description="Nueva descripción de la transacción (máximo 255 caracteres)")
    value: Optional[float] = Field(None, description="Nuevo valor de la transacción")
    transaction_date: Optional[date] = Field(None, description="Nueva fecha de la transacción")
    
    @field_validator('value')
    def value_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('El valor de la transacción debe ser positivo')
        return v

class DeleteTransactionRequest(BaseModel):
    transaction_id: int = Field(..., description="ID de la transacción a eliminar")

class TransactionResponse(BaseModel):
    transaction_id: int
    plot_id: int
    transaction_type_name: str
    transaction_category_name: str
    description: Optional[str]
    value: float
    transaction_date: date
    transaction_state: str

class TransactionTypeResponse(BaseModel):
    transaction_type_id: int
    name: str

class TransactionCategoryResponse(BaseModel):
    transaction_category_id: int
    name: str
    transaction_type_id: int
    transaction_type_name: str

# Financial Report Schemas
class FinancialReportRequest(BaseModel):
    plot_ids: List[int] = Field(..., description="Lista de IDs de lotes (debe contener al menos un ID)", min_items=1)
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
