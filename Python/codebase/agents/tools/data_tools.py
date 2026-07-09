"""Data query tools for agents"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from data_layer.query_engine import QueryEngine
from data_layer.time_period_parser import TimePeriodContext


def clean_for_json(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to list of dicts, replacing NaN with None for JSON compatibility"""
    # Replace NaN, NaT, inf with None
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
    # Convert NaT (datetime NaN) to None
    for col in df.select_dtypes(include=['datetime64[ns]']).columns:
        df[col] = df[col].astype(object).where(df[col].notna(), None)
    return df.to_dict('records')


class DataTools:
    """Tools for querying and retrieving data from DataFrames"""

    def __init__(self, query_engine: QueryEngine):
        self.qe = query_engine

    def query_table(
        self,
        table: str,
        filters: Optional[Dict] = None,
        columns: Optional[List[str]] = None,
        limit: int = 100,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Query a table with optional filters and column selection

        Returns dict with:
            - source_file: path to the source CSV/Excel file
            - table: table name
            - total_rows: total rows in table (before limit)
            - returned_rows: number of rows returned
            - data: list of records
        """
        try:
            df = self.qe.query(table, filters, columns, limit)
            
            # Exclude actual_start_date and actual_end_date columns from RFA data before passing to LLM
            if table == "rfas":
                columns_to_exclude = ["actual_start_date", "actual_end_date"]
                df = df.drop(columns=[col for col in columns_to_exclude if col in df.columns], errors='ignore')
            
            records = clean_for_json(df)

            if include_metadata:
                # Get total count before limit was applied
                total_df = self.qe.query(table, filters)
                return {
                    "source_file": self.qe.get_source_file(table),
                    "table": table,
                    "total_rows": len(total_df),
                    "returned_rows": len(records),
                    "data": records
                }
            return records
        except Exception as e:
            return {"error": str(e)}

    def get_table_schema(self, table: str) -> Dict:
        """Get schema information for a table"""
        try:
            stats = self.qe.get_summary_stats(table)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "row_count": stats['total_rows'],
                "columns": stats['columns'],
                "categorical_values": stats.get('categorical_summary', {})
            }
        except Exception as e:
            return {"error": str(e)}

    def get_overdue_items(
        self,
        table: str,
        due_date_col: str = "due_date",
        status_col: str = "status",
        open_statuses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get overdue items from a table"""
        try:
            if open_statuses is None:
                open_statuses = ["open", "in_progress", "draft"]

            df = self.qe.get_overdue(
                table,
                due_date_col=due_date_col,
                status_col=status_col,
                open_statuses=open_statuses
            )
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "total_overdue": len(records),
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def search_text(
        self,
        table: str,
        column: str,
        search_term: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search for text in a specific column"""
        try:
            df = self.qe.query(table, {column: {"contains": search_term}}, limit=limit)
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "search_column": column,
                "search_term": search_term,
                "returned_rows": len(records),
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def get_date_range_data(
        self,
        table: str,
        date_column: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Get data within a date range"""
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)

            df = self.qe.query(table, {
                date_column: {"between": [start, end]}
            })
            records = clean_for_json(df)
            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "date_range": {"start": start_date, "end": end_date},
                "returned_rows": len(records),
                "data": records
            }
        except Exception as e:
            return {"error": str(e)}

    def get_data_by_period(
        self,
        table: str,
        date_column: str,
        period: TimePeriodContext,
        *,
        columns: Optional[List[str]] = None,
        limit: int = 200,
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Filter a table to a normalized period (week/month/quarter/year/custom).

        Returns JSON-serializable records + metadata.
        """
        try:
            start = datetime.fromisoformat(period.start_date)
            end = datetime.fromisoformat(period.end_date)

            filters: Dict[str, Any] = {date_column: {"between": [start, end]}}
            if extra_filters:
                # Merge shallowly; period filter always wins for date_column
                filters.update(extra_filters)
                filters[date_column] = {"between": [start, end]}

            # Reuse query_table for limit + metadata
            return self.query_table(
                table,
                filters=filters,
                columns=columns,
                limit=limit,
                include_metadata=True,
            )
        except Exception as e:
            return {"error": str(e)}

    def get_trend_over_period(
        self,
        table: str,
        date_column: str,
        group_period: str,
        period: TimePeriodContext,
        *,
        count_column: Optional[str] = None,
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a trend grouped by `group_period` (daily/weekly/monthly/quarterly/yearly)
        restricted to the provided period boundaries.
        """
        try:
            start = datetime.fromisoformat(period.start_date)
            end = datetime.fromisoformat(period.end_date)

            filters: Dict[str, Any] = {date_column: {"between": [start, end]}}
            if extra_filters:
                filters.update(extra_filters)
                filters[date_column] = {"between": [start, end]}

            df = self.qe.get_trend_data(
                table=table,
                date_column=date_column,
                period=group_period,
                count_column=count_column,
                filters=filters,
            )
            records = clean_for_json(df)

            return {
                "source_file": self.qe.get_source_file(table),
                "table": table,
                "period": group_period,
                "date_column": date_column,
                "data": records,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_unique_values(self, table: str, column: str) -> List[Any]:
        """Get unique values from a column"""
        try:
            df = self.qe.query(table, columns=[column])
            return df[column].dropna().unique().tolist()
        except Exception as e:
            return {"error": str(e)}

    def count_by_status(self, table: str, status_column: str = "status") -> Dict[str, int]:
        """Count items by status"""
        try:
            df = self.qe.group_and_count(table, status_column)
            return dict(zip(df[status_column], df['count']))
        except Exception as e:
            return {"error": str(e)}

    def get_available_tables(self) -> List[str]:
        """Get list of available tables"""
        return self.qe.get_tables()
