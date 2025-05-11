from fastapi import FastAPI
from endpoints import transactions, reports
from utils.logger import setup_logger

# Setup logging for the entire application
logger = setup_logger()
logger.info("Starting CoffeeTech Transactions Service")

app = FastAPI()

app.include_router(transactions.router, prefix="/transaction", tags=["Transacciones"])

app.include_router(reports.router, prefix="/reports", tags=["Reports"])

@app.get("/", include_in_schema=False)
def read_root():
    """
    Ruta raíz que retorna un mensaje de bienvenida.

    Returns:
        dict: Un diccionario con un mensaje de bienvenida.
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the FastAPI application CoffeeTech Transactions Service!"}