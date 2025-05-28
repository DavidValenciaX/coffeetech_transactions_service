"""
Tests para list_transactions_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date
from decimal import Decimal

from use_cases.list_transactions_use_case import list_transactions_use_case
from domain.schemas import UserResponse, PlotVerificationResponse, UserRoleFarmResponse
from models.models import Transactions


class TestListTransactionsUseCase:
    """
    Tests para el caso de uso de listar transacciones
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        # Mock database session
        self.mock_db = Mock()
        
        # Mock user data
        self.valid_user = UserResponse(
            user_id=1,
            name="Test User",
            email="test@example.com"
        )
        
        # Mock plot data
        self.valid_plot = PlotVerificationResponse(
            plot_id=1,
            name="Test Plot",
            farm_id=1,
            plot_state_id=1,
            plot_state="Activo"
        )
        
        # Mock user role farm data
        self.valid_user_role_farm = UserRoleFarmResponse(
            user_role_farm_id=1,
            user_role_id=1,
            farm_id=1,
            user_role_farm_state_id=1,
            user_role_farm_state="Activo"
        )
        
        # Mock transaction state
        self.inactive_state = Mock()
        self.inactive_state.transaction_state_id = 2
        self.inactive_state.name = "Inactivo"
        
        # Mock transaction type
        self.transaction_type = Mock()
        self.transaction_type.name = "Ingreso"
        
        # Mock transaction category
        self.transaction_category = Mock()
        self.transaction_category.name = "Venta de producto"
        self.transaction_category.transaction_type = self.transaction_type
        
        # Mock transaction state (active)
        self.active_state = Mock()
        self.active_state.name = "Activo"
        
        # Mock transaction
        self.mock_transaction = Mock()
        self.mock_transaction.transaction_id = 1
        self.mock_transaction.plot_id = 1
        self.mock_transaction.description = "Test transaction"
        self.mock_transaction.value = Decimal("100.50")
        self.mock_transaction.transaction_date = date(2024, 1, 15)
        self.mock_transaction.transaction_category = self.transaction_category
        self.mock_transaction.state = self.active_state

    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_missing_session_token(self, mock_verify_token):
        """
        Test cuando no se proporciona el token de sesión
        """
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 401
        response_data = response.body.decode()
        assert "Token de sesión faltante" in response_data
        mock_verify_token.assert_not_called()

    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_invalid_session_token(self, mock_verify_token):
        """
        Test cuando el token de sesión es inválido
        """
        # Arrange
        mock_verify_token.return_value = None
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="invalid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 401
        response_data = response.body.decode()
        assert "Credenciales expiradas" in response_data
        mock_verify_token.assert_called_once_with("invalid_token")

    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_plot_not_found(self, mock_verify_token, mock_verify_plot, 
                           mock_get_user_role_farm, mock_get_permissions):
        """
        Test cuando el lote no existe o no está activo
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = None
        
        # Act
        response = list_transactions_use_case(
            plot_id=999,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 404
        response_data = response.body.decode()
        assert "El lote no existe o no está activo" in response_data
        mock_verify_plot.assert_called_once_with(999)
        mock_get_user_role_farm.assert_not_called()

    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_user_not_associated_with_farm(self, mock_verify_token, mock_verify_plot,
                                          mock_get_user_role_farm, mock_get_permissions):
        """
        Test cuando el usuario no está asociado con la finca del lote
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = None
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        response_data = response.body.decode()
        assert "No tienes permiso para ver las transacciones en esta finca" in response_data
        mock_get_user_role_farm.assert_called_once_with(1, 1)
        mock_get_permissions.assert_not_called()

    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_user_no_read_permission(self, mock_verify_token, mock_verify_plot,
                                    mock_get_user_role_farm, mock_get_permissions):
        """
        Test cuando el usuario no tiene permiso para leer transacciones
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["create_transaction", "update_transaction"]  # Sin read_transaction
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        response_data = response.body.decode()
        assert "No tienes permiso para ver las transacciones" in response_data
        mock_get_permissions.assert_called_once_with(1)

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_inactive_state_not_found(self, mock_verify_token, mock_verify_plot,
                                     mock_get_user_role_farm, mock_get_permissions,
                                     mock_get_transaction_state):
        """
        Test cuando no se encuentra el estado 'Inactivo' para transacciones
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = None
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Estado 'Inactivo' para Transactions no encontrado" in response_data
        mock_get_transaction_state.assert_called_once_with(self.mock_db, "Inactivo")

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_no_transactions_found(self, mock_verify_token, mock_verify_plot,
                                  mock_get_user_role_farm, mock_get_permissions,
                                  mock_get_transaction_state):
        """
        Test cuando no hay transacciones para el lote
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Mock database query to return empty list
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "El lote no tiene transacciones registradas" in response_data
        assert '"transactions":[]' in response_data

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_successful_transaction_listing(self, mock_verify_token, mock_verify_plot,
                                           mock_get_user_role_farm, mock_get_permissions,
                                           mock_get_transaction_state):
        """
        Test del caso exitoso: listar transacciones correctamente
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction", "create_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Mock database query to return transactions
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.all.return_value = [self.mock_transaction]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Transacciones obtenidas exitosamente" in response_data
        assert "transactions" in response_data
        assert "Test transaction" in response_data
        assert "100.5" in response_data

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_transaction_with_missing_category(self, mock_verify_token, mock_verify_plot,
                                              mock_get_user_role_farm, mock_get_permissions,
                                              mock_get_transaction_state):
        """
        Test de transacción con categoría faltante
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Mock transaction without category
        transaction_without_category = Mock()
        transaction_without_category.transaction_id = 1
        transaction_without_category.plot_id = 1
        transaction_without_category.description = "Transaction without category"
        transaction_without_category.value = Decimal("50.00")
        transaction_without_category.transaction_date = date(2024, 1, 15)
        transaction_without_category.transaction_category = None
        transaction_without_category.state = self.active_state
        
        # Mock database query
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.all.return_value = [transaction_without_category]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Transacciones obtenidas exitosamente" in response_data
        assert "Desconocido" in response_data  # Default values for missing category/type

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_transaction_with_missing_state(self, mock_verify_token, mock_verify_plot,
                                           mock_get_user_role_farm, mock_get_permissions,
                                           mock_get_transaction_state):
        """
        Test de transacción con estado faltante
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Mock transaction without state
        transaction_without_state = Mock()
        transaction_without_state.transaction_id = 1
        transaction_without_state.plot_id = 1
        transaction_without_state.description = "Transaction without state"
        transaction_without_state.value = Decimal("75.25")
        transaction_without_state.transaction_date = date(2024, 1, 15)
        transaction_without_state.transaction_category = self.transaction_category
        transaction_without_state.state = None
        
        # Mock database query
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.all.return_value = [transaction_without_state]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Transacciones obtenidas exitosamente" in response_data
        assert "Desconocido" in response_data  # Default value for missing state

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_multiple_transactions_listing(self, mock_verify_token, mock_verify_plot,
                                          mock_get_user_role_farm, mock_get_permissions,
                                          mock_get_transaction_state):
        """
        Test de listado de múltiples transacciones
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Create multiple mock transactions
        transaction1 = Mock()
        transaction1.transaction_id = 1
        transaction1.plot_id = 1
        transaction1.description = "First transaction"
        transaction1.value = Decimal("100.00")
        transaction1.transaction_date = date(2024, 1, 15)
        transaction1.transaction_category = self.transaction_category
        transaction1.state = self.active_state
        
        transaction2 = Mock()
        transaction2.transaction_id = 2
        transaction2.plot_id = 1
        transaction2.description = "Second transaction"
        transaction2.value = Decimal("200.50")
        transaction2.transaction_date = date(2024, 1, 16)
        transaction2.transaction_category = self.transaction_category
        transaction2.state = self.active_state
        
        # Mock database query
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.all.return_value = [transaction1, transaction2]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Transacciones obtenidas exitosamente" in response_data
        assert "First transaction" in response_data
        assert "Second transaction" in response_data
        assert "100.0" in response_data
        assert "200.5" in response_data

    @patch('use_cases.list_transactions_use_case.get_transaction_state')
    @patch('use_cases.list_transactions_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.list_transactions_use_case.get_user_role_farm')
    @patch('use_cases.list_transactions_use_case.verify_plot')
    @patch('use_cases.list_transactions_use_case.verify_session_token')
    def test_database_query_filters_correctly(self, mock_verify_token, mock_verify_plot,
                                              mock_get_user_role_farm, mock_get_permissions,
                                              mock_get_transaction_state):
        """
        Test que verifica que la consulta a la base de datos filtra correctamente
        """
        # Arrange
        mock_verify_token.return_value = self.valid_user
        mock_verify_plot.return_value = self.valid_plot
        mock_get_user_role_farm.return_value = self.valid_user_role_farm
        mock_get_permissions.return_value = ["read_transaction"]
        mock_get_transaction_state.return_value = self.inactive_state
        
        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_options = Mock()
        
        # Setup the chain of mocks
        self.mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        
        # Act
        response = list_transactions_use_case(
            plot_id=1,
            session_token="valid_token",
            db=self.mock_db
        )
        
        # Assert that database was queried correctly
        self.mock_db.query.assert_called_once_with(Transactions)
        mock_query.options.assert_called_once()
        mock_options.filter.assert_called_once()
        mock_filter.all.assert_called_once()
        assert response.status_code == 200 