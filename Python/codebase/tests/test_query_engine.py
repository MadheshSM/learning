"""Unit tests for Query Engine"""
import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_layer.csv_loader import CSVDataLoader
from data_layer.query_engine import QueryEngine


class TestQueryEngine:
    """Test cases for QueryEngine"""

    @pytest.fixture
    def query_engine(self):
        """Create a QueryEngine with loaded data"""
        loader = CSVDataLoader("data", "Data extraction 29.08.25")
        dataframes = loader.load_all()
        return QueryEngine(dataframes)

    def test_get_tables(self, query_engine):
        """Test that get_tables returns list of tables"""
        tables = query_engine.get_tables()
        assert isinstance(tables, list)
        assert 'projects' in tables
        assert 'issues' in tables

    def test_query_basic(self, query_engine):
        """Test basic query without filters"""
        result = query_engine.query('projects')
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_query_with_limit(self, query_engine):
        """Test query with limit"""
        result = query_engine.query('issues', limit=5)
        assert len(result) <= 5

    def test_query_with_filter(self, query_engine):
        """Test query with exact match filter"""
        result = query_engine.query('issues', filters={'status': 'open'})
        assert all(result['status'] == 'open')

    def test_query_with_list_filter(self, query_engine):
        """Test query with IN clause filter"""
        result = query_engine.query('issues', filters={'status': ['open', 'closed']})
        assert all(result['status'].isin(['open', 'closed']))

    def test_query_invalid_table(self, query_engine):
        """Test query with invalid table raises error"""
        with pytest.raises(ValueError):
            query_engine.query('nonexistent_table')

    def test_group_and_count(self, query_engine):
        """Test group_and_count functionality"""
        result = query_engine.group_and_count('issues', 'status')
        assert isinstance(result, pd.DataFrame)
        assert 'count' in result.columns
        assert 'status' in result.columns

    def test_get_summary_stats(self, query_engine):
        """Test get_summary_stats returns summary"""
        result = query_engine.get_summary_stats('projects')
        assert 'table_name' in result
        assert 'total_rows' in result
        assert 'columns' in result

    def test_query_with_column_selection(self, query_engine):
        """Test query with specific columns"""
        result = query_engine.query('projects', columns=['project_id', 'project_name'])
        assert list(result.columns) == ['project_id', 'project_name']

    def test_query_with_order_by(self, query_engine):
        """Test query with ordering"""
        result = query_engine.query('issues', order_by='created_date', ascending=False)
        if 'created_date' in result.columns:
            dates = result['created_date'].dropna()
            if len(dates) > 1:
                assert dates.iloc[0] >= dates.iloc[-1]


class TestQueryEngineAggregation:
    """Test aggregation functions"""

    @pytest.fixture
    def query_engine(self):
        """Create a QueryEngine with loaded data"""
        loader = CSVDataLoader("data", "Data extraction 29.08.25")
        dataframes = loader.load_all()
        return QueryEngine(dataframes)

    def test_aggregate_sum(self, query_engine):
        """Test sum aggregation"""
        result = query_engine.aggregate(
            'schedule', 
            'project_id', 
            'percent_complete', 
            agg_func='sum'
        )
        assert isinstance(result, pd.DataFrame)

    def test_aggregate_mean(self, query_engine):
        """Test mean aggregation"""
        result = query_engine.aggregate(
            'schedule', 
            'project_id', 
            'percent_complete', 
            agg_func='mean'
        )
        assert isinstance(result, pd.DataFrame)

    def test_get_trend_data(self, query_engine):
        """Test trend data aggregation"""
        result = query_engine.get_trend_data(
            'issues',
            'created_date',
            'monthly'
        )
        assert isinstance(result, pd.DataFrame)
        assert 'period' in result.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
