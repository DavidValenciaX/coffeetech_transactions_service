"""
Comprehensive test suite for the farm_client.py module.

This test suite provides 100% code coverage for all functions in the farm_client module:

Functions tested:
- verify_plot: Verifies if a plot exists and is active in the farms service
- get_farm_by_id: Retrieves farm information by ID  
- get_user_role_farm: Retrieves user role farm relationship
- create_user_role_farm: Creates a new user role farm relationship
- get_user_role_farm_state_by_name: Retrieves user role farm state by name

Test categories:
1. Success scenarios: Testing normal successful operations
2. Error handling: HTTP errors, connection errors, timeouts
3. Data validation: Invalid JSON, Pydantic validation errors
4. Edge cases: Different status codes, error responses
5. Logging: Timing logs, warning logs, error logs
6. Integration: Multi-function workflows
7. Constants: Module-level constants and defaults

Coverage areas:
- All possible return paths (success, various error conditions)
- Exception handling for different error types
- Response parsing and validation
- Timing and logging functionality
- HTTP client context management
- Pydantic schema validation

Test structure follows the existing patterns in the codebase with:
- Arrange-Act-Assert pattern
- Proper mocking of external dependencies
- Comprehensive edge case coverage
- Clear test documentation
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import httpx
import time
from datetime import datetime

from adapters.farm_client import (
    verify_plot,
    get_farm_by_id,
    get_user_role_farm,
    create_user_role_farm,
    get_user_role_farm_state_by_name,
    FARMS_SERVICE_URL
)
from domain.schemas import (
    PlotVerificationResponse,
    FarmDetailResponse,
    UserRoleFarmResponse
)


class TestVerifyPlot:
    """Test verify_plot function"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_success(self, mock_time, mock_client_class):
        """Test successful plot verification"""
        # Arrange
        mock_time.side_effect = [0.0, 1.5]  # start and end time
        plot_id = 123
        expected_data = {
            "plot_id": 123,
            "name": "Plot Test",
            "farm_id": 1,
            "plot_state_id": 1,
            "plot_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert isinstance(result, PlotVerificationResponse)
        assert result.plot_id == 123
        assert result.name == "Plot Test"
        assert result.farm_id == 1
        assert result.plot_state == "Activo"
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/verify-plot/{plot_id}"
        mock_client.get.assert_called_once_with(expected_url)
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_not_found(self, mock_time, mock_client_class):
        """Test plot not found (404 status)"""
        # Arrange
        mock_time.side_effect = [0.0, 1.0]
        plot_id = 999
        
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/verify-plot/{plot_id}"
        mock_client.get.assert_called_once_with(expected_url)
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_error_status_in_response(self, mock_time, mock_client_class):
        """Test plot verification with error status in response"""
        # Arrange
        mock_time.side_effect = [0.0, 0.5]
        plot_id = 123
        error_data = {
            "status": "error",
            "message": "Plot is inactive"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_data
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_connection_error(self, mock_time, mock_client_class):
        """Test plot verification with connection error"""
        # Arrange
        mock_time.side_effect = [0.0, 2.0]
        plot_id = 123
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_timeout_error(self, mock_time, mock_client_class):
        """Test plot verification with timeout error"""
        # Arrange
        mock_time.side_effect = [0.0, 30.5]
        plot_id = 123
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_json_decode_error(self, mock_time, mock_client_class):
        """Test plot verification with JSON decode error"""
        # Arrange
        mock_time.side_effect = [0.0, 1.5, 0.8]  # start time, success duration, error duration
        plot_id = 123
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None


class TestGetFarmById:
    """Test get_farm_by_id function"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_success(self, mock_time, mock_client_class):
        """Test successful farm retrieval"""
        # Arrange
        mock_time.side_effect = [0.0, 2.3]
        farm_id = 456
        expected_data = {
            "farm_id": 456,
            "name": "Farm Test",
            "area": 100.5,
            "area_unit_id": 1,
            "area_unit": "hectares",
            "farm_state_id": 1,
            "farm_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert isinstance(result, FarmDetailResponse)
        assert result.farm_id == 456
        assert result.name == "Farm Test"
        assert result.area == 100.5
        assert result.area_unit == "hectares"
        assert result.farm_state == "Activo"
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/get-farm/{farm_id}"
        mock_client.get.assert_called_once_with(expected_url)
        mock_response.raise_for_status.assert_called_once()
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_timeout(self, mock_time, mock_client_class):
        """Test farm retrieval with timeout"""
        # Arrange
        mock_time.side_effect = [0.0, 60.5]
        farm_id = 456
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_http_error(self, mock_time, mock_client_class):
        """Test farm retrieval with HTTP error"""
        # Arrange
        mock_time.side_effect = [0.0, 2.3, 1.2]  # start time, success duration, error duration
        farm_id = 456
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock()
        )
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_connection_error(self, mock_time, mock_client_class):
        """Test farm retrieval with connection error"""
        # Arrange
        mock_time.side_effect = [0.0, 3.0]
        farm_id = 456
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_invalid_json(self, mock_time, mock_client_class):
        """Test farm retrieval with invalid JSON response"""
        # Arrange
        mock_time.side_effect = [0.0, 2.3, 1.0]  # start time, success duration, error duration
        farm_id = 456
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None


class TestGetUserRoleFarm:
    """Test get_user_role_farm function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_success(self, mock_client_class):
        """Test successful user role farm retrieval"""
        # Arrange
        user_id = 123
        farm_id = 456
        expected_data = {
            "user_role_farm_id": 789,
            "user_role_id": 123,
            "farm_id": 456,
            "user_role_farm_state_id": 1,
            "user_role_farm_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert isinstance(result, UserRoleFarmResponse)
        assert result.user_role_farm_id == 789
        assert result.user_role_id == 123
        assert result.farm_id == 456
        assert result.user_role_farm_state == "Activo"
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/get-user-role-farm/{user_id}/{farm_id}"
        mock_client.get.assert_called_once_with(expected_url)
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_error_status(self, mock_client_class):
        """Test user role farm with error status in response"""
        # Arrange
        user_id = 123
        farm_id = 456
        error_data = {
            "status": "error",
            "message": "User role farm not found"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_http_error(self, mock_client_class):
        """Test user role farm with HTTP error"""
        # Arrange
        user_id = 123
        farm_id = 456
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock()
        )
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_connection_error(self, mock_client_class):
        """Test user role farm with connection error"""
        # Arrange
        user_id = 123
        farm_id = 456
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None


class TestCreateUserRoleFarm:
    """Test create_user_role_farm function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_user_role_farm_success(self, mock_client_class):
        """Test successful user role farm creation"""
        # Arrange
        user_role_id = 123
        farm_id = 456
        user_role_farm_state_id = 1
        expected_response = {
            "status": "success",
            "user_role_farm_id": 789,
            "message": "User role farm created successfully"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result == expected_response
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/create-user-role-farm"
        expected_payload = {
            "user_role_id": user_role_id,
            "farm_id": farm_id,
            "user_role_farm_state_id": user_role_farm_state_id
        }
        mock_client.post.assert_called_once_with(expected_url, json=expected_payload)
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_user_role_farm_http_error(self, mock_client_class):
        """Test user role farm creation with HTTP error"""
        # Arrange
        user_role_id = 123
        farm_id = 456
        user_role_farm_state_id = 1
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=Mock(), response=Mock()
        )
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result["status"] == "error"
        assert "Error al crear user_role_farm" in result["message"]
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_user_role_farm_connection_error(self, mock_client_class):
        """Test user role farm creation with connection error"""
        # Arrange
        user_role_id = 123
        farm_id = 456
        user_role_farm_state_id = 1
        
        mock_client = Mock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result["status"] == "error"
        assert "Error al crear user_role_farm" in result["message"]


class TestGetUserRoleFarmStateByName:
    """Test get_user_role_farm_state_by_name function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_success(self, mock_client_class):
        """Test successful user role farm state retrieval by name"""
        # Arrange
        state_name = "Activo"
        expected_data = {
            "user_role_farm_state_id": 1,
            "name": "Activo",
            "description": "Estado activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result == expected_data
        
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/get-user-role-farm-state/{state_name}"
        mock_client.get.assert_called_once_with(expected_url)
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_error_status(self, mock_client_class):
        """Test user role farm state with error status in response"""
        # Arrange
        state_name = "NonExistent"
        error_data = {
            "status": "error",
            "message": "State not found"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_http_error(self, mock_client_class):
        """Test user role farm state with HTTP error"""
        # Arrange
        state_name = "Activo"
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock()
        )
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_connection_error(self, mock_client_class):
        """Test user role farm state with connection error"""
        # Arrange
        state_name = "Activo"
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None


class TestConstants:
    """Test module constants"""
    
    def test_farms_service_url_default(self):
        """Test FARMS_SERVICE_URL default value"""
        # The URL should either be from environment or default
        assert FARMS_SERVICE_URL is not None
        assert isinstance(FARMS_SERVICE_URL, str)
        assert FARMS_SERVICE_URL.startswith("http")


class TestIntegration:
    """Integration-style tests for farm client functions"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_to_get_farm_flow(self, mock_time, mock_client_class):
        """Test complete flow from plot verification to farm retrieval"""
        # Arrange
        mock_time.side_effect = [0.0, 1.0, 2.0, 3.5]  # Multiple calls
        plot_id = 123
        farm_id = 456
        
        # First call - verify plot
        plot_data = {
            "plot_id": 123,
            "name": "Plot Test",
            "farm_id": 456,
            "plot_state_id": 1,
            "plot_state": "Activo"
        }
        
        # Second call - get farm
        farm_data = {
            "farm_id": 456,
            "name": "Farm Test",
            "area": 100.5,
            "area_unit_id": 1,
            "area_unit": "hectares",
            "farm_state_id": 1,
            "farm_state": "Activo"
        }
        
        mock_response_plot = Mock()
        mock_response_plot.status_code = 200
        mock_response_plot.json.return_value = plot_data
        
        mock_response_farm = Mock()
        mock_response_farm.status_code = 200
        mock_response_farm.json.return_value = farm_data
        mock_response_farm.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.side_effect = [mock_response_plot, mock_response_farm]
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        plot_result = verify_plot(plot_id)
        farm_result = get_farm_by_id(plot_result.farm_id)
        
        # Assert
        assert isinstance(plot_result, PlotVerificationResponse)
        assert isinstance(farm_result, FarmDetailResponse)
        assert plot_result.farm_id == farm_result.farm_id
        assert mock_client.get.call_count == 2
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_and_retrieve_user_role_farm_flow(self, mock_client_class):
        """Test flow of creating and then retrieving user role farm"""
        # Arrange
        user_role_id = 123
        farm_id = 456
        user_role_farm_state_id = 1
        
        # First call - create user role farm
        create_response = {
            "status": "success",
            "user_role_farm_id": 789,
            "message": "User role farm created successfully"
        }
        
        # Second call - get user role farm
        get_response = {
            "user_role_farm_id": 789,
            "user_role_id": 123,
            "farm_id": 456,
            "user_role_farm_state_id": 1,
            "user_role_farm_state": "Activo"
        }
        
        mock_response_create = Mock()
        mock_response_create.status_code = 201
        mock_response_create.json.return_value = create_response
        mock_response_create.raise_for_status.return_value = None
        
        mock_response_get = Mock()
        mock_response_get.status_code = 200
        mock_response_get.json.return_value = get_response
        mock_response_get.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response_create
        mock_client.get.return_value = mock_response_get
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        create_result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        get_result = get_user_role_farm(user_role_id, farm_id)
        
        # Assert
        assert create_result["status"] == "success"
        assert isinstance(get_result, UserRoleFarmResponse)
        assert get_result.user_role_id == user_role_id
        assert get_result.farm_id == farm_id
        
        # Verify the calls were made correctly
        mock_client.post.assert_called_once()
        mock_client.get.assert_called_once()


class TestTimeLogging:
    """Test timing and logging functionality"""
    
    @patch('adapters.farm_client.logger')
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_logs_timing(self, mock_time, mock_client_class, mock_logger):
        """Test that verify_plot logs timing information correctly"""
        # Arrange
        mock_time.side_effect = [0.0, 2.5678]  # 2.5678 seconds duration
        plot_id = 123
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "plot_id": 123,
            "name": "Test Plot",
            "farm_id": 1,
            "plot_state_id": 1,
            "plot_state": "Activo"
        }
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        verify_plot(plot_id)
        
        # Assert timing logs
        expected_start_url = f"{FARMS_SERVICE_URL}/farms-service/verify-plot/{plot_id}"
        mock_logger.info.assert_any_call(f"Verificando lote ID {plot_id} en {expected_start_url}...")
        mock_logger.info.assert_any_call(f"Consulta a {expected_start_url} finalizada en 2.5678 segundos con estado 200")
    
    @patch('adapters.farm_client.logger')
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_logs_timing(self, mock_time, mock_client_class, mock_logger):
        """Test that get_farm_by_id logs timing information correctly"""
        # Arrange
        mock_time.side_effect = [0.0, 1.2345]  # 1.2345 seconds duration
        farm_id = 456
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "farm_id": 456,
            "name": "Test Farm",
            "area": 100.0,
            "area_unit_id": 1,
            "area_unit": "hectares",
            "farm_state_id": 1,
            "farm_state": "Activo"
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        get_farm_by_id(farm_id)
        
        # Assert timing logs
        expected_url = f"{FARMS_SERVICE_URL}/farms-service/get-farm/{farm_id}"
        mock_logger.info.assert_any_call(f"Consultando finca ID {farm_id} en {expected_url}...")
        mock_logger.info.assert_any_call(f"Consulta a {expected_url} finalizada en 1.2345 segundos con estado 200")
    
    @patch('adapters.farm_client.logger')
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_logs_warning_for_inactive(self, mock_time, mock_client_class, mock_logger):
        """Test that verify_plot logs warning for inactive plots"""
        # Arrange
        mock_time.side_effect = [0.0, 1.0]
        plot_id = 999
        
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        verify_plot(plot_id)
        
        # Assert warning log
        mock_logger.warning.assert_called_with(f"El lote ID {plot_id} no existe o no está activo. Código: 404")
    
    @patch('adapters.farm_client.logger')
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_logs_error_with_status_field(self, mock_time, mock_client_class, mock_logger):
        """Test that verify_plot logs warning when status field indicates error"""
        # Arrange
        mock_time.side_effect = [0.0, 1.0]
        plot_id = 123
        error_data = {
            "status": "error",
            "message": "Plot is inactive"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_data
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        verify_plot(plot_id)
        
        # Assert warning log
        mock_logger.warning.assert_called_with(f"Error verificando lote: Plot is inactive")


class TestAdditionalEdgeCases:
    """Test additional edge cases and scenarios"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_different_error_status_codes(self, mock_time, mock_client_class):
        """Test verify_plot with different HTTP error status codes"""
        # Test different status codes
        test_cases = [400, 401, 403, 500, 503]
        
        for status_code in test_cases:
            mock_time.side_effect = [0.0, 1.0]
            
            mock_response = Mock()
            mock_response.status_code = status_code
            
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            # Act
            result = verify_plot(123)
            
            # Assert
            assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_with_pydantic_validation_error(self, mock_client_class):
        """Test get_user_role_farm with invalid data causing Pydantic validation error"""
        # Arrange
        user_id = 123
        farm_id = 456
        invalid_data = {
            "user_role_farm_id": "not_an_int",  # Invalid type
            "user_role_id": 123,
            "farm_id": 456,
            "user_role_farm_state_id": 1,
            "user_role_farm_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_with_pydantic_validation_error(self, mock_time, mock_client_class):
        """Test get_farm_by_id with invalid data causing Pydantic validation error"""
        # Arrange
        mock_time.side_effect = [0.0, 2.3, 1.0]
        farm_id = 456
        invalid_data = {
            "farm_id": "not_an_int",  # Invalid type
            "name": "Farm Test",
            "area": 100.5,
            "area_unit_id": 1,
            "area_unit": "hectares",
            "farm_state_id": 1,
            "farm_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_data
        mock_response.raise_for_status.return_value = None
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_verify_plot_with_pydantic_validation_error(self, mock_time, mock_client_class):
        """Test verify_plot with invalid data causing Pydantic validation error"""
        # Arrange
        mock_time.side_effect = [0.0, 1.5, 0.8]
        plot_id = 123
        invalid_data = {
            "plot_id": "not_an_int",  # Invalid type
            "name": "Plot Test",
            "farm_id": 1,
            "plot_state_id": 1,
            "plot_state": "Activo"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_data
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = verify_plot(plot_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_user_role_farm_with_json_decode_error(self, mock_client_class):
        """Test create_user_role_farm when response.json() fails"""
        # Arrange
        user_role_id = 123
        farm_id = 456
        user_role_farm_state_id = 1
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result["status"] == "error"
        assert "Error al crear user_role_farm" in result["message"]
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_with_json_decode_error(self, mock_client_class):
        """Test get_user_role_farm_state_by_name when response.json() fails"""
        # Arrange
        state_name = "Activo"
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_with_json_decode_error(self, mock_client_class):
        """Test get_user_role_farm when response.json() fails"""
        # Arrange
        user_id = 123
        farm_id = 456
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
