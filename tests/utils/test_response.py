"""
Tests para utils/response.py

Este módulo contiene tests para las funciones utilitarias de respuesta:
- process_data_for_json
- create_response
- session_token_invalid_response
"""
import pytest
from datetime import datetime, date, time
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel
from fastapi.responses import ORJSONResponse
import json

from utils.response import process_data_for_json, create_response, session_token_invalid_response


class SampleModel(BaseModel):
    """Modelo de prueba para testing"""
    id: int
    name: str


class TestProcessDataForJson:
    """Tests para la función process_data_for_json"""
    
    def test_process_basemodel(self):
        """Test procesamiento de BaseModel"""
        model = SampleModel(id=1, name="Test")
        result = process_data_for_json(model)
        assert result == {"id": 1, "name": "Test"}
    
    def test_process_decimal(self):
        """Test procesamiento de Decimal"""
        decimal_value = Decimal("123.45")
        result = process_data_for_json(decimal_value)
        assert result == 123.45
        assert isinstance(result, float)
    
    def test_process_datetime(self):
        """Test procesamiento de datetime"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = process_data_for_json(dt)
        assert result == "2024-01-15T10:30:45"
    
    def test_process_date(self):
        """Test procesamiento de date"""
        d = date(2024, 1, 15)
        result = process_data_for_json(d)
        assert result == "2024-01-15"
    
    def test_process_time(self):
        """Test procesamiento de time"""
        t = time(10, 30, 45)
        result = process_data_for_json(t)
        assert result == "10:30:45"
    
    def test_process_uuid(self):
        """Test procesamiento de UUID"""
        uuid_value = UUID("12345678-1234-5678-1234-567812345678")
        result = process_data_for_json(uuid_value)
        assert result == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result, str)
    
    def test_process_dict(self):
        """Test procesamiento de diccionario con tipos especiales"""
        data = {
            "decimal": Decimal("123.45"),
            "datetime": datetime(2024, 1, 15),
            "model": SampleModel(id=1, name="Test")
        }
        result = process_data_for_json(data)
        expected = {
            "decimal": 123.45,
            "datetime": "2024-01-15T00:00:00",
            "model": {"id": 1, "name": "Test"}
        }
        assert result == expected
    
    def test_process_list(self):
        """Test procesamiento de lista con tipos especiales"""
        data = [
            Decimal("123.45"),
            datetime(2024, 1, 15),
            SampleModel(id=1, name="Test")
        ]
        result = process_data_for_json(data)
        expected = [
            123.45,
            "2024-01-15T00:00:00",
            {"id": 1, "name": "Test"}
        ]
        assert result == expected
    
    def test_process_tuple(self):
        """Test procesamiento de tupla"""
        data = (Decimal("123.45"), "normal_string")
        result = process_data_for_json(data)
        expected = [123.45, "normal_string"]
        assert result == expected
    
    def test_process_set(self):
        """Test procesamiento de set"""
        data = {1, 2, 3}
        result = process_data_for_json(data)
        assert isinstance(result, list)
        assert set(result) == {1, 2, 3}
    
    def test_process_nested_collections(self):
        """Test procesamiento de colecciones anidadas"""
        data = {
            "list": [
                {"decimal": Decimal("123.45")},
                {"datetime": datetime(2024, 1, 15)}
            ],
            "dict": {
                "nested": {"uuid": UUID("12345678-1234-5678-1234-567812345678")}
            }
        }
        result = process_data_for_json(data)
        expected = {
            "list": [
                {"decimal": 123.45},
                {"datetime": "2024-01-15T00:00:00"}
            ],
            "dict": {
                "nested": {"uuid": "12345678-1234-5678-1234-567812345678"}
            }
        }
        assert result == expected
    
    def test_process_regular_types(self):
        """Test que tipos regulares no se modifican"""
        regular_data = {"string": "test", "int": 123, "float": 45.67, "bool": True, "none": None}
        result = process_data_for_json(regular_data)
        assert result == regular_data


class TestCreateResponse:
    """Tests para la función create_response"""
    
    def test_create_response_success_without_data(self):
        """Test crear respuesta exitosa sin datos"""
        response = create_response("success", "Operation completed")
        
        assert isinstance(response, ORJSONResponse)
        assert response.status_code == 200
        
        # Verificar contenido
        content = json.loads(response.body.decode())
        assert content["status"] == "success"
        assert content["message"] == "Operation completed"
        assert content["data"] == {}
    
    def test_create_response_success_with_data(self):
        """Test crear respuesta exitosa con datos"""
        data = {"result": "test_data", "count": 5}
        response = create_response("success", "Data retrieved", data)
        
        assert isinstance(response, ORJSONResponse)
        assert response.status_code == 200
        
        content = json.loads(response.body.decode())
        assert content["status"] == "success"
        assert content["message"] == "Data retrieved"
        assert content["data"] == data
    
    def test_create_response_error(self):
        """Test crear respuesta de error"""
        response = create_response("error", "Something went wrong", status_code=400)
        
        assert isinstance(response, ORJSONResponse)
        assert response.status_code == 400
        
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["message"] == "Something went wrong"
        assert content["data"] == {}
    
    def test_create_response_with_special_types(self):
        """Test crear respuesta con tipos especiales que requieren procesamiento"""
        data = {
            "decimal": Decimal("123.45"),
            "datetime": datetime(2024, 1, 15, 10, 30),
            "model": SampleModel(id=1, name="Test")
        }
        response = create_response("success", "Special data", data)
        
        content = json.loads(response.body.decode())
        expected_data = {
            "decimal": 123.45,
            "datetime": "2024-01-15T10:30:00",
            "model": {"id": 1, "name": "Test"}
        }
        assert content["data"] == expected_data
    
    def test_create_response_with_none_data(self):
        """Test crear respuesta cuando data es None"""
        response = create_response("success", "No data", data=None)
        
        content = json.loads(response.body.decode())
        assert content["data"] == {}
    
    def test_create_response_custom_status_code(self):
        """Test crear respuesta con código de estado personalizado"""
        response = create_response("success", "Created", status_code=201)
        assert response.status_code == 201


class TestSessionTokenInvalidResponse:
    """Tests para la función session_token_invalid_response"""
    
    def test_session_token_invalid_response(self):
        """Test crear respuesta para token inválido"""
        response = session_token_invalid_response()
        
        assert isinstance(response, ORJSONResponse)
        assert response.status_code == 401
        
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["message"] == "Credenciales expiradas, cerrando sesión."
        assert content["data"] == {}
    
    def test_session_token_invalid_response_structure(self):
        """Test estructura completa de respuesta de token inválido"""
        response = session_token_invalid_response()
        content = json.loads(response.body.decode())
        
        # Verificar que tiene todas las claves requeridas
        required_keys = ["status", "message", "data"]
        for key in required_keys:
            assert key in content
        
        # Verificar tipos
        assert isinstance(content["status"], str)
        assert isinstance(content["message"], str)
        assert isinstance(content["data"], dict) 