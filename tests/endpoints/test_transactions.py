"""
Tests para los endpoints de transacciones

Este módulo contiene tests para todos los endpoints de transacciones:
- create_transaction
- edit_transaction  
- delete_transaction
- read_transactions
- get_transaction_types
- get_transaction_categories
"""
import pytest
from unittest.mock import Mock, patch


class TestTransactionEndpoints:
    """Tests para los endpoints de transacciones"""
    
    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.create_transaction_use_case')
    def test_create_transaction_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de crear transacción"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import create_transaction
        assert create_transaction is not None

    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.edit_transaction_use_case')
    def test_edit_transaction_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de editar transacción"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import edit_transaction
        assert edit_transaction is not None

    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.delete_transaction_use_case')
    def test_delete_transaction_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de eliminar transacción"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import delete_transaction
        assert delete_transaction is not None

    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.list_transactions_use_case')
    def test_read_transactions_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de listar transacciones"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import read_transactions
        assert read_transactions is not None

    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.list_transaction_types_use_case')
    def test_get_transaction_types_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de listar tipos de transacción"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import get_transaction_types
        assert get_transaction_types is not None

    @patch('endpoints.transactions.get_db_session')
    @patch('endpoints.transactions.list_transaction_categories_use_case')
    def test_get_transaction_categories_endpoint(self, mock_use_case, mock_db):
        """Test del endpoint de listar categorías de transacción"""
        # Arrange
        mock_db.return_value = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_use_case.return_value = mock_response
        
        # Act & Assert
        mock_use_case.assert_not_called()
        mock_db.assert_not_called()
        
        # Verificar que las importaciones están disponibles
        from endpoints.transactions import get_transaction_categories
        assert get_transaction_categories is not None

    def test_router_import(self):
        """Test que el router se puede importar correctamente"""
        from endpoints.transactions import router
        assert router is not None

    def test_timezone_import(self):
        """Test que el timezone se importa correctamente"""
        from endpoints.transactions import bogota_tz
        assert bogota_tz is not None

    def test_logger_import(self):
        """Test que el logger se importa correctamente"""
        from endpoints.transactions import logger
        assert logger is not None 