"""Tests for agent tools"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.tools.data_tools import DataTools
from agents.tools.aggregation_tools import AggregationTools
from agents.tools.chart_tools import ChartTools


class TestDataTools:
    """Tests for DataTools class"""

    @pytest.fixture
    def data_tools(self, query_engine):
        """Create DataTools instance"""
        return DataTools(query_engine)

    def test_query_table_basic(self, data_tools):
        """Test basic table query"""
        result = data_tools.query_table("issues")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_query_table_with_filters(self, data_tools):
        """Test table query with filters"""
        result = data_tools.query_table("issues", filters={"status": "open"})

        assert isinstance(result, list)
        for item in result:
            assert item.get("status") == "open"

    def test_query_table_with_limit(self, data_tools):
        """Test table query with limit"""
        result = data_tools.query_table("issues", limit=2)

        assert len(result) <= 2

    def test_query_table_invalid_table(self, data_tools):
        """Test query on invalid table returns error"""
        result = data_tools.query_table("nonexistent")

        assert isinstance(result, dict)
        assert "error" in result

    def test_get_table_schema(self, data_tools):
        """Test getting table schema"""
        result = data_tools.get_table_schema("issues")

        assert "table" in result
        assert "row_count" in result
        assert "columns" in result

    def test_get_overdue_items(self, data_tools):
        """Test getting overdue items"""
        result = data_tools.get_overdue_items(
            "issues",
            open_statuses=["open", "in_progress"]
        )

        assert isinstance(result, list)

    def test_search_text(self, data_tools):
        """Test text search"""
        result = data_tools.search_text("issues", "title", "issue")

        assert isinstance(result, list)

    def test_get_unique_values(self, data_tools):
        """Test getting unique values"""
        result = data_tools.get_unique_values("issues", "status")

        assert isinstance(result, list)
        assert "open" in result

    def test_count_by_status(self, data_tools):
        """Test counting by status"""
        result = data_tools.count_by_status("issues")

        assert isinstance(result, dict)
        assert "open" in result

    def test_get_available_tables(self, data_tools):
        """Test getting available tables"""
        result = data_tools.get_available_tables()

        assert isinstance(result, list)
        assert "issues" in result
        assert "projects" in result


class TestAggregationTools:
    """Tests for AggregationTools class"""

    @pytest.fixture
    def agg_tools(self, query_engine):
        """Create AggregationTools instance"""
        return AggregationTools(query_engine)

    def test_group_and_count_single(self, agg_tools):
        """Test group and count with single column"""
        result = agg_tools.group_and_count("issues", "status")

        assert isinstance(result, list)
        for item in result:
            assert "status" in item
            assert "count" in item

    def test_group_and_count_multiple(self, agg_tools):
        """Test group and count with multiple columns"""
        result = agg_tools.group_and_count("issues", ["project_id", "status"])

        assert isinstance(result, list)
        for item in result:
            assert "project_id" in item
            assert "status" in item

    def test_group_and_count_with_filters(self, agg_tools):
        """Test group and count with filters"""
        result = agg_tools.group_and_count(
            "issues",
            "status",
            filters={"project_id": "PROJ-001"}
        )

        assert isinstance(result, list)

    def test_aggregate_sum(self, agg_tools):
        """Test aggregate with sum"""
        result = agg_tools.aggregate("cost", "category", "budgeted", "sum")

        assert isinstance(result, list)

    def test_aggregate_mean(self, agg_tools):
        """Test aggregate with mean"""
        result = agg_tools.aggregate("cost", "project_id", "budgeted", "mean")

        assert isinstance(result, list)

    def test_get_trend_data(self, agg_tools):
        """Test getting trend data"""
        result = agg_tools.get_trend_data("issues", "created_date", "monthly")

        assert isinstance(result, list)
        if len(result) > 0:
            assert "period" in result[0]
            assert "count" in result[0]

    def test_calculate_metrics(self, agg_tools):
        """Test calculating metrics"""
        result = agg_tools.calculate_metrics("cost", "budgeted")

        assert "count" in result
        assert "sum" in result
        assert "mean" in result
        assert "min" in result
        assert "max" in result

    def test_compare_groups(self, agg_tools):
        """Test comparing groups"""
        result = agg_tools.compare_groups("issues", "status", "count")

        assert isinstance(result, list)
        for item in result:
            assert "group" in item
            assert "value" in item
            assert "percentage" in item

    def test_get_top_n(self, agg_tools):
        """Test getting top N"""
        result = agg_tools.get_top_n("issues", "assignee", n=3)

        assert isinstance(result, list)
        assert len(result) <= 3

    def test_calculate_overdue_stats(self, agg_tools):
        """Test calculating overdue stats"""
        result = agg_tools.calculate_overdue_stats(
            "issues",
            open_statuses=["open", "in_progress"]
        )

        assert "total_open" in result
        assert "total_overdue" in result
        assert "overdue_percentage" in result

    def test_cross_tabulate(self, agg_tools):
        """Test cross tabulation"""
        result = agg_tools.cross_tabulate("issues", "project_id", "status")

        assert "index" in result
        assert "columns" in result
        assert "values" in result


class TestChartTools:
    """Tests for ChartTools class"""

    @pytest.fixture
    def chart_tools(self, query_engine):
        """Create ChartTools instance"""
        return ChartTools(query_engine)

    def test_create_bar_chart(self, chart_tools):
        """Test creating bar chart"""
        chart = chart_tools.create_bar_chart(
            labels=["A", "B", "C"],
            data=[10, 20, 30],
            title="Test Bar Chart"
        )

        assert chart["type"] == "bar"
        assert chart["title"] == "Test Bar Chart"
        assert chart["data"]["labels"] == ["A", "B", "C"]
        assert chart["data"]["datasets"][0]["data"] == [10, 20, 30]

    def test_create_bar_chart_horizontal(self, chart_tools):
        """Test creating horizontal bar chart"""
        chart = chart_tools.create_bar_chart(
            labels=["A", "B"],
            data=[10, 20],
            title="Horizontal",
            horizontal=True
        )

        assert chart["options"]["indexAxis"] == "y"

    def test_create_pie_chart(self, chart_tools):
        """Test creating pie chart"""
        chart = chart_tools.create_pie_chart(
            labels=["A", "B", "C"],
            data=[10, 20, 30],
            title="Test Pie"
        )

        assert chart["type"] == "pie"
        assert len(chart["data"]["labels"]) == 3

    def test_create_doughnut_chart(self, chart_tools):
        """Test creating doughnut chart"""
        chart = chart_tools.create_doughnut_chart(
            labels=["A", "B"],
            data=[50, 50],
            title="Test Doughnut"
        )

        assert chart["type"] == "doughnut"
        assert chart["options"]["cutout"] == "60%"

    def test_create_line_chart(self, chart_tools):
        """Test creating line chart"""
        chart = chart_tools.create_line_chart(
            labels=["Jan", "Feb", "Mar"],
            datasets=[
                {"label": "Series 1", "data": [10, 20, 30]},
                {"label": "Series 2", "data": [5, 15, 25]}
            ],
            title="Test Line"
        )

        assert chart["type"] == "line"
        assert len(chart["data"]["datasets"]) == 2

    def test_create_kpi_card(self, chart_tools):
        """Test creating KPI card"""
        kpi = chart_tools.create_kpi_card(
            title="Total Issues",
            value=42,
            unit="items",
            trend="up",
            change="+10%"
        )

        assert kpi["type"] == "kpi"
        assert kpi["data"]["value"] == 42
        assert kpi["data"]["trend"] == "up"
        assert kpi["data"]["change"] == "+10%"

    def test_create_table(self, chart_tools):
        """Test creating table"""
        table = chart_tools.create_table(
            headers=["ID", "Name", "Status"],
            rows=[
                ["1", "Item A", "Open"],
                ["2", "Item B", "Closed"]
            ],
            title="Test Table"
        )

        assert table["type"] == "table"
        assert len(table["data"]["headers"]) == 3
        assert len(table["data"]["rows"]) == 2

    def test_create_stacked_bar_chart(self, chart_tools):
        """Test creating stacked bar chart"""
        chart = chart_tools.create_stacked_bar_chart(
            labels=["A", "B", "C"],
            datasets=[
                {"label": "Open", "data": [10, 5, 8]},
                {"label": "Closed", "data": [5, 10, 2]}
            ],
            title="Stacked"
        )

        assert chart["type"] == "bar"
        assert chart["options"]["scales"]["x"]["stacked"] is True

    def test_get_colors_status(self, chart_tools):
        """Test color selection for status values"""
        colors = chart_tools._get_colors(["open", "closed", "in_progress"])

        assert len(colors) == 3
        # Open should be reddish
        assert "68, 68" in colors[0] or "239" in colors[0]

    def test_get_colors_priority(self, chart_tools):
        """Test color selection for priority values"""
        colors = chart_tools._get_colors(["critical", "high", "medium", "low"])

        assert len(colors) == 4

    def test_auto_chart_few_categories(self, chart_tools):
        """Test auto chart with few categories creates doughnut"""
        data = [
            {"status": "open", "count": 10},
            {"status": "closed", "count": 5}
        ]

        chart = chart_tools.auto_chart(data, "status", "count", "Status")

        assert chart["type"] == "doughnut"

    def test_auto_chart_many_categories(self, chart_tools):
        """Test auto chart with many categories creates bar"""
        data = [
            {"category": f"Cat{i}", "count": i}
            for i in range(8)
        ]

        chart = chart_tools.auto_chart(data, "category", "count", "Categories")

        assert chart["type"] == "bar"

    def test_auto_chart_empty_data(self, chart_tools):
        """Test auto chart with empty data creates KPI"""
        chart = chart_tools.auto_chart([], "status", "count", "Empty")

        assert chart["type"] == "kpi"
        assert chart["data"]["value"] == 0


class TestChartColors:
    """Tests for chart color handling"""

    @pytest.fixture
    def chart_tools(self, query_engine):
        return ChartTools(query_engine)

    def test_color_palettes_exist(self, chart_tools):
        """Test that color palettes are defined"""
        assert "primary" in chart_tools.COLORS
        assert "status" in chart_tools.COLORS
        assert "priority" in chart_tools.COLORS
        assert "severity" in chart_tools.COLORS

    def test_primary_colors_have_enough(self, chart_tools):
        """Test primary palette has enough colors"""
        assert len(chart_tools.COLORS["primary"]) >= 8

    def test_status_colors_complete(self, chart_tools):
        """Test all status values have colors"""
        statuses = ["open", "in_progress", "resolved", "closed"]
        for status in statuses:
            assert status in chart_tools.COLORS["status"]

    def test_priority_colors_complete(self, chart_tools):
        """Test all priority values have colors"""
        priorities = ["critical", "high", "medium", "low"]
        for priority in priorities:
            assert priority in chart_tools.COLORS["priority"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
