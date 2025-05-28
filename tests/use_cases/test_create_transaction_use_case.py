"""
Tests para create_transaction_use_case.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from use_cases.create_transaction_use_case import create_transaction_use_case
from domain.schemas import CreateTransactionRequest, UserResponse, PlotVerificationResponse, UserRoleFarmResponse
from models.models import TransactionCategories, TransactionTypes, Transactions, TransactionStates
from utils.response import create_response, session_token_invalid_response


class TestCreateTransactionUseCase:
    """
    Tests para el caso de uso de crear transacción
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        self.mock_db = Mock(spec=Session)
        self.valid_request = CreateTransactionRequest(
            plot_id=1,
            transaction_category_id=1,
            description="Test transaction",
            value=100.0,
            transaction_date=date(2024, 1, 15)
        )
        self.session_token = "valid_session_token"
        
        # Mock user response
        self.mock_user = UserResponse(
            user_id=1,
            name="Test User",
            email="test@example.com"
        )
        
        # Mock plot verification response
        self.mock_plot = PlotVerificationResponse(
            plot_id=1,
            name="Test Plot",
            farm_id=1,
            plot_state_id=1,
            plot_state="Activo"
        )
        
        # Mock user role farm response
        self.mock_user_role_farm = UserRoleFarmResponse(
            user_role_farm_id=1,
            user_role_id=1,
            farm_id=1,
            user_role_farm_state_id=1,
            user_role_farm_state="Activo"
        )
        
        # Mock transaction category
        self.mock_transaction_category = TransactionCategories(
            transaction_category_id=1,
            name="Test Category",
            transaction_type_id=1
        )
        
        # Mock transaction type
        self.mock_transaction_type = TransactionTypes(
            transaction_type_id=1,
            name="Gasto"
        )
        
        # Mock transaction state
        self.mock_transaction_state = TransactionStates(
            transaction_state_id=1,
            name="Activo"
        )

    def test_create_transaction_missing_session_token(self):
        """
        Test que falla cuando no se proporciona session_token
        """
        response = create_transaction_use_case(self.valid_request, "", self.mock_db)
        
        assert response.status_code == 401
        response_data = response.body.decode()
        assert "Token de sesión faltante" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    def test_create_transaction_invalid_session_token(self, mock_verify_token):
        """
        Test que falla cuando el session_token es inválido
        """
        mock_verify_token.return_value = None
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 401
        response_data = response.body.decode()
        assert "Credenciales expiradas" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    def test_create_transaction_missing_active_state(self, mock_get_state, mock_verify_token):
        """
        Test que falla cuando no se encuentra el estado 'Activo' para user_role_farm
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = None
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "Estado 'Activo' para user_role_farm no encontrado" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    def test_create_transaction_invalid_plot(self, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando el lote no existe o no está activo
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = None
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 404
        response_data = response.body.decode()
        assert "El lote especificado no existe o no está activo" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    def test_create_transaction_user_not_associated_with_farm(self, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando el usuario no está asociado con la finca
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = None
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 403
        response_data = response.body.decode()
        assert "No tienes permisos para agregar transacciones" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    def test_create_transaction_insufficient_permissions(self, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando el usuario no tiene permisos para agregar transacciones
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["read_transaction", "edit_transaction"]  # Sin 'add_transaction'
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 403
        response_data = response.body.decode()
        assert "No tienes permiso para agregar transacciones" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    def test_create_transaction_invalid_category(self, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando la categoría de transacción no existe
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        
        # Mock query que no encuentra la categoría
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "La categoría de transacción especificada no existe" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    def test_create_transaction_invalid_transaction_type(self, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando el tipo de transacción asociado a la categoría no existe
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        
        # Mock queries - categoría existe pero tipo no
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_transaction_category,  # Primera consulta - categoría existe
            None  # Segunda consulta - tipo no existe
        ]
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "El tipo de transacción asociado a la categoría no existe" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    def test_create_transaction_negative_value(self, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando el valor de la transacción es negativo o cero
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        
        # Usar valor negativo
        invalid_request = CreateTransactionRequest(
            plot_id=1,
            transaction_category_id=1,
            description="Test transaction",
            value=-100.0,
            transaction_date=date(2024, 1, 15)
        )
        
        response = create_transaction_use_case(invalid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "El valor de la transacción debe ser positivo" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.create_transaction_use_case.get_transaction_state')
    def test_create_transaction_missing_transaction_state(self, mock_get_transaction_state, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que falla cuando no se encuentra el estado 'Activo' para transacciones
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        mock_get_transaction_state.return_value = None
        
        # Mock queries para categoría y tipo exitosos
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_transaction_category,
            self.mock_transaction_type
        ]
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Estado 'Activo' para Transactions no encontrado" in response_data

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.create_transaction_use_case.get_transaction_state')
    def test_create_transaction_database_error(self, mock_get_transaction_state, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test que maneja errores de base de datos durante la creación
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        mock_get_transaction_state.return_value = self.mock_transaction_state
        
        # Mock queries para categoría y tipo exitosos
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_transaction_category,
            self.mock_transaction_type
        ]
        
        # Simular error en la base de datos durante commit
        self.mock_db.commit.side_effect = Exception("Database error")
        
        response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Error al crear la transacción: Database error" in response_data
        # Verificar que se llama rollback
        self.mock_db.rollback.assert_called_once()

    @patch('use_cases.create_transaction_use_case.verify_session_token')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_transaction_use_case.verify_plot')
    @patch('use_cases.create_transaction_use_case.get_user_role_farm')
    @patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.create_transaction_use_case.get_transaction_state')
    def test_create_transaction_success(self, mock_get_transaction_state, mock_get_permissions, mock_get_user_role_farm, mock_verify_plot, mock_get_state, mock_verify_token):
        """
        Test exitoso de creación de transacción
        """
        mock_verify_token.return_value = self.mock_user
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = self.mock_plot
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["add_transaction"]
        mock_get_transaction_state.return_value = self.mock_transaction_state
        
        # Mock queries para categoría y tipo exitosos
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_transaction_category,
            self.mock_transaction_type
        ]
        
        # Mock de la transacción creada
        mock_new_transaction = Mock()
        mock_new_transaction.transaction_id = 1
        mock_new_transaction.plot_id = 1
        mock_new_transaction.description = "Test transaction"
        mock_new_transaction.value = Decimal('100.0')
        mock_new_transaction.transaction_date = date(2024, 1, 15)
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Simular que el objeto añadido es el mock_new_transaction
        with patch('use_cases.create_transaction_use_case.Transactions', return_value=mock_new_transaction):
            response = create_transaction_use_case(self.valid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Transacción creada correctamente" in response_data
        assert "success" in response_data
        
        # Verificar que se llamaron los métodos de base de datos
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_create_transaction_zero_value(self):
        """
        Test que falla cuando el valor de la transacción es cero
        """
        # Usar valor cero
        invalid_request = CreateTransactionRequest(
            plot_id=1,
            transaction_category_id=1,
            description="Test transaction",
            value=0.0,
            transaction_date=date(2024, 1, 15)
        )
        
        with patch('use_cases.create_transaction_use_case.verify_session_token') as mock_verify_token:
            mock_verify_token.return_value = self.mock_user
            
            with patch('use_cases.create_transaction_use_case.get_user_role_farm_state_by_name') as mock_get_state:
                mock_get_state.return_value = {"user_role_farm_state_id": 1}
                
                with patch('use_cases.create_transaction_use_case.verify_plot') as mock_verify_plot:
                    mock_verify_plot.return_value = self.mock_plot
                    
                    with patch('use_cases.create_transaction_use_case.get_user_role_farm') as mock_get_user_role_farm:
                        mock_get_user_role_farm.return_value = self.mock_user_role_farm
                        
                        with patch('use_cases.create_transaction_use_case.get_role_permissions_for_user_role') as mock_get_permissions:
                            mock_get_permissions.return_value = ["add_transaction"]
                            
                            response = create_transaction_use_case(invalid_request, self.session_token, self.mock_db)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "El valor de la transacción debe ser positivo" in response_data 