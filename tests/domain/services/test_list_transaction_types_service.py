"""
Tests para list_transaction_types_use_case.py

Este módulo contiene tests exhaustivos para el caso de uso list_transaction_types_use_case,
que se encarga de listar todos los tipos de transacción disponibles en el sistema.

Tests incluidos:
- test_successful_transaction_types_listing: Test del caso exitoso básico
- test_empty_transaction_types_list: Test cuando no hay tipos de transacción
- test_single_transaction_type_listing: Test con un solo tipo de transacción
- test_multiple_transaction_types_with_different_ids: Test con múltiples tipos y diferentes IDs
- test_transaction_types_with_special_characters: Test con caracteres especiales en nombres
- test_database_session_interaction: Test de interacción correcta con la base de datos
- test_response_structure_validation: Test de validación de estructura de respuesta
- test_large_number_of_transaction_types: Test de manejo de gran cantidad de tipos
- test_none_database_session_handling: Test de manejo de sesión nula

Cobertura: 100% del código del use case
"""
from unittest.mock import Mock
import pytest
import json

from domain.services.list_transaction_types_service import list_transaction_types_use_case
from models.models import TransactionTypes


class TestListTransactionTypesUseCase:
    """
    Tests para el caso de uso de listar tipos de transacción
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        # Mock database session
        self.mock_db = Mock()
        
        # Mock transaction type 1
        self.transaction_type1 = Mock()
        self.transaction_type1.transaction_type_id = 1
        self.transaction_type1.name = "Ingreso"
        
        # Mock transaction type 2
        self.transaction_type2 = Mock()
        self.transaction_type2.transaction_type_id = 2
        self.transaction_type2.name = "Gasto"

    def test_successful_transaction_types_listing(self):
        """
        Test del caso exitoso: listar tipos de transacción correctamente
        """
        # Arrange
        self.mock_db.query.return_value.all.return_value = [self.transaction_type1, self.transaction_type2]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        assert response_json["status"] == "success"
        assert response_json["message"] == "Tipos de transacción obtenidos correctamente"
        assert "transaction_types" in response_json["data"]
        
        transaction_types = response_json["data"]["transaction_types"]
        assert len(transaction_types) == 2
        
        # Verificar primer tipo de transacción
        assert transaction_types[0]["transaction_type_id"] == 1
        assert transaction_types[0]["name"] == "Ingreso"
        
        # Verificar segundo tipo de transacción
        assert transaction_types[1]["transaction_type_id"] == 2
        assert transaction_types[1]["name"] == "Gasto"
        
        # Verify database query was called correctly
        self.mock_db.query.assert_called_once_with(TransactionTypes)

    def test_empty_transaction_types_list(self):
        """
        Test cuando no hay tipos de transacción en la base de datos
        """
        # Arrange
        self.mock_db.query.return_value.all.return_value = []
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        assert response_json["status"] == "success"
        assert response_json["message"] == "Tipos de transacción obtenidos correctamente"
        assert response_json["data"]["transaction_types"] == []
        
        # Verify database query was called correctly
        self.mock_db.query.assert_called_once_with(TransactionTypes)

    def test_single_transaction_type_listing(self):
        """
        Test de listado de un solo tipo de transacción
        """
        # Arrange
        self.mock_db.query.return_value.all.return_value = [self.transaction_type1]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        assert response_json["status"] == "success"
        assert response_json["message"] == "Tipos de transacción obtenidos correctamente"
        
        transaction_types = response_json["data"]["transaction_types"]
        assert len(transaction_types) == 1
        assert transaction_types[0]["transaction_type_id"] == 1
        assert transaction_types[0]["name"] == "Ingreso"

    def test_multiple_transaction_types_with_different_ids(self):
        """
        Test de listado de múltiples tipos de transacción con diferentes IDs
        """
        # Arrange
        type3 = Mock()
        type3.transaction_type_id = 10
        type3.name = "Transferencia"
        
        type4 = Mock()
        type4.transaction_type_id = 25
        type4.name = "Inversión"
        
        self.mock_db.query.return_value.all.return_value = [type3, type4, self.transaction_type1]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        transaction_types = response_json["data"]["transaction_types"]
        assert len(transaction_types) == 3
        
        # Verificar que todos los tipos están presentes
        type_ids = [tt["transaction_type_id"] for tt in transaction_types]
        type_names = [tt["name"] for tt in transaction_types]
        
        assert 10 in type_ids
        assert 25 in type_ids
        assert 1 in type_ids
        assert "Transferencia" in type_names
        assert "Inversión" in type_names
        assert "Ingreso" in type_names

    def test_transaction_types_with_special_characters(self):
        """
        Test de tipos de transacción con caracteres especiales en el nombre
        """
        # Arrange
        special_type = Mock()
        special_type.transaction_type_id = 100
        special_type.name = "Préstamo & Financiamiento"
        
        unicode_type = Mock()
        unicode_type.transaction_type_id = 101
        unicode_type.name = "Inversión en Tecnología"
        
        self.mock_db.query.return_value.all.return_value = [special_type, unicode_type]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        transaction_types = response_json["data"]["transaction_types"]
        assert len(transaction_types) == 2
        
        assert transaction_types[0]["name"] == "Préstamo & Financiamiento"
        assert transaction_types[1]["name"] == "Inversión en Tecnología"

    def test_database_session_interaction(self):
        """
        Test que verifica la correcta interacción con la sesión de base de datos
        """
        # Arrange
        mock_query = Mock()
        self.mock_db.query.return_value = mock_query
        mock_query.all.return_value = [self.transaction_type1]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        # Verificar que se llamó a query con el modelo correcto
        self.mock_db.query.assert_called_once_with(TransactionTypes)
        # Verificar que se llamó a all() en el resultado de query
        mock_query.all.assert_called_once()
        assert response.status_code == 200

    def test_response_structure_validation(self):
        """
        Test que valida la estructura de la respuesta
        """
        # Arrange
        self.mock_db.query.return_value.all.return_value = [self.transaction_type1]
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        # Verificar estructura principal de la respuesta
        assert "status" in response_json
        assert "message" in response_json
        assert "data" in response_json
        
        # Verificar estructura de data
        assert "transaction_types" in response_json["data"]
        assert isinstance(response_json["data"]["transaction_types"], list)
        
        # Verificar estructura de cada transaction type
        if response_json["data"]["transaction_types"]:
            transaction_type = response_json["data"]["transaction_types"][0]
            assert "transaction_type_id" in transaction_type
            assert "name" in transaction_type
            assert isinstance(transaction_type["transaction_type_id"], int)
            assert isinstance(transaction_type["name"], str)

    def test_large_number_of_transaction_types(self):
        """
        Test de manejo de un gran número de tipos de transacción
        """
        # Arrange
        large_list = []
        for i in range(100):
            mock_type = Mock()
            mock_type.transaction_type_id = i + 1
            mock_type.name = f"Tipo de Transacción {i + 1}"
            large_list.append(mock_type)
        
        self.mock_db.query.return_value.all.return_value = large_list
        
        # Act
        response = list_transaction_types_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        response_json = json.loads(response_data)
        
        transaction_types = response_json["data"]["transaction_types"]
        assert len(transaction_types) == 100
        
        # Verificar algunos elementos específicos
        assert transaction_types[0]["transaction_type_id"] == 1
        assert transaction_types[0]["name"] == "Tipo de Transacción 1"
        assert transaction_types[99]["transaction_type_id"] == 100
        assert transaction_types[99]["name"] == "Tipo de Transacción 100"

    def test_none_database_session_handling(self):
        """
        Test de manejo cuando la sesión de base de datos es None
        """
        # Act & Assert
        with pytest.raises(AttributeError):
            list_transaction_types_use_case(db=None) 