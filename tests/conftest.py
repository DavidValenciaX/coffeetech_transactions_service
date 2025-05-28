"""
Configuración global de pytest para el proyecto de transacciones.
Este archivo debe estar en la carpeta tests/ para que pytest lo detecte automáticamente.
"""
# IMPORTANTE: Importar mock_database ANTES que cualquier otra cosa
import tests.mock_database  # Esto aplica los mocks globalmente

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session():
    """
    Fixture que proporciona una sesión de base de datos mock para testing
    """
    return Mock(spec=Session)


@pytest.fixture(scope="session", autouse=True)
def setup_and_cleanup():
    """
    Configuración y limpieza de la sesión de testing
    """
    yield
    # Limpiar patches al final
    tests.mock_database.cleanup_patches() 