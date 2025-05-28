"""
Tests para list_transaction_categories_use_case.py
"""
from unittest.mock import Mock

from domain.services.list_transaction_categories_service import list_transaction_categories_use_case
from models.models import TransactionCategories


class TestListTransactionCategoriesUseCase:
    """
    Tests para el caso de uso de listar categorías de transacción
    """
    
    def setup_method(self):
        """
        Configuración antes de cada test
        """
        # Mock database session
        self.mock_db = Mock()
        
        # Mock transaction type
        self.transaction_type = Mock()
        self.transaction_type.name = "Ingreso"
        
        # Mock transaction category
        self.transaction_category = Mock()
        self.transaction_category.transaction_category_id = 1
        self.transaction_category.name = "Venta de producto"
        self.transaction_category.transaction_type_id = 1
        self.transaction_category.transaction_type = self.transaction_type

    def test_successful_categories_listing(self):
        """
        Test del caso exitoso: listar categorías correctamente
        """
        # Arrange
        mock_query = Mock()
        mock_query.options.return_value.all.return_value = [self.transaction_category]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transaction_categories_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Categorías de transacción obtenidas correctamente" in response_data
        assert "transaction_categories" in response_data
        assert "Venta de producto" in response_data
        assert "Ingreso" in response_data
        
        # Verify database query was called correctly
        self.mock_db.query.assert_called_once_with(TransactionCategories)
        mock_query.options.assert_called_once()

    def test_empty_categories_list(self):
        """
        Test cuando no hay categorías en la base de datos
        """
        # Arrange
        mock_query = Mock()
        mock_query.options.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transaction_categories_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Categorías de transacción obtenidas correctamente" in response_data
        assert '"transaction_categories":[]' in response_data

    def test_categories_with_missing_transaction_type(self):
        """
        Test de categorías con tipo de transacción faltante
        """
        # Arrange
        category_without_type = Mock()
        category_without_type.transaction_category_id = 1
        category_without_type.name = "Categoría sin tipo"
        category_without_type.transaction_type_id = 1
        category_without_type.transaction_type = None
        
        mock_query = Mock()
        mock_query.options.return_value.all.return_value = [category_without_type]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transaction_categories_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Categorías de transacción obtenidas correctamente" in response_data
        assert "Categoría sin tipo" in response_data
        assert "Desconocido" in response_data  # Default value for missing type

    def test_multiple_categories_listing(self):
        """
        Test de listado de múltiples categorías
        """
        # Arrange
        type1 = Mock()
        type1.name = "Ingreso"
        
        type2 = Mock()
        type2.name = "Gasto"
        
        category1 = Mock()
        category1.transaction_category_id = 1
        category1.name = "Venta de producto"
        category1.transaction_type_id = 1
        category1.transaction_type = type1
        
        category2 = Mock()
        category2.transaction_category_id = 2
        category2.name = "Compra de insumos"
        category2.transaction_type_id = 2
        category2.transaction_type = type2
        
        mock_query = Mock()
        mock_query.options.return_value.all.return_value = [category1, category2]
        self.mock_db.query.return_value = mock_query
        
        # Act
        response = list_transaction_categories_use_case(db=self.mock_db)
        
        # Assert
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Categorías de transacción obtenidas correctamente" in response_data
        assert "Venta de producto" in response_data
        assert "Compra de insumos" in response_data
        assert "Ingreso" in response_data
        assert "Gasto" in response_data

    def test_database_query_with_joinedload(self):
        """
        Test que verifica que la consulta incluye joinedload para transaction_type
        """
        # Arrange
        mock_query = Mock()
        mock_options = Mock()
        
        self.mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_options
        mock_options.all.return_value = []
        
        # Act
        response = list_transaction_categories_use_case(db=self.mock_db)
        
        # Assert
        self.mock_db.query.assert_called_once_with(TransactionCategories)
        mock_query.options.assert_called_once()
        mock_options.all.assert_called_once()
        assert response.status_code == 200 