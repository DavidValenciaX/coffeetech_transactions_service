import pytest
from unittest.mock import patch, Mock, MagicMock
import httpx
from typing import Dict, Any

from adapters.user_client import (
    _make_request,
    get_role_name_for_user_role,
    get_user_role_ids,
    verify_session_token,
    user_verification_by_email,
    create_user_role,
    get_role_permissions_for_user_role,
    get_role_name_by_id,
    update_user_role,
    get_collaborators_info,
    delete_user_role,
    get_user_by_id,
    UserServiceError,
    UserServiceConnectionError,
    UserServiceResponseError,
    UserRoleNotFoundError,
    UserNotFoundError,
    RoleCreationError,
    RoleUpdateError,
    RoleDeletionError,
    CollaboratorInfoError,
    USER_SERVICE_URL,
    DEFAULT_TIMEOUT
)
from domain.schemas import UserResponse


class TestExceptions:
    """Test custom exception classes"""
    
    def test_user_service_error_inheritance(self):
        """Test that all custom exceptions inherit from UserServiceError"""
        assert issubclass(UserServiceConnectionError, UserServiceError)
        assert issubclass(UserServiceResponseError, UserServiceError)
        assert issubclass(UserRoleNotFoundError, UserServiceError)
        assert issubclass(UserNotFoundError, UserServiceError)
        assert issubclass(RoleCreationError, UserServiceError)
        assert issubclass(RoleUpdateError, UserServiceError)
        assert issubclass(RoleDeletionError, UserServiceError)
        assert issubclass(CollaboratorInfoError, UserServiceError)


class TestMakeRequest:
    """Test the _make_request base function"""
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_get_success(self, mock_client_class):
        """Test successful GET request"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = _make_request("/test-endpoint", method="GET", params={"param": "value"})
        
        # Assert
        assert result == {"test": "data"}
        mock_client.get.assert_called_once_with(f"{USER_SERVICE_URL}/test-endpoint", params={"param": "value"})
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_post_success(self, mock_client_class):
        """Test successful POST request"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": "data"}
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = _make_request("/test-endpoint", method="POST", data={"key": "value"})
        
        # Assert
        assert result == {"created": "data"}
        mock_client.post.assert_called_once_with(f"{USER_SERVICE_URL}/test-endpoint", json={"key": "value"})
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_unsupported_method(self, mock_client_class):
        """Test unsupported HTTP method"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = _make_request("/test-endpoint", method="PUT")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_error_status_code(self, mock_client_class):
        """Test request with error status code"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = _make_request("/test-endpoint")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_connection_error(self, mock_client_class):
        """Test connection error handling"""
        # Arrange
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(UserServiceConnectionError) as exc_info:
            _make_request("/test-endpoint")
        
        assert "Unable to connect to user service" in str(exc_info.value)
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_timeout_error(self, mock_client_class):
        """Test timeout error handling"""
        # Arrange
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(UserServiceConnectionError) as exc_info:
            _make_request("/test-endpoint")
        
        assert "Unable to connect to user service" in str(exc_info.value)
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_unexpected_error(self, mock_client_class):
        """Test unexpected error handling"""
        # Arrange
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Unexpected error")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(UserServiceConnectionError) as exc_info:
            _make_request("/test-endpoint")
        
        assert "Unexpected error connecting to user service" in str(exc_info.value)


class TestGetRoleNameForUserRole:
    """Test get_role_name_for_user_role function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_success(self, mock_make_request):
        """Test successful role name retrieval"""
        # Arrange
        mock_make_request.return_value = {"role_name": "Administrator"}
        
        # Act
        result = get_role_name_for_user_role(123)
        
        # Assert
        assert result == "Administrator"
        mock_make_request.assert_called_once_with("/users-service/user-role/123")
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_no_role_name_in_response(self, mock_make_request):
        """Test when role_name is not in response"""
        # Arrange
        mock_make_request.return_value = {"other_field": "value"}
        
        # Act
        result = get_role_name_for_user_role(123)
        
        # Assert
        assert result == "Unknown"
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_none_response(self, mock_make_request):
        """Test when response is None"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_role_name_for_user_role(123)
        
        # Assert
        assert result == "Unknown"


class TestGetUserRoleIds:
    """Test get_user_role_ids function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_user_role_ids_success(self, mock_make_request):
        """Test successful user role IDs retrieval"""
        # Arrange
        mock_make_request.return_value = {"user_role_ids": [1, 2, 3]}
        
        # Act
        result = get_user_role_ids(456)
        
        # Assert
        assert result == [1, 2, 3]
        mock_make_request.assert_called_once_with("/users-service/user-role-ids/456")
    
    @patch('adapters.user_client._make_request')
    def test_get_user_role_ids_empty_list(self, mock_make_request):
        """Test when user_role_ids is empty"""
        # Arrange
        mock_make_request.return_value = {"user_role_ids": []}
        
        # Act
        result = get_user_role_ids(456)
        
        # Assert
        assert result == []
    
    @patch('adapters.user_client._make_request')
    def test_get_user_role_ids_no_user_role_ids_in_response(self, mock_make_request):
        """Test when user_role_ids is not in response"""
        # Arrange
        mock_make_request.return_value = {"other_field": "value"}
        
        # Act
        result = get_user_role_ids(456)
        
        # Assert
        assert result == []
    
    @patch('adapters.user_client._make_request')
    def test_get_user_role_ids_none_response(self, mock_make_request):
        """Test when response is None"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(UserRoleNotFoundError) as exc_info:
            get_user_role_ids(456)
        
        assert "Error retrieving user_role_ids for user 456" in str(exc_info.value)


class TestVerifySessionToken:
    """Test verify_session_token function"""
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_success(self, mock_make_request):
        """Test successful session token verification"""
        # Arrange
        user_data = {
            "user_id": 1,
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_make_request.return_value = {
            "status": "success",
            "data": {"user": user_data}
        }
        
        # Act
        result = verify_session_token("valid_token")
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.user_id == 1
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        mock_make_request.assert_called_once_with(
            "/users-service/session-token-verification",
            method="POST",
            data={"session_token": "valid_token"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_invalid_status(self, mock_make_request):
        """Test session token verification with invalid status"""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "Invalid token"
        }
        
        # Act
        result = verify_session_token("invalid_token")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_no_user_in_data(self, mock_make_request):
        """Test session token verification with no user in data"""
        # Arrange
        mock_make_request.return_value = {
            "status": "success",
            "data": {"other_field": "value"}
        }
        
        # Act
        result = verify_session_token("token")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_none_response(self, mock_make_request):
        """Test session token verification with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = verify_session_token("token")
        
        # Assert
        assert result is None


class TestUserVerificationByEmail:
    """Test user_verification_by_email function"""
    
    @patch('adapters.user_client._make_request')
    def test_user_verification_by_email_success(self, mock_make_request):
        """Test successful user verification by email"""
        # Arrange
        user_data = {
            "user_id": 1,
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_make_request.return_value = {
            "status": "success",
            "data": {"user": user_data}
        }
        
        # Act
        result = user_verification_by_email("test@example.com")
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
        mock_make_request.assert_called_once_with(
            "/users-service/user-verification-by-email",
            method="POST",
            data={"email": "test@example.com"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_user_verification_by_email_not_found(self, mock_make_request):
        """Test user verification by email when user not found"""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "User not found"
        }
        
        # Act
        result = user_verification_by_email("notfound@example.com")
        
        # Assert
        assert result is None


class TestCreateUserRole:
    """Test create_user_role function"""
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_success(self, mock_make_request):
        """Test successful user role creation"""
        # Arrange
        mock_make_request.return_value = {"user_role_id": 123}
        
        # Act
        result = create_user_role(1, "Administrator")
        
        # Assert
        assert result == {"user_role_id": 123}
        mock_make_request.assert_called_once_with(
            "/users-service/user-role",
            method="POST",
            data={"user_id": 1, "role_name": "Administrator"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_failure(self, mock_make_request):
        """Test user role creation failure"""
        # Arrange
        mock_make_request.return_value = {"error": "Role creation failed"}
        
        # Act & Assert
        with pytest.raises(RoleCreationError) as exc_info:
            create_user_role(1, "InvalidRole")
        
        assert "Error creating user_role for user 1 with role 'InvalidRole'" in str(exc_info.value)
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_none_response(self, mock_make_request):
        """Test user role creation with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(RoleCreationError):
            create_user_role(1, "Administrator")


class TestGetRolePermissionsForUserRole:
    """Test get_role_permissions_for_user_role function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_success(self, mock_make_request):
        """Test successful role permissions retrieval"""
        # Arrange
        mock_make_request.return_value = {
            "permissions": [
                {"name": "read"},
                {"name": "write"},
                {"name": "delete"}
            ]
        }
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == ["read", "write", "delete"]
        mock_make_request.assert_called_once_with("/users-service/user-role/123/permissions")
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_no_permissions(self, mock_make_request):
        """Test when no permissions in response"""
        # Arrange
        mock_make_request.return_value = {"other_field": "value"}
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == []
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_none_response(self, mock_make_request):
        """Test when response is None"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == []


class TestGetRoleNameById:
    """Test get_role_name_by_id function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_by_id_success(self, mock_make_request):
        """Test successful role name retrieval by ID"""
        # Arrange
        mock_make_request.return_value = {"role_name": "Administrator"}
        
        # Act
        result = get_role_name_by_id(1)
        
        # Assert
        assert result == "Administrator"
        mock_make_request.assert_called_once_with("/users-service/1/name")
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_by_id_not_found(self, mock_make_request):
        """Test when role name not found"""
        # Arrange
        mock_make_request.return_value = {"error": "Role not found"}
        
        # Act
        result = get_role_name_by_id(999)
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_by_id_none_response(self, mock_make_request):
        """Test when response is None"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_role_name_by_id(1)
        
        # Assert
        assert result is None


class TestUpdateUserRole:
    """Test update_user_role function"""
    
    @patch('adapters.user_client._make_request')
    def test_update_user_role_success(self, mock_make_request):
        """Test successful user role update"""
        # Arrange
        mock_make_request.return_value = {"status": "success"}
        
        # Act
        update_user_role(123, 2)
        
        # Assert
        mock_make_request.assert_called_once_with(
            "/users-service/user-role/123/update-role",
            method="POST",
            data={"new_role_id": 2}
        )
    
    @patch('adapters.user_client._make_request')
    def test_update_user_role_failure(self, mock_make_request):
        """Test user role update failure"""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "Role update failed"
        }
        
        # Act & Assert
        with pytest.raises(RoleUpdateError) as exc_info:
            update_user_role(123, 2)
        
        assert "No se pudo actualizar el rol del user_role_id 123 al role_id 2" in str(exc_info.value)
        assert "Role update failed" in str(exc_info.value)
    
    @patch('adapters.user_client._make_request')
    def test_update_user_role_none_response(self, mock_make_request):
        """Test user role update with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(RoleUpdateError) as exc_info:
            update_user_role(123, 2)
        
        assert "No response" in str(exc_info.value)


class TestGetCollaboratorsInfo:
    """Test get_collaborators_info function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_collaborators_info_success(self, mock_make_request):
        """Test successful collaborators info retrieval"""
        # Arrange
        collaborators_data = [
            {"user_id": 1, "name": "User 1", "role": "Administrator"},
            {"user_id": 2, "name": "User 2", "role": "Manager"}
        ]
        mock_make_request.return_value = {"collaborators": collaborators_data}
        
        # Act
        result = get_collaborators_info([1, 2, 3])
        
        # Assert
        assert result == collaborators_data
        mock_make_request.assert_called_once_with(
            "/users-service/user-role/bulk-info",
            method="POST",
            data={"user_role_ids": [1, 2, 3]}
        )
    
    @patch('adapters.user_client._make_request')
    def test_get_collaborators_info_failure(self, mock_make_request):
        """Test collaborators info retrieval failure"""
        # Arrange
        mock_make_request.return_value = {"error": "Failed to retrieve collaborators"}
        
        # Act & Assert
        with pytest.raises(CollaboratorInfoError) as exc_info:
            get_collaborators_info([1, 2, 3])
        
        assert "No se pudo obtener la información de los colaboradores" in str(exc_info.value)
    
    @patch('adapters.user_client._make_request')
    def test_get_collaborators_info_none_response(self, mock_make_request):
        """Test collaborators info retrieval with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(CollaboratorInfoError):
            get_collaborators_info([1, 2, 3])


class TestDeleteUserRole:
    """Test delete_user_role function"""
    
    @patch('adapters.user_client._make_request')
    def test_delete_user_role_success(self, mock_make_request):
        """Test successful user role deletion"""
        # Arrange
        mock_make_request.return_value = {"status": "success"}
        
        # Act
        delete_user_role(123)
        
        # Assert
        mock_make_request.assert_called_once_with(
            "/users-service/user-role/123/delete",
            method="POST"
        )
    
    @patch('adapters.user_client._make_request')
    def test_delete_user_role_failure(self, mock_make_request):
        """Test user role deletion failure"""
        # Arrange
        mock_make_request.return_value = {"status": "error", "message": "Deletion failed"}
        
        # Act & Assert
        with pytest.raises(RoleDeletionError) as exc_info:
            delete_user_role(123)
        
        assert "No se pudo eliminar el user_role_id 123" in str(exc_info.value)
    
    @patch('adapters.user_client._make_request')
    def test_delete_user_role_none_response(self, mock_make_request):
        """Test user role deletion with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(RoleDeletionError):
            delete_user_role(123)


class TestGetUserById:
    """Test get_user_by_id function"""
    
    @patch('adapters.user_client._make_request')
    def test_get_user_by_id_success(self, mock_make_request):
        """Test successful user retrieval by ID"""
        # Arrange
        user_data = {
            "user_id": 1,
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_make_request.return_value = {
            "status": "success",
            "data": {"user": user_data}
        }
        
        # Act
        result = get_user_by_id(1)
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.user_id == 1
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        mock_make_request.assert_called_once_with("/users-service/user/1")
    
    @patch('adapters.user_client._make_request')
    def test_get_user_by_id_not_found(self, mock_make_request):
        """Test user retrieval when user not found"""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "User not found"
        }
        
        # Act
        result = get_user_by_id(999)
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_get_user_by_id_none_response(self, mock_make_request):
        """Test user retrieval with None response"""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_user_by_id(1)
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_get_user_by_id_no_user_in_data(self, mock_make_request):
        """Test user retrieval with no user in data"""
        # Arrange
        mock_make_request.return_value = {
            "status": "success",
            "data": {"other_field": "value"}
        }
        
        # Act
        result = get_user_by_id(1)
        
        # Assert
        assert result is None


class TestConstants:
    """Test module constants"""
    
    def test_user_service_url_default(self):
        """Test USER_SERVICE_URL default value"""
        # This test would need to be adjusted based on actual environment
        assert USER_SERVICE_URL is not None
    
    def test_default_timeout(self):
        """Test DEFAULT_TIMEOUT value"""
        assert abs(DEFAULT_TIMEOUT - 10.0) < 1e-9


# Integration test class for testing with actual HTTP mocking
class TestIntegration:
    """Integration tests with more realistic scenarios"""
    
    @patch('adapters.user_client.httpx.Client')
    def test_full_session_token_verification_flow(self, mock_client_class):
        """Test complete session token verification flow"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "user": {
                    "user_id": 1,
                    "name": "Integration Test User",
                    "email": "integration@test.com"
                }
            }
        }
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_session_token("integration_test_token")
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.user_id == 1
        assert result.name == "Integration Test User"
        assert result.email == "integration@test.com"
        
        # Verify the actual HTTP call
        mock_client.post.assert_called_once_with(
            f"{USER_SERVICE_URL}/users-service/session-token-verification",
            json={"session_token": "integration_test_token"}
        )


if __name__ == "__main__":
    pytest.main([__file__])
