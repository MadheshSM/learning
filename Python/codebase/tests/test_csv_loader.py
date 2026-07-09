"""Unit tests for CSV Data Loader"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_layer.csv_loader import CSVDataLoader


class TestCSVDataLoader:
    """Test cases for CSVDataLoader"""

    @pytest.fixture
    def loader(self):
        """Create a CSVDataLoader instance"""
        return CSVDataLoader("data", "Data extraction 29.08.25")

    def test_loader_initialization(self, loader):
        """Test that loader initializes correctly"""
        assert loader.data_dir == Path("data")
        assert loader.extraction_folder == "Data extraction 29.08.25"
        assert loader.dataframes == {}

    def test_load_all_returns_dict(self, loader):
        """Test that load_all returns a dictionary"""
        result = loader.load_all()
        assert isinstance(result, dict)

    def test_load_all_contains_key_tables(self, loader):
        """Test that key tables are loaded"""
        result = loader.load_all()
        key_tables = ['projects', 'issues', 'rfis', 'submittals', 'schedule', 'users']
        for table in key_tables:
            assert table in result, f"Missing table: {table}"

    def test_projects_table_has_required_columns(self, loader):
        """Test that projects table has required columns"""
        loader.load_all()
        projects = loader.get_dataframe('projects')
        assert projects is not None
        required_cols = ['project_id', 'project_name', 'status']
        for col in required_cols:
            assert col in projects.columns, f"Missing column: {col}"

    def test_issues_table_has_required_columns(self, loader):
        """Test that issues table has required columns"""
        loader.load_all()
        issues = loader.get_dataframe('issues')
        assert issues is not None
        required_cols = ['issue_id', 'project_id', 'title', 'status']
        for col in required_cols:
            assert col in issues.columns, f"Missing column: {col}"

    def test_rfis_table_has_required_columns(self, loader):
        """Test that RFIs table has required columns"""
        loader.load_all()
        rfis = loader.get_dataframe('rfis')
        assert rfis is not None
        required_cols = ['rfi_id', 'project_id', 'title', 'status']
        for col in required_cols:
            assert col in rfis.columns, f"Missing column: {col}"

    def test_schedule_table_has_required_columns(self, loader):
        """Test that schedule table has required columns"""
        loader.load_all()
        schedule = loader.get_dataframe('schedule')
        assert schedule is not None
        required_cols = ['task_id', 'project_id', 'task_name']
        for col in required_cols:
            assert col in schedule.columns, f"Missing column: {col}"

    def test_date_columns_converted(self, loader):
        """Test that date columns are converted to datetime"""
        loader.load_all()
        issues = loader.get_dataframe('issues')
        if 'due_date' in issues.columns:
            assert pd.api.types.is_datetime64_any_dtype(issues['due_date'])

    def test_get_table_names(self, loader):
        """Test that get_table_names returns loaded tables"""
        loader.load_all()
        names = loader.get_table_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_get_schema(self, loader):
        """Test that get_schema returns table schema"""
        loader.load_all()
        schema = loader.get_schema('projects')
        assert schema is not None
        assert 'name' in schema
        assert 'row_count' in schema
        assert 'columns' in schema

    def test_get_nonexistent_dataframe_returns_none(self, loader):
        """Test that getting nonexistent table returns None"""
        loader.load_all()
        result = loader.get_dataframe('nonexistent_table')
        assert result is None


class TestDataIntegrity:
    """Test data integrity across tables"""

    @pytest.fixture
    def loader(self):
        """Create and load a CSVDataLoader instance"""
        loader = CSVDataLoader("data", "Data extraction 29.08.25")
        loader.load_all()
        return loader

    def test_projects_not_empty(self, loader):
        """Test that projects table has data"""
        projects = loader.get_dataframe('projects')
        assert len(projects) > 0

    def test_issues_not_empty(self, loader):
        """Test that issues table has data"""
        issues = loader.get_dataframe('issues')
        assert len(issues) > 0

    def test_issues_have_valid_status(self, loader):
        """Test that issues have valid status values"""
        issues = loader.get_dataframe('issues')
        valid_statuses = ['open', 'closed', 'completed', 'in_review', 'draft']
        for status in issues['status'].dropna().unique():
            assert status in valid_statuses, f"Invalid status: {status}"

    def test_rfis_have_valid_status(self, loader):
        """Test that RFIs have valid status values"""
        rfis = loader.get_dataframe('rfis')
        # ACC RFI statuses - includes workflow states
        valid_base_statuses = ['open', 'closed', 'answered', 'draft', 'submitted', 'rejected', 'void']
        for status in rfis['status'].dropna().unique():
            # Strip revision suffixes for base status check
            base_status = status.lower().replace('rev1', '').replace('rev2', '').replace('rev3', '')
            is_valid = any(base in base_status for base in valid_base_statuses)
            assert is_valid, f"Unexpected RFI status: {status}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
