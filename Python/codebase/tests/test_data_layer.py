"""Comprehensive tests for data layer components"""
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
from unittest.mock import Mock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_layer.excel_loader import ExcelDataLoader
from data_layer.krion6d_loader import Krion6dDataLoader
from data_layer.query_engine import QueryEngine
from agents.data_analyst_agent import DataAnalystAgent
from data_layer.data_store import DataStore
from data_layer.schema import validate_dataframe_schema, EXPECTED_SCHEMAS


class TestExcelDataLoader:
    """Tests for ExcelDataLoader class"""

    def test_init_creates_instance(self):
        """Test that loader initializes correctly"""
        loader = ExcelDataLoader("test_data")
        assert loader.data_dir == Path("test_data")
        assert loader.dataframes == {}

    def test_load_all_with_empty_directory(self, tmp_path):
        """Test loading from empty directory returns empty dict"""
        loader = ExcelDataLoader(str(tmp_path))
        result = loader.load_all()
        assert result == {}
        assert loader.dataframes == {}

    def test_load_all_with_nonexistent_directory(self):
        """Test loading from nonexistent directory"""
        loader = ExcelDataLoader("nonexistent_directory_12345")
        result = loader.load_all()
        assert result == {}

    def test_load_single_excel_file(self, tmp_path):
        """Test loading a single Excel file"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'value': [10.5, 20.0, 30.5]
        })
        file_path = tmp_path / "test_data.xlsx"
        df.to_excel(file_path, index=False)

        loader = ExcelDataLoader(str(tmp_path))
        result = loader.load_all()

        assert 'test_data' in result
        assert len(result['test_data']) == 3
        assert list(result['test_data'].columns) == ['id', 'name', 'value']

    def test_load_multiple_excel_files(self, tmp_path):
        """Test loading multiple Excel files"""
        df1 = pd.DataFrame({'col1': [1, 2]})
        df2 = pd.DataFrame({'col2': ['a', 'b']})

        (tmp_path / "file1.xlsx").write_bytes(b'')
        df1.to_excel(tmp_path / "file1.xlsx", index=False)
        df2.to_excel(tmp_path / "file2.xlsx", index=False)

        loader = ExcelDataLoader(str(tmp_path))
        result = loader.load_all()

        assert 'file1' in result
        assert 'file2' in result

    def test_date_column_conversion(self, tmp_path):
        """Test that date columns are auto-converted"""
        df = pd.DataFrame({
            'id': [1, 2],
            'created_date': ['2024-01-01', '2024-01-02'],
            'due_date': ['2024-02-01', '2024-02-02']
        })
        file_path = tmp_path / "dates.xlsx"
        df.to_excel(file_path, index=False)

        loader = ExcelDataLoader(str(tmp_path))
        result = loader.load_all()

        assert pd.api.types.is_datetime64_any_dtype(result['dates']['created_date'])
        assert pd.api.types.is_datetime64_any_dtype(result['dates']['due_date'])

    def test_get_dataframe_existing(self, excel_loader):
        """Test getting an existing dataframe"""
        df = excel_loader.get_dataframe('projects')
        assert df is not None
        assert isinstance(df, pd.DataFrame)

    def test_get_dataframe_nonexistent(self, excel_loader):
        """Test getting a nonexistent dataframe returns None"""
        df = excel_loader.get_dataframe('nonexistent')
        assert df is None

    def test_reload_existing_table(self, temp_data_dir):
        """Test reloading a specific table"""
        loader = ExcelDataLoader(temp_data_dir)
        loader.load_all()

        original_count = len(loader.dataframes['projects'])

        # Modify the file
        df = loader.dataframes['projects']
        new_df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        new_df.to_excel(Path(temp_data_dir) / "projects.xlsx", index=False)

        # Reload
        result = loader.reload('projects')

        assert result is not None
        assert len(result) == original_count + 1

    def test_get_table_names(self, excel_loader):
        """Test getting list of table names"""
        names = excel_loader.get_table_names()
        assert 'projects' in names
        assert 'issues' in names
        assert isinstance(names, list)

    def test_get_schema_existing_table(self, excel_loader):
        """Test getting schema for existing table"""
        schema = excel_loader.get_schema('issues')

        assert schema is not None
        assert schema['name'] == 'issues'
        assert 'row_count' in schema
        assert 'columns' in schema
        assert len(schema['columns']) > 0

    def test_get_schema_nonexistent_table(self, excel_loader):
        """Test getting schema for nonexistent table"""
        schema = excel_loader.get_schema('nonexistent')
        assert schema is None

    def test_schema_includes_column_details(self, excel_loader):
        """Test that schema includes detailed column info"""
        schema = excel_loader.get_schema('issues')

        for col_info in schema['columns']:
            assert 'name' in col_info
            assert 'dtype' in col_info
            assert 'non_null_count' in col_info
            assert 'null_count' in col_info


class TestQueryEngine:
    """Tests for QueryEngine class"""

    def test_init_with_dataframes(self, sample_dataframes):
        """Test initialization with dataframes"""
        qe = QueryEngine(sample_dataframes)
        assert qe.dfs == sample_dataframes

    def test_get_tables(self, query_engine):
        """Test getting list of available tables"""
        tables = query_engine.get_tables()
        assert 'projects' in tables
        assert 'issues' in tables
        assert 'rfis' in tables

    def test_query_basic(self, query_engine):
        """Test basic query without filters"""
        result = query_engine.query('issues')
        assert len(result) == 5
        assert isinstance(result, pd.DataFrame)

    def test_query_with_equality_filter(self, query_engine):
        """Test query with equality filter"""
        result = query_engine.query('issues', filters={'status': 'open'})
        assert len(result) == 2
        assert all(result['status'] == 'open')

    def test_query_with_list_filter(self, query_engine):
        """Test query with IN filter (list)"""
        result = query_engine.query('issues', filters={'status': ['open', 'in_progress']})
        assert len(result) == 3
        assert all(result['status'].isin(['open', 'in_progress']))

    def test_query_with_gt_operator(self, query_engine):
        """Test query with greater than operator"""
        result = query_engine.query('cost', filters={'budgeted': {'gt': 5000000}})
        assert all(result['budgeted'] > 5000000)

    def test_query_with_lt_operator(self, query_engine):
        """Test query with less than operator"""
        result = query_engine.query('cost', filters={'budgeted': {'lt': 3000000}})
        assert all(result['budgeted'] < 3000000)

    def test_query_with_contains_operator(self, query_engine):
        """Test query with contains operator"""
        result = query_engine.query('issues', filters={'title': {'contains': 'issue'}})
        assert len(result) >= 1

    def test_query_with_column_selection(self, query_engine):
        """Test query with specific columns"""
        result = query_engine.query('issues', columns=['issue_id', 'status'])
        assert list(result.columns) == ['issue_id', 'status']

    def test_query_with_limit(self, query_engine):
        """Test query with limit"""
        result = query_engine.query('issues', limit=2)
        assert len(result) == 2

    def test_query_with_order_by(self, query_engine):
        """Test query with ordering"""
        result = query_engine.query('issues', order_by='priority', ascending=True)
        assert len(result) == 5

    def test_query_invalid_table_raises_error(self, query_engine):
        """Test that querying invalid table raises ValueError"""
        with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
            query_engine.query('nonexistent')

    def test_group_and_count_single_column(self, query_engine):
        """Test group and count with single column"""
        result = query_engine.group_and_count('issues', 'status')

        assert 'status' in result.columns
        assert 'count' in result.columns
        assert result['count'].sum() == 5

    def test_group_and_count_multiple_columns(self, query_engine):
        """Test group and count with multiple columns"""
        result = query_engine.group_and_count('issues', ['project_id', 'status'])

        assert 'project_id' in result.columns
        assert 'status' in result.columns
        assert 'count' in result.columns

    def test_group_and_count_with_filters(self, query_engine):
        """Test group and count with filters"""
        result = query_engine.group_and_count(
            'issues',
            'status',
            filters={'project_id': 'PROJ-001'}
        )
        assert result['count'].sum() == 3

    def test_aggregate_sum(self, query_engine):
        """Test aggregate with sum function"""
        result = query_engine.aggregate('cost', 'category', 'budgeted', 'sum')

        assert 'category' in result.columns
        assert 'budgeted' in result.columns

    def test_aggregate_mean(self, query_engine):
        """Test aggregate with mean function"""
        result = query_engine.aggregate('cost', 'project_id', 'budgeted', 'mean')
        assert len(result) == 2

    def test_aggregate_invalid_function(self, query_engine):
        """Test aggregate with invalid function raises error"""
        with pytest.raises(ValueError):
            query_engine.aggregate('cost', 'category', 'budgeted', 'invalid_func')

    def test_get_overdue_items(self, query_engine):
        """Test getting overdue items"""
        result = query_engine.get_overdue(
            'issues',
            due_date_col='due_date',
            status_col='status',
            open_statuses=['open', 'in_progress']
        )

        # All returned items should have due_date in the past
        assert all(result['due_date'] < datetime.now())

    def test_get_overdue_calculates_days(self, query_engine):
        """Test that overdue calculation adds days_overdue column"""
        result = query_engine.get_overdue(
            'issues',
            open_statuses=['open', 'in_progress']
        )

        if len(result) > 0:
            assert 'days_overdue' in result.columns
            assert all(result['days_overdue'] >= 0)

    def test_get_summary_stats(self, query_engine):
        """Test getting summary statistics"""
        stats = query_engine.get_summary_stats('issues')

        assert stats['table_name'] == 'issues'
        assert stats['total_rows'] == 5
        assert 'columns' in stats
        assert 'categorical_summary' in stats

    def test_get_summary_stats_includes_date_range(self, query_engine):
        """Test that summary stats include date range"""
        stats = query_engine.get_summary_stats('issues')
        assert 'date_range' in stats

    def test_get_trend_data_monthly(self, query_engine):
        """Test getting trend data with monthly grouping"""
        result = query_engine.get_trend_data(
            'issues',
            'created_date',
            period='monthly'
        )

        assert 'period' in result.columns
        assert 'count' in result.columns

    def test_get_trend_data_weekly(self, query_engine):
        """Test getting trend data with weekly grouping"""
        result = query_engine.get_trend_data(
            'issues',
            'created_date',
            period='weekly'
        )
        assert len(result) >= 1

    def test_update_dataframes(self, query_engine, sample_projects_df):
        """Test updating dataframes"""
        new_dfs = {'new_table': sample_projects_df}
        query_engine.update_dataframes(new_dfs)

        assert 'new_table' in query_engine.get_tables()


class TestDataStore:
    """Tests for DataStore singleton"""

    def test_singleton_pattern(self):
        """Test that DataStore implements singleton pattern"""
        # Reset singleton for testing
        DataStore._instance = None

        store1 = DataStore("data1")
        store2 = DataStore("data2")

        assert store1 is store2

    def test_initialize(self, temp_data_dir):
        """Test DataStore initialization"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        result = store.initialize()

        assert result is True
        assert len(store.dataframes) > 0
        assert store.query_engine is not None

    def test_get_tables(self, temp_data_dir):
        """Test getting table list from DataStore"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        store.initialize()

        tables = store.get_tables()
        assert 'projects' in tables
        assert 'issues' in tables

    def test_get_table(self, temp_data_dir):
        """Test getting specific table"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        store.initialize()

        df = store.get_table('projects')
        assert df is not None
        assert isinstance(df, pd.DataFrame)

    def test_get_table_info(self, temp_data_dir):
        """Test getting table info"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        store.initialize()

        info = store.get_table_info('projects')

        assert info['name'] == 'projects'
        assert 'rows' in info
        assert 'columns' in info
        assert 'column_names' in info

    def test_add_dataframe(self, temp_data_dir):
        """Test adding a new DataFrame"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        store.initialize()

        new_df = pd.DataFrame({'col': [1, 2, 3]})
        store.add_dataframe('new_table', new_df)

        assert 'new_table' in store.get_tables()

    def test_remove_table(self, temp_data_dir):
        """Test removing a table"""
        DataStore._instance = None
        store = DataStore(temp_data_dir)
        store.initialize()

        initial_count = len(store.get_tables())
        result = store.remove_table('projects')

        assert result is True
        assert len(store.get_tables()) == initial_count - 1


class TestKrion6dDataLoader:
    """Tests for Krion6dDataLoader-derived fields"""

    def test_rfa_work_hours_derived_and_worklog_preserved(self):
        """RFA work_hours is derived separately from worklog_hours (inclusive days, weekends excluded)."""
        loader = Krion6dDataLoader(client=None)
        records = [{
            "id": "RFA-1",
            "projectId": "PROJ-1",
            "name": "Approval A",
            "startDate": "2026-04-10",  # Friday
            "targetDate": "2026-04-14",  # Tuesday (Sat/Sun in between)
            "worklogHours": 6,
        }]

        df = loader._to_dataframe(records, "rfas")

        assert "work_hours" in df.columns
        assert "worklog_hours" in df.columns
        assert df.loc[0, "work_hours"] == 24.0
        assert df.loc[0, "worklog_hours"] == 6


class TestRfaWorkHoursDataAnalystIntent:
    """RFA work_hours vs worklog_hours intent (avoids importing orchestrator/redis via test_agents)."""

    def test_rfa_work_hours_intent_helpers(self, query_engine, mock_llm_provider):
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        assert agent._is_work_hours_query("show work hours for rfa") is True
        assert agent._is_worklog_hours_query("show work hours for rfa") is False
        assert agent._is_worklog_hours_query("show work log hours for rfa") is True
        assert agent._is_work_hours_query("show work log hours for rfa") is False

    @pytest.mark.asyncio
    async def test_query_rfas_prioritizes_work_hours_columns(self, query_engine, mock_llm_provider):
        agent = DataAnalystAgent(mock_llm_provider, query_engine)
        agent._current_context = {"original_query": "show work hours for rfa"}
        agent.data_tools.query_table = Mock(return_value={"data": []})

        await agent._execute_tool("query_rfas", {})

        called_columns = agent.data_tools.query_table.call_args.kwargs.get("columns")
        assert called_columns is not None
        assert called_columns.index("work_hours") < called_columns.index("worklog_hours")


class TestSchemaValidation:
    """Tests for schema validation"""

    def test_validate_projects_schema(self, sample_projects_df):
        """Test validating projects schema"""
        result = validate_dataframe_schema(sample_projects_df, 'projects')

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_issues_schema(self, sample_issues_df):
        """Test validating issues schema"""
        result = validate_dataframe_schema(sample_issues_df, 'issues')

        assert result['valid'] is True

    def test_validate_missing_required_column(self):
        """Test validation fails with missing required column"""
        df = pd.DataFrame({
            'project_name': ['A', 'B'],
            'status': ['active', 'inactive']
        })  # Missing project_id

        result = validate_dataframe_schema(df, 'projects')

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_unknown_schema(self):
        """Test validation of unknown schema type"""
        df = pd.DataFrame({'col': [1, 2, 3]})
        result = validate_dataframe_schema(df, 'unknown_table')

        assert result['valid'] is True  # Unknown schemas pass by default

    def test_expected_schemas_defined(self):
        """Test that expected schemas are defined"""
        assert 'projects' in EXPECTED_SCHEMAS
        assert 'issues' in EXPECTED_SCHEMAS
        assert 'rfis' in EXPECTED_SCHEMAS
        assert 'rfas' in EXPECTED_SCHEMAS
        assert 'safety_observations' in EXPECTED_SCHEMAS
        assert 'documents' in EXPECTED_SCHEMAS
        assert 'schedule' in EXPECTED_SCHEMAS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
