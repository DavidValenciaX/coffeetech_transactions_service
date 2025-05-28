"""
Tests para delete_transaction_use_case.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from decimal import Decimal
from pydantic import ValidationError

from use_cases.delete_transaction_use_case import delete_transaction_use_case
from domain.schemas import DeleteTransactionRequest, UserResponse, PlotVerificationResponse, UserRoleFarmResponse
from models.models import Transactions, TransactionStates


class TestDeleteTransactionUseCase:
    """
    Tests para el caso de uso de eliminar transacción
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        # Mock de la sesión de base de datos
        self.mock_db = Mock()
        
        # Datos de prueba
        self.valid_request = DeleteTransactionRequest(transaction_id=1)
        self.valid_session_token = "valid_token_123"
        
        # Usuario mock
        self.mock_user = UserResponse(
            user_id=1,
            name="Test User",
            email="test@example.com"
        )
        
        # Transacción mock
        self.mock_transaction = Mock(spec=Transactions)
        self.mock_transaction.transaction_id = 1
        self.mock_transaction.plot_id = 1
        self.mock_transaction.transaction_state_id = 1
        
        # Estado de transacción mock
        self.mock_inactive_state = Mock(spec=TransactionStates)
        self.mock_inactive_state.transaction_state_id = 2
        self.mock_inactive_state.name = "Inactivo"
        
        # Plot verification mock
        self.mock_plot_info = PlotVerificationResponse(
            plot_id=1,
            name="Test Plot",
            farm_id=1,
            plot_state_id=1,
            plot_state="Activo"
        )
        
        # User role farm mock
        self.mock_user_role_farm = UserRoleFarmResponse(
            user_role_farm_id=1,
            user_role_id=1,
            farm_id=1,
            user_role_farm_state_id=1,
            user_role_farm_state="Activo"
        )

    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_missing_session_token(self, mock_verify_token):
        """
        Test cuando no se proporciona session_token
        """
        # Arrange
        empty_token = ""
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=empty_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 401
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"Token de sesión faltante"' in content
        mock_verify_token.assert_not_called()

    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_invalid_session_token(self, mock_verify_token):
        """
        Test cuando el session_token es inválido
        """
        # Arrange
        mock_verify_token.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 401
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"Credenciales expiradas, cerrando sesión."' in content
        mock_verify_token.assert_called_once_with(self.valid_session_token)

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_not_found(self, mock_verify_token, mock_get_state, 
                                        mock_verify_plot, mock_get_user_role_farm, 
                                        mock_get_permissions):
        """
        Test cuando la transacción no existe
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 404
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"La transacción especificada no existe"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_inactive_state_not_found(self, mock_verify_token, mock_get_state, 
                                                       mock_verify_plot, mock_get_user_role_farm, 
                                                       mock_get_permissions):
        """
        Test cuando no se encuentra el estado 'Inactivo'
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 500
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"Estado \'Inactivo\' para Transactions no encontrado"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_already_inactive(self, mock_verify_token, mock_get_state, 
                                                mock_verify_plot, mock_get_user_role_farm, 
                                                mock_get_permissions):
        """
        Test cuando la transacción ya está inactiva
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 2  # Estado inactivo
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 400
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"La transacción ya está eliminada"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_plot_not_found(self, mock_verify_token, mock_get_state, 
                                             mock_verify_plot, mock_get_user_role_farm, 
                                             mock_get_permissions):
        """
        Test cuando el lote asociado a la transacción no existe
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1  # Estado activo
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 404
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"El lote asociado a esta transacción no existe o no está activo"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_user_not_associated_with_farm(self, mock_verify_token, mock_get_state, 
                                                            mock_verify_plot, mock_get_user_role_farm, 
                                                            mock_get_permissions):
        """
        Test cuando el usuario no está asociado con la finca
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"No tienes permisos para eliminar transacciones en esta finca"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_no_delete_permission(self, mock_verify_token, mock_get_state, 
                                                   mock_verify_plot, mock_get_user_role_farm, 
                                                   mock_get_permissions):
        """
        Test cuando el usuario no tiene permiso para eliminar transacciones
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["read_transaction", "create_transaction"]  # Sin delete_transaction
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"No tienes permiso para eliminar transacciones"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_empty_permissions(self, mock_verify_token, mock_get_state, 
                                                mock_verify_plot, mock_get_user_role_farm, 
                                                mock_get_permissions):
        """
        Test cuando el usuario no tiene permisos (lista vacía)
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = []
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"No tienes permiso para eliminar transacciones"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_none_permissions(self, mock_verify_token, mock_get_state, 
                                               mock_verify_plot, mock_get_user_role_farm, 
                                               mock_get_permissions):
        """
        Test cuando get_role_permissions_for_user_role retorna None
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = None
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 403
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"No tienes permiso para eliminar transacciones"' in content

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_success(self, mock_verify_token, mock_get_state, 
                                      mock_verify_plot, mock_get_user_role_farm, 
                                      mock_get_permissions):
        """
        Test de eliminación exitosa de transacción
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1  # Estado activo
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["delete_transaction", "read_transaction"]
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        content = response.body.decode()
        assert '"status":"success"' in content
        assert '"message":"Transacción eliminada correctamente"' in content
        assert '"transaction_id":1' in content
        
        # Verificar que se cambió el estado
        assert self.mock_transaction.transaction_state_id == self.mock_inactive_state.transaction_state_id
        self.mock_db.commit.assert_called_once()

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_database_error(self, mock_verify_token, mock_get_state, 
                                             mock_verify_plot, mock_get_user_role_farm, 
                                             mock_get_permissions):
        """
        Test cuando ocurre un error en la base de datos durante el commit
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["delete_transaction"]
        
        # Simular error en commit
        self.mock_db.commit.side_effect = Exception("Database connection error")
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 500
        content = response.body.decode()
        assert '"status":"error"' in content
        assert '"message":"Error al eliminar la transacción: Database connection error"' in content
        
        # Verificar rollback
        self.mock_db.rollback.assert_called_once()

    @patch('use_cases.delete_transaction_use_case.get_role_permissions_for_user_role')
    @patch('use_cases.delete_transaction_use_case.get_user_role_farm')
    @patch('use_cases.delete_transaction_use_case.verify_plot')
    @patch('use_cases.delete_transaction_use_case.get_transaction_state')
    @patch('use_cases.delete_transaction_use_case.verify_session_token')
    def test_delete_transaction_verify_all_calls(self, mock_verify_token, mock_get_state, 
                                                mock_verify_plot, mock_get_user_role_farm, 
                                                mock_get_permissions):
        """
        Test para verificar que se llaman todas las funciones con los parámetros correctos
        """
        # Arrange
        mock_verify_token.return_value = self.mock_user
        self.mock_transaction.transaction_state_id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_transaction
        mock_get_state.return_value = self.mock_inactive_state
        mock_verify_plot.return_value = self.mock_plot_info
        mock_get_user_role_farm.return_value = self.mock_user_role_farm
        mock_get_permissions.return_value = ["delete_transaction"]
        
        # Act
        response = delete_transaction_use_case(
            request=self.valid_request,
            session_token=self.valid_session_token,
            db=self.mock_db
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verificar todas las llamadas
        mock_verify_token.assert_called_once_with(self.valid_session_token)
        mock_get_state.assert_called_once_with(self.mock_db, "Inactivo")
        mock_verify_plot.assert_called_once_with(self.mock_transaction.plot_id)
        mock_get_user_role_farm.assert_called_once_with(self.mock_user.user_id, self.mock_plot_info.farm_id)
        mock_get_permissions.assert_called_once_with(self.mock_user_role_farm.user_role_id)

    def test_delete_transaction_request_validation(self):
        """
        Test de validación del request DeleteTransactionRequest
        """
        # Test con transaction_id válido
        valid_request = DeleteTransactionRequest(transaction_id=123)
        assert valid_request.transaction_id == 123
        
        # Test con transaction_id como string que no se puede convertir
        with pytest.raises(ValidationError):
            DeleteTransactionRequest(transaction_id="invalid")
            
        # Test sin transaction_id (debe fallar con ValidationError)
        with pytest.raises(ValidationError):
            DeleteTransactionRequest() 