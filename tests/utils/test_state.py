"""
Tests para utils/state.py

Este módulo contiene tests para las funciones utilitarias de estado:
- get_transaction_state
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from utils.state import get_transaction_state
from models.models import TransactionStates


class TestGetTransactionState:
    """Tests para la función get_transaction_state"""
    
    def setup_method(self):
        """Configuración antes de cada test"""
        self.mock_db = Mock(spec=Session)
        
    def test_get_transaction_state_success(self):
        """Test exitoso de obtener estado de transacción"""
        # Arrange
        mock_state = Mock()
        mock_state.state_id = 1
        mock_state.name = "Activo"
        
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_state
        
        # Act
        result = get_transaction_state(self.mock_db, "Activo")
        
        # Assert
        assert result == mock_state
        self.mock_db.query.assert_called_once_with(TransactionStates)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
    
    def test_get_transaction_state_not_found(self):
        """Test cuando no se encuentra el estado"""
        # Arrange
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        # Act
        result = get_transaction_state(self.mock_db, "NoExiste")
        
        # Assert
        assert result is None
        self.mock_db.query.assert_called_once_with(TransactionStates)
    
    def test_get_transaction_state_inactive(self):
        """Test de obtener estado inactivo"""
        # Arrange
        mock_state = Mock()
        mock_state.state_id = 2
        mock_state.name = "Inactivo"
        
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_state
        
        # Act
        result = get_transaction_state(self.mock_db, "Inactivo")
        
        # Assert
        assert result == mock_state
        assert result.name == "Inactivo"
    
    @patch('utils.state.logger')
    def test_get_transaction_state_exception(self, mock_logger):
        """Test cuando ocurre una excepción en la consulta"""
        # Arrange
        self.mock_db.query.side_effect = Exception("Database error")
        
        # Act
        result = get_transaction_state(self.mock_db, "Activo")
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Error al obtener el estado 'Activo' para transacciones" in error_call_args
    
    def test_get_transaction_state_different_states(self):
        """Test con diferentes nombres de estado"""
        # Arrange
        states = ["Activo", "Inactivo", "Pendiente", "Cancelado"]
        
        for state_name in states:
            mock_state = Mock()
            mock_state.name = state_name
            
            mock_query = Mock()
            self.mock_db.query.return_value = mock_query
            mock_query.filter.return_value.first.return_value = mock_state
            
            # Act
            result = get_transaction_state(self.mock_db, state_name)
            
            # Assert
            assert result.name == state_name
    
    def test_get_transaction_state_empty_string(self):
        """Test con string vacío como nombre de estado"""
        # Arrange
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        # Act
        result = get_transaction_state(self.mock_db, "")
        
        # Assert
        assert result is None
    
    def test_get_transaction_state_case_sensitive(self):
        """Test que la búsqueda es case-sensitive"""
        # Arrange
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        # Act
        result = get_transaction_state(self.mock_db, "activo")  # lowercase
        
        # Assert
        assert result is None
        # Verificar que se hizo la consulta con el texto exacto
        filter_call = mock_query.filter.call_args
        # El filtro debe incluir el texto tal como se pasó
        assert filter_call is not None 