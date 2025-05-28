"""
Configuración global de pytest para el proyecto de transacciones.
"""
import os
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

# Configurar variables de entorno para testing antes de cualquier importación
os.environ["PYTEST_CURRENT_TEST"] = "true"
os.environ["PGHOST"] = "localhost"
os.environ["PGPORT"] = "5432"
os.environ["PGDATABASE"] = "test_db"
os.environ["PGUSER"] = "test_user"
os.environ["PGPASSWORD"] = "test_password"


@pytest.fixture
def mock_db_session():
    """
    Fixture que proporciona una sesión de base de datos mock para testing
    """
    mock_session = Mock(spec=Session)
    return mock_session


@pytest.fixture(autouse=True)
def mock_database_initialization():
    """
    Fixture que automáticamente mockea la inicialización de la base de datos
    para todos los tests
    """
    with patch('dataBase.initialize_database') as _:
        with patch('dataBase.get_db_session') as mock_get_session:
            mock_session = Mock(spec=Session)
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            yield mock_session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Fixture que configura el entorno de testing
    """
    # Asegurar que estamos en modo testing
    os.environ["PYTEST_CURRENT_TEST"] = "true"
    yield
    # Cleanup después del test si es necesario 