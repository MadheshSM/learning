"""Aggregation and statistics tools for agents"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from data_layer.query_engine import QueryEngine


# Plain string filters on these columns are treated as partial name match (same as query_rfis).
_PERSON_NAME_FILTER_COLUMNS = frozenset(
    {"submitted_by", "assigned_to", "assignee", "manager", "subcontractor"}
)


def _normalize_person_name_filters(filters: Optional[Dict]) -> Optional[Dict]:
    if not filters:
        return filters
    out = {}
    for k, v in filters.items():
        if k in _PERSON_NAME_FILTER_COLUMNS and isinstance(v, str) and v.strip():
            out[k] = {"contains": v.strip()}
        else:
            out[k] = v
    return out


def clean_for_json(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to list of dicts, replacing NaN with None for JSON compatibility"""
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    for col in df.select_dtypes(include=['datetime64[ns]']).columns:
        df[col] = df[col].astype(object).where(df[col].notna(), None)
    return df.to_dict('records')


class AggregationTools:
    """Tools for aggregating and analyzing data"""

    def __init__(self, query_engine: QueryEngine):
        self.qe = query_engine

    def group_and_count(
        self,
        table: str,
        group_by: Union[str, List[str]],
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Group by column(s) and count occurrences"""
        try:
            filters = _normalize_person_name_filters(filters)
            df = self.qe.group_and_count(table, group_by, filters)
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "group_by": group_by,
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def aggregate(
        self,
        table: str,
        group_by: Union[str, List[str]],
        agg_column: str,
        agg_func: str = "sum"
    ) -> Dict[str, Any]:
        """Aggregate data with grouping"""
        try:
            df = self.qe.aggregate(table, group_by, agg_column, agg_func)
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "group_by": group_by,
                "aggregation": {"column": agg_column, "function": agg_func},
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def get_trend_data(
        self,
        table: str,
        date_column: str,
        period: str = "monthly",
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get trend data grouped by time period"""
        try:
            df = self.qe.get_trend_data(table, date_column, period, filters=filters)
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "period": period,
                "date_column": date_column,
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_metrics(
        self,
        table: str,
        numeric_column: str,
        filters: Optional[Dict] = None
    ) -> Dict[str, float]:
        """Calculate various metrics for a numeric column"""
        try:
            df = self.qe.query(table, filters)

            if numeric_column not in df.columns:
                return {"error": f"Column '{numeric_column}' not found"}

            series = df[numeric_column].dropna()

            return {
                "count": int(len(series)),
                "sum": float(series.sum()),
                "mean": float(series.mean()) if len(series) > 0 else 0,
                "median": float(series.median()) if len(series) > 0 else 0,
                "min": float(series.min()) if len(series) > 0 else 0,
                "max": float(series.max()) if len(series) > 0 else 0,
                "std": float(series.std()) if len(series) > 1 else 0
            }
        except Exception as e:
            return {"error": str(e)}

    def compare_groups(
        self,
        table: str,
        group_column: str,
        metric_column: str,
        agg_func: str = "count"
    ) -> List[Dict]:
        """Compare metrics across different groups"""
        try:
            if agg_func == "count":
                df = self.qe.group_and_count(table, group_column)
            else:
                df = self.qe.aggregate(table, group_column, metric_column, agg_func)

            # Calculate percentages
            total = df['count'].sum() if 'count' in df.columns else df[metric_column].sum()
            value_col = 'count' if 'count' in df.columns else metric_column

            results = []
            for _, row in df.iterrows():
                results.append({
                    "group": row[group_column],
                    "value": float(row[value_col]),
                    "percentage": round((row[value_col] / total) * 100, 2) if total > 0 else 0
                })

            return sorted(results, key=lambda x: x['value'], reverse=True)
        except Exception as e:
            return {"error": str(e)}

    def get_top_n(
        self,
        table: str,
        group_column: str,
        n: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get top N groups by count"""
        try:
            df = self.qe.group_and_count(table, group_column, filters)
            return clean_for_json(df.head(n))
        except Exception as e:
            return {"error": str(e)}

    def calculate_overdue_stats(
        self,
        table: str,
        due_date_col: str = "due_date",
        status_col: str = "status",
        open_statuses: Optional[List[str]] = None
    ) -> Dict:
        """Calculate overdue statistics"""
        try:
            if open_statuses is None:
                open_statuses = ["open", "in_progress", "draft"]

            # Get total open items
            total_df = self.qe.query(table, {status_col: open_statuses})
            total_open = len(total_df)

            # Get overdue items
            overdue_df = self.qe.get_overdue(
                table,
                due_date_col=due_date_col,
                status_col=status_col,
                open_statuses=open_statuses
            )
            total_overdue = len(overdue_df)

            # Calculate average days overdue
            avg_days_overdue = 0
            if 'days_overdue' in overdue_df.columns and len(overdue_df) > 0:
                avg_days_overdue = float(overdue_df['days_overdue'].mean())

            return {
                "total_open": total_open,
                "total_overdue": total_overdue,
                "overdue_percentage": round((total_overdue / total_open) * 100, 2) if total_open > 0 else 0,
                "avg_days_overdue": round(avg_days_overdue, 1)
            }
        except Exception as e:
            return {"error": str(e)}

    def cross_tabulate(
        self,
        table: str,
        row_column: str,
        col_column: str,
        filters: Optional[Dict] = None
    ) -> Dict:
        """Create a cross-tabulation of two columns"""
        try:
            df = self.qe.query(table, filters)

            if row_column not in df.columns or col_column not in df.columns:
                return {"error": "Column not found"}

            crosstab = pd.crosstab(df[row_column], df[col_column])

            return {
                "index": crosstab.index.tolist(),
                "columns": crosstab.columns.tolist(),
                "values": crosstab.values.tolist()
            }
        except Exception as e:
            return {"error": str(e)}
