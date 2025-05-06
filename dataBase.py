import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(override=True, encoding='utf-8')

def running_in_docker():
    # Detecta si está en Docker
    path = "/.dockerenv"
    if os.path.exists(path):
        return True
    try:
        with open("/proc/1/cgroup", "rt") as f:
            return "docker" in f.read()
    except Exception:
        return False

# Selecciona el host según el entorno
if running_in_docker():
    DB_HOST = "host.docker.internal"
else:
    DB_HOST = os.getenv("PGHOST", "localhost")

DB_PORT = os.getenv("PGPORT")
DB_NAME = os.getenv("PGDATABASE")
DB_USER = os.getenv("PGUSER")
DB_PASSWORD = os.getenv("PGPASSWORD")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'client_encoding': 'utf8'}, pool_pre_ping=True)

# Configurar logger
logger = logging.getLogger(__name__)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        logger.info("Conexión exitosa a la base de datos")
except Exception as e:
    logger.error(f"Error al conectar a la base de datos: {e}")
    
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """
    Proporciona una sesión de base de datos, que se puede utilizar 
    en las operaciones CRUD. Asegura que la sesión se cierre 
    correctamente después de su uso.

    Yields:
        Session: Una sesión de base de datos.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
