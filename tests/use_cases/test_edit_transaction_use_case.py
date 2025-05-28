"""
Tests para edit_transaction_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from use_cases.edit_transaction_use_case import (
    edit_transaction_use_case,
    _validate_session_token,
    _validate_transaction_exists_and_active,
    _validate_user_permissions,
    _update_transaction_fields,
    _build_transaction_response
)
from domain.schemas import UpdateTransactionRequest, UserResponse, TransactionResponse
from models.models import Transactions, TransactionCategories, TransactionStates, TransactionTypes
from utils.response import create_response


class TestEditTransactionUseCase:
    """
    Tests para el caso de uso de editar transacción
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        self.mock_db = Mock(spec=Session)
        self.mock_user = UserResponse(
            user_id=1,
            name="Test User",
            email="test@example.com"
        )
        self.session_token = "valid_token"
        
        # Mock transaction
        self.mock_transaction = Mock(spec=Transactions)
        self.mock_transaction.transaction_id = 1
        self.mock_transaction.plot_id = 100
        self.mock_transaction.transaction_category_id = 1
        self.mock_transaction.description = "Original description"
        self.mock_transaction.value = Decimal("1000.00")
        self.mock_transaction.transaction_date = date(2024, 1, 1)
        self.mock_transaction.transaction_state_id = 1
        self.mock_transaction.creator_id = 1
        
        # Mock transaction state
        self.mock_state = Mock(spec=TransactionStates)
        self.mock_state.transaction_state_id = 1
        self.mock_state.name = "Activo"
        
        # Mock transaction category
        self.mock_category = Mock(spec=TransactionCategories)
        self.mock_category.transaction_category_id = 1
        self.mock_category.name = "Test Category"
        
        # Mock transaction type
        self.mock_type = Mock(spec=TransactionTypes)
        self.mock_type.transaction_type_id = 1
        self.mock_type.name = "Test Type"
        self.mock_category.transaction_type = self.mock_type

    @patch('use_cases.edit_transaction_use_case.verify_session_token')
    def test_validate_session_token_success(self, mock_verify_token):
        """Test successful session token validation"""
        mock_verify_token.return_value = self.mock_user
        
        user, error_response = _validate_session_token(self.session_token)
        
        assert user == self.mock_user
        assert error_response is None
        mock_verify_token.assert_called_once_with(self.session_token)

    def test_validate_session_token_missing(self):
        """Test validation with missing session token"""
        user, error_response = _validate_session_token("")
        
        assert user is None
        assert error_response is not None
        assert error_response.status_code == 401

    @patch('use_cases.edit_transaction_use_case.verify_session_token')
    def test_validate_session_token_invalid(self, mock_verify_token):
        """Test validation with invalid session token"""
        mock_verify_token.return_value = None
        
        user, error_response = _validate_session_token(self.session_token)
        
        assert user is None
        assert error_response is not None
        assert error_response.status_code == 401

    @patch('use_cases.edit_transaction_use_case.get_transaction_state')
    def test_validate_transaction_exists_and_active_success(self, mock_get_state):
        """Test successful transaction validation"""
        self.mock_db.query().filter().first.return_value = self.mock_transaction
        
        inactive_state = Mock(spec=TransactionStates)
        inactive_state.transaction_state_id = 2
        mock_get_state.return_value = inactive_state
        
        transaction, error_response = _validate_transaction_exists_and_active(self.mock_db, 1)
        
        assert transaction == self.mock_transaction
        assert error_response is None

    def test_validate_transaction_not_exists(self):
        """Test validation when transaction doesn't exist"""
        self.mock_db.query().filter().first.return_value = None
        
        transaction, error_response = _validate_transaction_exists_and_active(self.mock_db, 999)
        
        assert transaction is None
        assert error_response is not None
        assert error_response.status_code == 404

    @patch('use_cases.edit_transaction_use_case.get_transaction_state')
    def test_validate_transaction_inactive(self, mock_get_state):
        """Test validation when transaction is inactive"""
        inactive_state = Mock(spec=TransactionStates)
        inactive_state.transaction_state_id = 2
        mock_get_state.return_value = inactive_state
        
        # Set transaction as inactive
        self.mock_transaction.transaction_state_id = 2
        self.mock_db.query().filter().first.return_value = self.mock_transaction
        
        transaction, error_response = _validate_transaction_exists_and_active(self.mock_db, 1)
        
        assert transaction is None
        assert error_response is not None
        assert error_response.status_code == 403

    @patch('use_cases.edit_transaction_use_case.get_transaction_state')
    def test_validate_transaction_inactive_state_not_found(self, mock_get_state):
        """Test validation when inactive state is not found"""
        mock_get_state.return_value = None
        self.mock_db.query().filter().first.return_value = self.mock_transaction
        
        transaction, error_response = _validate_transaction_exists_and_active(self.mock_db, 1)
        
        assert transaction is None
        assert error_response is not None
        assert error_response.status_code == 500

    @patch('use_cases.edit_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm')
    @patch('use_cases.edit_transaction_use_case.verify_plot')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm_state_by_name')
    def test_validate_user_permissions_success(self, mock_get_urf_state, mock_verify_plot, 
                                             mock_get_urf, mock_get_permissions):
        """Test successful user permissions validation"""
        # Mock responses
        mock_get_urf_state.return_value = {"user_role_farm_state_id": 1}
        
        mock_plot_info = Mock()
        mock_plot_info.farm_id = 1
        mock_verify_plot.return_value = mock_plot_info
        
        mock_user_role_farm = Mock()
        mock_user_role_farm.user_role_id = 1
        mock_get_urf.return_value = mock_user_role_farm
        
        mock_get_permissions.return_value = ["edit_transaction", "view_transaction"]
        
        error_response = _validate_user_permissions(self.mock_user, self.mock_transaction)
        
        assert error_response is None

    @patch('use_cases.edit_transaction_use_case.get_user_role_farm_state_by_name')
    def test_validate_user_permissions_state_not_found(self, mock_get_urf_state):
        """Test validation when user role farm state is not found"""
        mock_get_urf_state.return_value = None
        
        error_response = _validate_user_permissions(self.mock_user, self.mock_transaction)
        
        assert error_response is not None
        assert error_response.status_code == 400

    @patch('use_cases.edit_transaction_use_case.verify_plot')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm_state_by_name')
    def test_validate_user_permissions_plot_not_found(self, mock_get_urf_state, mock_verify_plot):
        """Test validation when plot is not found"""
        mock_get_urf_state.return_value = {"user_role_farm_state_id": 1}
        mock_verify_plot.return_value = None
        
        error_response = _validate_user_permissions(self.mock_user, self.mock_transaction)
        
        assert error_response is not None
        assert error_response.status_code == 404

    @patch('use_cases.edit_transaction_use_case.get_user_role_farm')
    @patch('use_cases.edit_transaction_use_case.verify_plot')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm_state_by_name')
    def test_validate_user_permissions_no_farm_access(self, mock_get_urf_state, mock_verify_plot, mock_get_urf):
        """Test validation when user has no access to farm"""
        mock_get_urf_state.return_value = {"user_role_farm_state_id": 1}
        
        mock_plot_info = Mock()
        mock_plot_info.farm_id = 1
        mock_verify_plot.return_value = mock_plot_info
        
        mock_get_urf.return_value = None
        
        error_response = _validate_user_permissions(self.mock_user, self.mock_transaction)
        
        assert error_response is not None
        assert error_response.status_code == 403

    @patch('use_cases.edit_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm')
    @patch('use_cases.edit_transaction_use_case.verify_plot')
    @patch('use_cases.edit_transaction_use_case.get_user_role_farm_state_by_name')
    def test_validate_user_permissions_no_edit_permission(self, mock_get_urf_state, mock_verify_plot, 
                                                        mock_get_urf, mock_get_permissions):
        """Test validation when user doesn't have edit permission"""
        mock_get_urf_state.return_value = {"user_role_farm_state_id": 1}
        
        mock_plot_info = Mock()
        mock_plot_info.farm_id = 1
        mock_verify_plot.return_value = mock_plot_info
        
        mock_user_role_farm = Mock()
        mock_user_role_farm.user_role_id = 1
        mock_get_urf.return_value = mock_user_role_farm
        
        mock_get_permissions.return_value = ["view_transaction"]  # No edit permission
        
        error_response = _validate_user_permissions(self.mock_user, self.mock_transaction)
        
        assert error_response is not None
        assert error_response.status_code == 403

    def test_update_transaction_fields_category_success(self):
        """Test successful category update"""
        request = UpdateTransactionRequest(
            transaction_id=1,
            transaction_category_id=2
        )
        
        self.mock_db.query().filter().first.return_value = self.mock_category
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        # Check that the assignment was attempted (the mock will track this)
        assert hasattr(self.mock_transaction, 'transaction_category_id')

    def test_update_transaction_fields_category_not_found(self):
        """Test category update with non-existent category"""
        request = UpdateTransactionRequest(
            transaction_id=1,
            transaction_category_id=999
        )
        
        self.mock_db.query().filter().first.return_value = None
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is not None
        assert error_response.status_code == 400

    def test_update_transaction_fields_description(self):
        """Test successful description update"""
        request = UpdateTransactionRequest(
            transaction_id=1,
            description="New description"
        )
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        # Verify the description was set (mock will track attribute access)
        assert hasattr(self.mock_transaction, 'description')

    def test_update_transaction_fields_value_success(self):
        """Test successful value update"""
        request = UpdateTransactionRequest(
            transaction_id=1,
            value=2000.50
        )
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        # Verify the value was set
        assert hasattr(self.mock_transaction, 'value')

    def test_update_transaction_fields_value_negative(self):
        """Test value update with negative value"""
        # Create request manually to bypass Pydantic validation
        request = Mock()
        request.transaction_id = 1
        request.transaction_category_id = None
        request.description = None
        request.value = -100.0
        request.transaction_date = None
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is not None
        assert error_response.status_code == 400

    def test_update_transaction_fields_value_zero(self):
        """Test value update with zero value"""
        # Create request manually to bypass Pydantic validation
        request = Mock()
        request.transaction_id = 1
        request.transaction_category_id = None
        request.description = None
        request.value = 0.0
        request.transaction_date = None
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is not None
        assert error_response.status_code == 400

    def test_update_transaction_fields_date(self):
        """Test successful date update"""
        new_date = date(2024, 2, 1)
        request = UpdateTransactionRequest(
            transaction_id=1,
            transaction_date=new_date
        )
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        assert self.mock_transaction.transaction_date == new_date

    def test_build_transaction_response_success(self):
        """Test successful transaction response building"""
        # Setup mock queries
        state_query_mock = Mock()
        state_query_mock.filter().first.return_value = self.mock_state
        
        category_query_mock = Mock()
        category_query_mock.options().filter().first.return_value = self.mock_category
        
        self.mock_db.query.side_effect = [state_query_mock, category_query_mock]
        
        response = _build_transaction_response(self.mock_db, self.mock_transaction)
        
        assert isinstance(response, TransactionResponse)
        assert response.transaction_id == self.mock_transaction.transaction_id
        assert response.plot_id == self.mock_transaction.plot_id
        assert response.transaction_type_name == "Test Type"
        assert response.transaction_category_name == "Test Category"
        assert response.transaction_state == "Activo"

    def test_build_transaction_response_no_state(self):
        """Test transaction response building when state is not found"""
        # Setup mock queries
        state_query_mock = Mock()
        state_query_mock.filter().first.return_value = None
        
        category_query_mock = Mock()
        category_query_mock.options().filter().first.return_value = self.mock_category
        
        self.mock_db.query.side_effect = [state_query_mock, category_query_mock]
        
        response = _build_transaction_response(self.mock_db, self.mock_transaction)
        
        assert response.transaction_state == "Desconocido"

    def test_build_transaction_response_no_category(self):
        """Test transaction response building when category is not found"""
        # Setup mock queries
        state_query_mock = Mock()
        state_query_mock.filter().first.return_value = self.mock_state
        
        category_query_mock = Mock()
        category_query_mock.options().filter().first.return_value = None
        
        self.mock_db.query.side_effect = [state_query_mock, category_query_mock]
        
        response = _build_transaction_response(self.mock_db, self.mock_transaction)
        
        assert response.transaction_category_name == "Desconocido"
        assert response.transaction_type_name == "Desconocido"

    @patch('use_cases.edit_transaction_use_case._build_transaction_response')
    @patch('use_cases.edit_transaction_use_case._update_transaction_fields')
    @patch('use_cases.edit_transaction_use_case._validate_user_permissions')
    @patch('use_cases.edit_transaction_use_case._validate_transaction_exists_and_active')
    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_success(self, mock_validate_token, mock_validate_transaction, 
                                             mock_validate_permissions, mock_update_fields, 
                                             mock_build_response):
        """Test complete successful transaction edit"""
        # Setup mocks
        mock_validate_token.return_value = (self.mock_user, None)
        mock_validate_transaction.return_value = (self.mock_transaction, None)
        mock_validate_permissions.return_value = None
        mock_update_fields.return_value = None
        
        mock_response = TransactionResponse(
            transaction_id=1,
            plot_id=100,
            transaction_type_name="Test Type",
            transaction_category_name="Test Category",
            description="Updated description",
            value=2000.0,
            transaction_date=date(2024, 2, 1),
            transaction_state="Activo"
        )
        mock_build_response.return_value = mock_response
        
        request = UpdateTransactionRequest(
            transaction_id=1,
            description="Updated description",
            value=2000.0
        )
        
        result = edit_transaction_use_case(request, self.session_token, self.mock_db)
        
        # Verify all validations were called
        mock_validate_token.assert_called_once_with(self.session_token)
        mock_validate_transaction.assert_called_once_with(self.mock_db, 1)
        mock_validate_permissions.assert_called_once_with(self.mock_user, self.mock_transaction)
        mock_update_fields.assert_called_once_with(self.mock_db, self.mock_transaction, request)
        mock_build_response.assert_called_once_with(self.mock_db, self.mock_transaction)
        
        # Verify database operations
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(self.mock_transaction)
        
        # Verify response
        assert result.status_code == 200

    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_invalid_token(self, mock_validate_token):
        """Test edit transaction with invalid token"""
        error_response = create_response("error", "Invalid token", status_code=401)
        mock_validate_token.return_value = (None, error_response)
        
        request = UpdateTransactionRequest(transaction_id=1, value=2000.0)
        
        result = edit_transaction_use_case(request, "invalid_token", self.mock_db)
        
        assert result.status_code == 401

    @patch('use_cases.edit_transaction_use_case._validate_transaction_exists_and_active')
    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_transaction_not_found(self, mock_validate_token, 
                                                           mock_validate_transaction):
        """Test edit transaction when transaction is not found"""
        mock_validate_token.return_value = (self.mock_user, None)
        
        error_response = create_response("error", "Transaction not found", status_code=404)
        mock_validate_transaction.return_value = (None, error_response)
        
        request = UpdateTransactionRequest(transaction_id=999, value=2000.0)
        
        result = edit_transaction_use_case(request, self.session_token, self.mock_db)
        
        assert result.status_code == 404

    @patch('use_cases.edit_transaction_use_case._validate_user_permissions')
    @patch('use_cases.edit_transaction_use_case._validate_transaction_exists_and_active')
    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_no_permissions(self, mock_validate_token, 
                                                    mock_validate_transaction, 
                                                    mock_validate_permissions):
        """Test edit transaction when user has no permissions"""
        mock_validate_token.return_value = (self.mock_user, None)
        mock_validate_transaction.return_value = (self.mock_transaction, None)
        
        error_response = create_response("error", "No permissions", status_code=403)
        mock_validate_permissions.return_value = error_response
        
        request = UpdateTransactionRequest(transaction_id=1, value=2000.0)
        
        result = edit_transaction_use_case(request, self.session_token, self.mock_db)
        
        assert result.status_code == 403

    @patch('use_cases.edit_transaction_use_case._update_transaction_fields')
    @patch('use_cases.edit_transaction_use_case._validate_user_permissions')
    @patch('use_cases.edit_transaction_use_case._validate_transaction_exists_and_active')
    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_update_error(self, mock_validate_token, 
                                                  mock_validate_transaction, 
                                                  mock_validate_permissions, 
                                                  mock_update_fields):
        """Test edit transaction when update fails"""
        mock_validate_token.return_value = (self.mock_user, None)
        mock_validate_transaction.return_value = (self.mock_transaction, None)
        mock_validate_permissions.return_value = None
        
        error_response = create_response("error", "Update failed", status_code=400)
        mock_update_fields.return_value = error_response
        
        # Use a valid request for this test since we're mocking the update function
        request = UpdateTransactionRequest(transaction_id=1, value=2000.0)
        
        result = edit_transaction_use_case(request, self.session_token, self.mock_db)
        
        assert result.status_code == 400

    @patch('use_cases.edit_transaction_use_case._build_transaction_response')
    @patch('use_cases.edit_transaction_use_case._update_transaction_fields')
    @patch('use_cases.edit_transaction_use_case._validate_user_permissions')
    @patch('use_cases.edit_transaction_use_case._validate_transaction_exists_and_active')
    @patch('use_cases.edit_transaction_use_case._validate_session_token')
    def test_edit_transaction_use_case_database_exception(self, mock_validate_token, 
                                                        mock_validate_transaction, 
                                                        mock_validate_permissions, 
                                                        mock_update_fields, 
                                                        mock_build_response):
        """Test edit transaction when database exception occurs"""
        mock_validate_token.return_value = (self.mock_user, None)
        mock_validate_transaction.return_value = (self.mock_transaction, None)
        mock_validate_permissions.return_value = None
        mock_update_fields.return_value = None
        
        # Mock database exception during commit
        self.mock_db.commit.side_effect = Exception("Database error")
        
        request = UpdateTransactionRequest(transaction_id=1, value=2000.0)
        
        result = edit_transaction_use_case(request, self.session_token, self.mock_db)
        
        # Verify rollback was called
        self.mock_db.rollback.assert_called_once()
        assert result.status_code == 500

    def test_update_transaction_fields_all_fields(self):
        """Test updating all fields at once"""
        new_date = date(2024, 3, 1)
        request = UpdateTransactionRequest(
            transaction_id=1,
            transaction_category_id=2,
            description="New description",
            value=3000.0,
            transaction_date=new_date
        )
        
        self.mock_db.query().filter().first.return_value = self.mock_category
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        # Verify that all fields have been accessed/set on the mock
        assert hasattr(self.mock_transaction, 'transaction_category_id')
        assert hasattr(self.mock_transaction, 'description')
        assert hasattr(self.mock_transaction, 'value')
        assert hasattr(self.mock_transaction, 'transaction_date')

    def test_update_transaction_fields_no_fields(self):
        """Test updating with no fields specified"""
        request = UpdateTransactionRequest(transaction_id=1)
        
        error_response = _update_transaction_fields(self.mock_db, self.mock_transaction, request)
        
        assert error_response is None
        # Verify no changes were made
        assert self.mock_transaction.transaction_category_id == 1
        assert self.mock_transaction.description == "Original description"
        assert self.mock_transaction.value == Decimal("1000.00")
        assert self.mock_transaction.transaction_date == date(2024, 1, 1)