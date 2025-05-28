"""
Módulo para configurar mocks de base de datos en testing.
Este módulo debe ser importado ANTES que dataBase.py para que los mocks funcionen.
"""
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Configurar variables de entorno
os.environ.update({
    "PYTEST_CURRENT_TEST": "true",
    "PGHOST": "localhost",
    "PGPORT": "5432", 
    "PGDATABASE": "test_db",
    "PGUSER": "test_user",
    "PGPASSWORD": "test_password"
})

# Crear mocks globales
mock_engine = MagicMock()
mock_connection = MagicMock()
mock_session = Mock(spec=Session)
mock_sessionmaker = MagicMock(return_value=mock_session)

# Configurar comportamiento de los mocks
mock_connection.__enter__ = MagicMock(return_value=mock_connection)
mock_connection.__exit__ = MagicMock(return_value=None)
mock_connection.execute = MagicMock(return_value=MagicMock())
mock_engine.connect = MagicMock(return_value=mock_connection)

# Aplicar los patches globalmente
create_engine_patcher = patch('sqlalchemy.create_engine', return_value=mock_engine)
sessionmaker_patcher = patch('sqlalchemy.orm.sessionmaker', return_value=mock_sessionmaker)

# Iniciar los patches
create_engine_patcher.start()
sessionmaker_patcher.start()

def get_mock_session():
    """Retorna una sesión mock para testing"""
    return Mock(spec=Session)

def cleanup_patches():
    """Limpia los patches cuando termine el testing"""
    create_engine_patcher.stop()
    sessionmaker_patcher.stop() 