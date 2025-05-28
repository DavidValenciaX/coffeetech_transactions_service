"""
Tests para generate_financial_report_use_case.py
"""
import pytest
from unittest.mock import Mock, patch
from datetime import date
from decimal import Decimal
from collections import defaultdict

from use_cases.generate_financial_report_use_case import (
    generate_financial_report,
    _validate_and_get_plots,
    _validate_user_permissions,
    _get_transactions_and_categories,
    _process_transaction,
    _build_plot_financials_list,
    _build_transaction_history
)
from domain.schemas import (
    FinancialReportRequest,
    FinancialCategoryBreakdown,
    PlotFinancialData,
    FarmFinancialSummary,
    TransactionHistoryItem,
    FinancialReportResponse,
    UserResponse,
    FarmDetailResponse,
    UserRoleFarmResponse,
    PlotVerificationResponse
)


class TestValidateAndGetPlots:
    """Tests para _validate_and_get_plots"""
    
    @patch('use_cases.generate_financial_report_use_case.verify_plot')
    def test_validate_and_get_plots_success(self, mock_verify_plot):
        """Test successful plot validation"""
        # Arrange
        mock_plot1 = Mock()
        mock_plot1.plot_id = 1
        mock_plot1.name = "Lote 1"
        mock_plot1.farm_id = 100
        
        mock_plot2 = Mock()
        mock_plot2.plot_id = 2
        mock_plot2.name = "Lote 2"
        mock_plot2.farm_id = 100
        
        mock_verify_plot.side_effect = [mock_plot1, mock_plot2]
        
        # Act
        plots, plot_names, farm_id = _validate_and_get_plots([1, 2])
        
        # Assert
        assert len(plots) == 2
        assert plot_names == {1: "Lote 1", 2: "Lote 2"}
        assert farm_id == 100
        assert mock_verify_plot.call_count == 2
    
    @patch('use_cases.generate_financial_report_use_case.verify_plot')
    def test_validate_and_get_plots_no_active_plots(self, mock_verify_plot):
        """Test when no active plots are found"""
        mock_verify_plot.return_value = None
        
        with pytest.raises(ValueError, match="No se encontraron lotes activos con los IDs proporcionados"):
            _validate_and_get_plots([1, 2])
    
    @patch('use_cases.generate_financial_report_use_case.verify_plot')
    def test_validate_and_get_plots_different_farms(self, mock_verify_plot):
        """Test when plots belong to different farms"""
        mock_plot1 = Mock()
        mock_plot1.plot_id = 1
        mock_plot1.name = "Lote 1"
        mock_plot1.farm_id = 100
        
        mock_plot2 = Mock()
        mock_plot2.plot_id = 2
        mock_plot2.name = "Lote 2"
        mock_plot2.farm_id = 200
        
        mock_verify_plot.side_effect = [mock_plot1, mock_plot2]
        
        with pytest.raises(ValueError, match="Los lotes seleccionados pertenecen a diferentes fincas"):
            _validate_and_get_plots([1, 2])
    
    @patch('use_cases.generate_financial_report_use_case.verify_plot')
    def test_validate_and_get_plots_partial_success(self, mock_verify_plot):
        """Test when some plots are invalid but others are valid"""
        mock_plot = Mock()
        mock_plot.plot_id = 2
        mock_plot.name = "Lote 2"
        mock_plot.farm_id = 100
        
        mock_verify_plot.side_effect = [None, mock_plot]  # First plot invalid, second valid
        
        plots, plot_names, farm_id = _validate_and_get_plots([1, 2])
        
        assert len(plots) == 1
        assert plot_names == {2: "Lote 2"}
        assert farm_id == 100


class TestValidateUserPermissions:
    """Tests para _validate_user_permissions"""
    
    @patch('use_cases.generate_financial_report_use_case.get_user_role_farm')
    @patch('use_cases.generate_financial_report_use_case.get_role_permissions_for_user_role')
    def test_validate_user_permissions_success(self, mock_get_permissions, mock_get_user_role_farm):
        """Test successful user permission validation"""
        # Arrange
        user = Mock()
        user.user_id = 1
        
        mock_user_role_farm = Mock()
        mock_user_role_farm.user_role_id = 10
        mock_get_user_role_farm.return_value = mock_user_role_farm
        
        mock_get_permissions.return_value = ["read_financial_report", "other_permission"]
        
        # Act & Assert (no exception should be raised)
        _validate_user_permissions(user, 100)
        
        mock_get_user_role_farm.assert_called_once_with(1, 100)
        mock_get_permissions.assert_called_once_with(10)
    
    @patch('use_cases.generate_financial_report_use_case.get_user_role_farm')
    def test_validate_user_permissions_no_farm_association(self, mock_get_user_role_farm):
        """Test when user is not associated with the farm"""
        user = Mock()
        user.user_id = 1
        
        mock_get_user_role_farm.return_value = None
        
        with pytest.raises(PermissionError, match="El usuario 1 no está asociado con la finca 100"):
            _validate_user_permissions(user, 100)
    
    @patch('use_cases.generate_financial_report_use_case.get_user_role_farm')
    @patch('use_cases.generate_financial_report_use_case.get_role_permissions_for_user_role')
    def test_validate_user_permissions_no_read_permission(self, mock_get_permissions, mock_get_user_role_farm):
        """Test when user doesn't have read_financial_report permission"""
        user = Mock()
        user.user_id = 1
        
        mock_user_role_farm = Mock()
        mock_user_role_farm.user_role_id = 10
        mock_get_user_role_farm.return_value = mock_user_role_farm
        
        mock_get_permissions.return_value = ["other_permission"]  # No read_financial_report
        
        with pytest.raises(PermissionError, match="No tienes permiso para ver reportes financieros"):
            _validate_user_permissions(user, 100)


class TestGetTransactionsAndCategories:
    """Tests para _get_transactions_and_categories"""
    
    @patch('use_cases.generate_financial_report_use_case.get_transaction_state')
    def test_get_transactions_and_categories_no_active_state(self, mock_get_state):
        """Test when active transaction state is not found"""
        mock_get_state.return_value = None
        mock_db = Mock()
        
        request = FinancialReportRequest(
            plot_ids=[1, 2],
            fechaInicio=date(2023, 1, 1),
            fechaFin=date(2023, 12, 31),
            include_transaction_history=False
        )
        
        with pytest.raises(ValueError, match="Estado 'Activo' para Transactions no encontrado"):
            _get_transactions_and_categories(mock_db, request)
    
    @patch('use_cases.generate_financial_report_use_case.get_transaction_state')
    def test_get_transactions_and_categories_success(self, mock_get_state):
        """Test successful retrieval of transactions and categories"""
        # Arrange
        mock_state = Mock()
        mock_state.transaction_state_id = 1
        mock_get_state.return_value = mock_state
        
        mock_transaction = Mock()
        mock_transaction.transaction_category_id = 5
        
        mock_category = Mock()
        mock_category.transaction_category_id = 5
        
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_transaction]
        mock_query.options.return_value = mock_query
        
        # Configure the second query for categories
        mock_db.query.side_effect = [mock_query, mock_query]
        mock_query.all.side_effect = [[mock_transaction], [mock_category]]
        
        request = FinancialReportRequest(
            plot_ids=[1, 2],
            fechaInicio=date(2023, 1, 1),
            fechaFin=date(2023, 12, 31),
            include_transaction_history=False
        )
        
        # Act
        transactions, categories_map = _get_transactions_and_categories(mock_db, request)
        
        # Assert
        assert transactions == [mock_transaction]
        assert categories_map == {5: mock_category}
        mock_get_state.assert_called_once_with(mock_db, "Activo")


class TestProcessTransaction:
    """Tests para _process_transaction"""
    
    def test_process_transaction_ingreso(self):
        """Test processing an income transaction"""
        # Arrange
        mock_txn = Mock()
        mock_txn.plot_id = 1
        mock_txn.transaction_id = 100
        mock_txn.transaction_category_id = 5
        mock_txn.value = Decimal("1000.50")
        
        mock_category = Mock()
        mock_category.name = "Venta de café"
        mock_type = Mock()
        mock_type.name = "Ingreso"
        mock_category.transaction_type = mock_type
        
        categories_map = {5: mock_category}
        
        plot_financials = {
            1: {
                "ingresos": 0.0,
                "gastos": 0.0,
                "ingresos_por_categoria": defaultdict(float),
                "gastos_por_categoria": defaultdict(float)
            }
        }
        
        farm_totals = {
            "ingresos": 0.0,
            "gastos": 0.0,
            "ingresos_categorias": defaultdict(float),
            "gastos_categorias": defaultdict(float)
        }
        
        # Act
        _process_transaction(mock_txn, categories_map, plot_financials, farm_totals)
        
        # Assert
        assert plot_financials[1]["ingresos"] == pytest.approx(1000.50)
        assert plot_financials[1]["gastos"] == pytest.approx(0.0)
        assert plot_financials[1]["ingresos_por_categoria"]["Venta de café"] == pytest.approx(1000.50)
        assert farm_totals["ingresos"] == pytest.approx(1000.50)
        assert farm_totals["ingresos_categorias"]["Venta de café"] == pytest.approx(1000.50)
    
    def test_process_transaction_gasto(self):
        """Test processing an expense transaction"""
        # Arrange
        mock_txn = Mock()
        mock_txn.plot_id = 1
        mock_txn.transaction_id = 100
        mock_txn.transaction_category_id = 5
        mock_txn.value = Decimal("500.25")
        
        mock_category = Mock()
        mock_category.name = "Fertilizante"
        mock_type = Mock()
        mock_type.name = "Gasto"
        mock_category.transaction_type = mock_type
        
        categories_map = {5: mock_category}
        
        plot_financials = {
            1: {
                "ingresos": 0.0,
                "gastos": 0.0,
                "ingresos_por_categoria": defaultdict(float),
                "gastos_por_categoria": defaultdict(float)
            }
        }
        
        farm_totals = {
            "ingresos": 0.0,
            "gastos": 0.0,
            "ingresos_categorias": defaultdict(float),
            "gastos_categorias": defaultdict(float)
        }
        
        # Act
        _process_transaction(mock_txn, categories_map, plot_financials, farm_totals)
        
        # Assert
        assert plot_financials[1]["gastos"] == pytest.approx(500.25)
        assert plot_financials[1]["ingresos"] == pytest.approx(0.0)
        assert plot_financials[1]["gastos_por_categoria"]["Fertilizante"] == pytest.approx(500.25)
        assert farm_totals["gastos"] == pytest.approx(500.25)
        assert farm_totals["gastos_categorias"]["Fertilizante"] == pytest.approx(500.25)
    
    def test_process_transaction_plot_not_in_financials(self):
        """Test processing transaction for plot not in plot_financials"""
        mock_txn = Mock()
        mock_txn.plot_id = 999  # Plot not in plot_financials
        
        categories_map = {}
        plot_financials = {}
        farm_totals = {}
        
        # Should not raise exception, just log warning
        _process_transaction(mock_txn, categories_map, plot_financials, farm_totals)
    
    def test_process_transaction_invalid_category(self):
        """Test processing transaction with invalid category"""
        mock_txn = Mock()
        mock_txn.plot_id = 1
        mock_txn.transaction_id = 100
        mock_txn.transaction_category_id = 999  # Invalid category
        
        categories_map = {}  # Empty categories map
        plot_financials = {1: {"ingresos": 0.0, "gastos": 0.0}}
        farm_totals = {}
        
        # Should not raise exception, just log warning
        _process_transaction(mock_txn, categories_map, plot_financials, farm_totals)


class TestBuildPlotFinancialsList:
    """Tests para _build_plot_financials_list"""
    
    def test_build_plot_financials_list(self):
        """Test building plot financials list"""
        plot_financials = {
            1: {
                "plot_id": 1,
                "plot_name": "Lote 1",
                "ingresos": 1000.0,
                "gastos": 300.0,
                "balance": 0.0,  # Will be calculated
                "ingresos_por_categoria": {"Venta": 1000.0},
                "gastos_por_categoria": {"Fertilizante": 300.0}
            },
            2: {
                "plot_id": 2,
                "plot_name": "Lote 2",
                "ingresos": 500.0,
                "gastos": 200.0,
                "balance": 0.0,  # Will be calculated
                "ingresos_por_categoria": {"Venta": 500.0},
                "gastos_por_categoria": {"Semillas": 200.0}
            }
        }
        
        result = _build_plot_financials_list(plot_financials)
        
        assert len(result) == 2
        assert isinstance(result[0], PlotFinancialData)
        assert isinstance(result[1], PlotFinancialData)
        
        # Check that balance was calculated
        for item in result:
            if item.plot_id == 1:
                assert item.balance == pytest.approx(700.0)  # 1000 - 300
                assert len(item.ingresos_por_categoria) == 1
                assert len(item.gastos_por_categoria) == 1
            elif item.plot_id == 2:
                assert item.balance == pytest.approx(300.0)  # 500 - 200


class TestBuildTransactionHistory:
    """Tests para _build_transaction_history"""
    
    @patch('use_cases.generate_financial_report_use_case.get_user_by_id')
    def test_build_transaction_history(self, mock_get_user):
        """Test building transaction history"""
        # Arrange
        mock_user = Mock()
        mock_user.name = "Juan Pérez"
        mock_get_user.return_value = mock_user
        
        mock_txn = Mock()
        mock_txn.plot_id = 1
        mock_txn.transaction_date = date(2023, 6, 15)
        mock_txn.creator_id = 1
        mock_txn.value = Decimal("1000.0")
        mock_txn.transaction_category_id = 5
        mock_txn.transaction_id = 100
        
        mock_category = Mock()
        mock_category.name = "Venta de café"
        mock_type = Mock()
        mock_type.name = "Ingreso"
        mock_category.transaction_type = mock_type
        
        transactions = [mock_txn]
        categories_map = {5: mock_category}
        plot_names = {1: "Lote Principal"}
        farm_name = "Finca El Café"
        
        # Act
        result = _build_transaction_history(transactions, categories_map, plot_names, farm_name)
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TransactionHistoryItem)
        assert result[0].date == date(2023, 6, 15)
        assert result[0].plot_name == "Lote Principal"
        assert result[0].farm_name == "Finca El Café"
        assert result[0].transaction_type == "Ingreso"
        assert result[0].transaction_category == "Venta de café"
        assert result[0].creator_name == "Juan Pérez"
        assert result[0].value == pytest.approx(1000.0)
    
    @patch('use_cases.generate_financial_report_use_case.get_user_by_id')
    def test_build_transaction_history_user_not_found(self, mock_get_user):
        """Test building transaction history when user is not found"""
        mock_get_user.return_value = None
        
        mock_txn = Mock()
        mock_txn.plot_id = 1
        mock_txn.transaction_date = date(2023, 6, 15)
        mock_txn.creator_id = 999
        mock_txn.value = Decimal("1000.0")
        mock_txn.transaction_category_id = 5
        mock_txn.transaction_id = 100
        
        mock_category = Mock()
        mock_category.name = "Venta de café"
        mock_type = Mock()
        mock_type.name = "Ingreso"
        mock_category.transaction_type = mock_type
        
        transactions = [mock_txn]
        categories_map = {5: mock_category}
        plot_names = {1: "Lote Principal"}
        farm_name = "Finca El Café"
        
        result = _build_transaction_history(transactions, categories_map, plot_names, farm_name)
        
        assert len(result) == 1
        assert result[0].creator_name == "Usuario #999"


class TestGenerateFinancialReport:
    """Tests para generate_financial_report"""
    
    def setup_method(self):
        """Setup common test data"""
        self.request = FinancialReportRequest(
            plot_ids=[1, 2],
            fechaInicio=date(2023, 1, 1),
            fechaFin=date(2023, 12, 31),
            include_transaction_history=False
        )
        
        self.user = UserResponse(
            user_id=1,
            name="Test User",
            email="test@example.com"
        )
        
        self.mock_db = Mock()
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    @patch('use_cases.generate_financial_report_use_case.get_farm_by_id')
    def test_generate_financial_report_farm_not_found(self, mock_get_farm, mock_validate_plots):
        """Test when farm is not found"""
        # Arrange
        mock_plots = [Mock()]
        mock_plot_names = {1: "Lote 1"}
        mock_validate_plots.return_value = (mock_plots, mock_plot_names, 100)
        mock_get_farm.return_value = None
        
        # Act
        result = generate_financial_report(self.request, self.user, self.mock_db)
        
        # Assert
        assert result.status_code == 404
        response_data = result.body.decode()
        assert "La finca asociada a los lotes no existe" in response_data
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    @patch('use_cases.generate_financial_report_use_case.get_farm_by_id')
    @patch('use_cases.generate_financial_report_use_case._validate_user_permissions')
    @patch('use_cases.generate_financial_report_use_case._get_transactions_and_categories')
    @patch('use_cases.generate_financial_report_use_case._process_transaction')
    @patch('use_cases.generate_financial_report_use_case._build_plot_financials_list')
    @patch('use_cases.generate_financial_report_use_case.create_response')
    @patch('use_cases.generate_financial_report_use_case.jsonable_encoder')
    def test_generate_financial_report_success(
        self, mock_jsonable_encoder, mock_create_response, mock_build_plot_financials,
        mock_process_transaction, mock_get_transactions, mock_validate_permissions,
        mock_get_farm, mock_validate_plots
    ):
        """Test successful financial report generation"""
        # Arrange
        mock_plot = Mock()
        mock_plot.plot_id = 1
        mock_plots = [mock_plot]
        mock_plot_names = {1: "Lote 1"}
        mock_validate_plots.return_value = (mock_plots, mock_plot_names, 100)
        
        mock_farm = Mock()
        mock_farm.name = "Finca Test"
        mock_get_farm.return_value = mock_farm
        
        mock_transactions = []
        mock_categories = {}
        mock_get_transactions.return_value = (mock_transactions, mock_categories)
        
        mock_plot_financial = PlotFinancialData(
            plot_id=1,
            plot_name="Lote 1",
            ingresos=1000.0,
            gastos=300.0,
            balance=700.0,
            ingresos_por_categoria=[],
            gastos_por_categoria=[]
        )
        mock_build_plot_financials.return_value = [mock_plot_financial]
        
        mock_encoded_response = {"encoded": "data"}
        mock_jsonable_encoder.return_value = mock_encoded_response
        
        mock_response = Mock()
        mock_create_response.return_value = mock_response
        
        # Act
        result = generate_financial_report(self.request, self.user, self.mock_db)
        
        # Assert
        mock_validate_plots.assert_called_once_with([1, 2])
        mock_get_farm.assert_called_once_with(100)
        mock_validate_permissions.assert_called_once_with(self.user, 100)
        mock_get_transactions.assert_called_once_with(self.mock_db, self.request)
        mock_build_plot_financials.assert_called_once()
        mock_create_response.assert_called_once()
        assert result == mock_response
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    def test_generate_financial_report_value_error(self, mock_validate_plots):
        """Test handling of ValueError"""
        mock_validate_plots.side_effect = ValueError("No se encontraron lotes activos")
        
        result = generate_financial_report(self.request, self.user, self.mock_db)
        
        assert result.status_code == 400
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    @patch('use_cases.generate_financial_report_use_case.get_farm_by_id')
    @patch('use_cases.generate_financial_report_use_case._validate_user_permissions')
    def test_generate_financial_report_permission_error(self, mock_validate_permissions, mock_get_farm, mock_validate_plots):
        """Test handling of PermissionError"""
        mock_plots = [Mock()]
        mock_plot_names = {1: "Lote 1"}
        mock_validate_plots.return_value = (mock_plots, mock_plot_names, 100)
        
        mock_farm = Mock()
        mock_get_farm.return_value = mock_farm
        
        mock_validate_permissions.side_effect = PermissionError("No tienes permiso")
        
        result = generate_financial_report(self.request, self.user, self.mock_db)
        
        assert result.status_code == 403
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    def test_generate_financial_report_unexpected_error(self, mock_validate_plots):
        """Test handling of unexpected exceptions"""
        mock_validate_plots.side_effect = Exception("Unexpected error")
        
        result = generate_financial_report(self.request, self.user, self.mock_db)
        
        assert result.status_code == 500
    
    @patch('use_cases.generate_financial_report_use_case._validate_and_get_plots')
    @patch('use_cases.generate_financial_report_use_case.get_farm_by_id')
    @patch('use_cases.generate_financial_report_use_case._validate_user_permissions')
    @patch('use_cases.generate_financial_report_use_case._get_transactions_and_categories')
    @patch('use_cases.generate_financial_report_use_case._build_transaction_history')
    def test_generate_financial_report_with_transaction_history(
        self, mock_build_history, mock_get_transactions, mock_validate_permissions,
        mock_get_farm, mock_validate_plots
    ):
        """Test financial report generation with transaction history"""
        # Arrange
        request_with_history = FinancialReportRequest(
            plot_ids=[1],
            fechaInicio=date(2023, 1, 1),
            fechaFin=date(2023, 12, 31),
            include_transaction_history=True
        )
        
        mock_plot = Mock()
        mock_plot.plot_id = 1
        mock_plots = [mock_plot]
        mock_plot_names = {1: "Lote 1"}
        mock_validate_plots.return_value = (mock_plots, mock_plot_names, 100)
        
        mock_farm = Mock()
        mock_farm.name = "Finca Test"
        mock_get_farm.return_value = mock_farm
        
        mock_transactions = [Mock()]
        mock_categories = {}
        mock_get_transactions.return_value = (mock_transactions, mock_categories)
        
        mock_history = [Mock()]
        mock_build_history.return_value = mock_history
        
        # Act
        with patch('use_cases.generate_financial_report_use_case._build_plot_financials_list') as mock_build_financials:
            mock_build_financials.return_value = []
            result = generate_financial_report(request_with_history, self.user, self.mock_db)
        
        # Assert
        assert result is not None
        mock_build_history.assert_called_once_with(
            mock_transactions, mock_categories, mock_plot_names, "Finca Test"
        )


class TestIntegrationScenarios:
    """Integration-style tests for complete scenarios"""
    
    def test_complete_financial_report_scenario(self):
        """Test a complete financial report generation scenario"""
        # This test would require more complex setup and mocking
        # but demonstrates how integration tests could be structured
        pass
    
    def test_multiple_transaction_types_processing(self):
        """Test processing multiple transaction types in one report"""
        # Arrange transaction data with both income and expenses
        plot_financials = {
            1: {
                "ingresos": 0.0,
                "gastos": 0.0,
                "ingresos_por_categoria": defaultdict(float),
                "gastos_por_categoria": defaultdict(float)
            }
        }
        
        farm_totals = {
            "ingresos": 0.0,
            "gastos": 0.0,
            "ingresos_categorias": defaultdict(float),
            "gastos_categorias": defaultdict(float)
        }
        
        # Create income transaction
        income_txn = Mock()
        income_txn.plot_id = 1
        income_txn.transaction_id = 1
        income_txn.transaction_category_id = 1
        income_txn.value = Decimal("1500.0")
        
        income_category = Mock()
        income_category.name = "Venta"
        income_type = Mock()
        income_type.name = "Ingreso"
        income_category.transaction_type = income_type
        
        # Create expense transaction
        expense_txn = Mock()
        expense_txn.plot_id = 1
        expense_txn.transaction_id = 2
        expense_txn.transaction_category_id = 2
        expense_txn.value = Decimal("500.0")
        
        expense_category = Mock()
        expense_category.name = "Fertilizante"
        expense_type = Mock()
        expense_type.name = "Gasto"
        expense_category.transaction_type = expense_type
        
        categories_map = {1: income_category, 2: expense_category}
        
        # Act
        _process_transaction(income_txn, categories_map, plot_financials, farm_totals)
        _process_transaction(expense_txn, categories_map, plot_financials, farm_totals)
        
        # Assert
        assert plot_financials[1]["ingresos"] == pytest.approx(1500.0)
        assert plot_financials[1]["gastos"] == pytest.approx(500.0)
        assert farm_totals["ingresos"] == pytest.approx(1500.0)
        assert farm_totals["gastos"] == pytest.approx(500.0)
        assert plot_financials[1]["ingresos_por_categoria"]["Venta"] == pytest.approx(1500.0)
        assert plot_financials[1]["gastos_por_categoria"]["Fertilizante"] == pytest.approx(500.0)


if __name__ == "__main__":
    pytest.main([__file__]) 