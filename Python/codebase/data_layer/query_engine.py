"""Query engine for executing queries against Excel DataFrames"""
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta


class QueryEngine:
    """Execute queries against Excel DataFrames"""

    def __init__(self, dataframes: Dict[str, pd.DataFrame], source_files: Optional[Dict[str, str]] = None):
        self.dfs = dataframes
        self.source_files = source_files or {}

    def update_dataframes(self, dataframes: Dict[str, pd.DataFrame], source_files: Optional[Dict[str, str]] = None):
        """Update the dataframes reference"""
        self.dfs = dataframes
        if source_files:
            self.source_files = source_files

    def get_tables(self) -> List[str]:
        """Get list of available tables"""
        return list(self.dfs.keys())

    def get_source_file(self, table: str) -> Optional[str]:
        """Get source file for a table"""
        return self.source_files.get(table)

    def query(
        self,
        table: str,
        filters: Optional[Dict] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """Query a table with optional filters, column selection, and ordering"""
        if table not in self.dfs:
            raise ValueError(f"Table '{table}' not found. Available: {list(self.dfs.keys())}")

        df = self.dfs[table].copy()
        # Apply filters
        if filters:
            df = self._apply_filters(df, filters)

        # Select columns
        if columns:
            available_cols = [c for c in columns if c in df.columns]
            df = df[available_cols]

        # Order by
        if order_by and order_by in df.columns:
            df = df.sort_values(by=order_by, ascending=ascending)

        # Limit results
        if limit:
            df = df.head(limit)

        return df

    def _apply_filters(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply filters to a DataFrame"""
        for col, value in filters.items():
            if col not in df.columns:
                continue

            if isinstance(value, list):
                # IN clause
                df = df[df[col].isin(value)]
            elif isinstance(value, dict):
                # Operators: gt, lt, gte, lte, ne, contains, between
                for op, val in value.items():
                    if op == 'gt':
                        df = df[df[col] > val]
                    elif op == 'lt':
                        df = df[df[col] < val]
                    elif op == 'gte':
                        df = df[df[col] >= val]
                    elif op == 'lte':
                        df = df[df[col] <= val]
                    elif op == 'ne':
                        df = df[df[col] != val]
                    elif op == 'contains':
                        df = df[df[col].str.contains(str(val), case=False, na=False)]
                    elif op == 'between':
                        if isinstance(val, (list, tuple)) and len(val) == 2:
                            df = df[(df[col] >= val[0]) & (df[col] <= val[1])]
                    elif op == 'is_null':
                        if val:
                            df = df[df[col].isnull()]
                        else:
                            df = df[df[col].notnull()]
            else:
                # Exact match
                df = df[df[col] == value]

        return df

    def group_and_count(
        self,
        table: str,
        group_by: Union[str, List[str]],
        filters: Optional[Dict] = None
    ) -> pd.DataFrame:
        """Group by column(s) and count occurrences"""
        df = self.query(table, filters)

        if isinstance(group_by, str):
            group_by = [group_by]

        # Filter to valid columns
        valid_cols = [c for c in group_by if c in df.columns]
        if not valid_cols:
            raise ValueError(f"No valid columns for grouping. Available: {list(df.columns)}")

        result = df.groupby(valid_cols).size().reset_index(name='count')
        return result.sort_values('count', ascending=False)

    def aggregate(
        self,
        table: str,
        group_by: Union[str, List[str]],
        agg_column: str,
        agg_func: str = 'sum',
        filters: Optional[Dict] = None
    ) -> pd.DataFrame:
        """Group and aggregate with various functions"""
        df = self.query(table, filters)

        if isinstance(group_by, str):
            group_by = [group_by]

        valid_cols = [c for c in group_by if c in df.columns]
        if not valid_cols:
            raise ValueError(f"No valid columns for grouping")

        if agg_column not in df.columns:
            raise ValueError(f"Aggregation column '{agg_column}' not found")

        agg_funcs = {
            'sum': 'sum',
            'avg': 'mean',
            'mean': 'mean',
            'min': 'min',
            'max': 'max',
            'count': 'count',
            'std': 'std',
            'median': 'median'
        }

        if agg_func.lower() not in agg_funcs:
            raise ValueError(f"Unknown aggregation function: {agg_func}")

        result = df.groupby(valid_cols)[agg_column].agg(agg_funcs[agg_func.lower()])
        return result.reset_index()

    def get_overdue(
        self,
        table: str,
        due_date_col: str = 'due_date',
        status_col: str = 'status',
        open_statuses: Optional[List[str]] = None,
        as_of_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get overdue items based on due date and status"""
        if table not in self.dfs:
            raise ValueError(f"Table '{table}' not found")

        df = self.dfs[table].copy()
        today = as_of_date or datetime.now()

        # Filter open items if status column exists
        if status_col in df.columns and open_statuses:
            df = df[df[status_col].isin(open_statuses)]

        # Filter overdue items
        if due_date_col in df.columns:
            df = df[df[due_date_col] < today]
            df = df[df[due_date_col].notna()]

            # Calculate days overdue
            df['days_overdue'] = (today - df[due_date_col]).dt.days

        return df

    def get_relevant_date_field(
        self,
        table: str,
        query_context: str,
        preferred_field: Optional[str] = None,
    ) -> str:
        """
        Choose the most relevant date column for a query.

        Heuristics (works with the standardized ACC column mappings):
        - due/overdue/deadline -> due_date
        - created/submitted/new/open -> created_date (fallback to start_date)
        - updated/recent/activity -> updated_date
        - schedule/task start/end keywords -> planned_start/planned_end/actual_start/actual_end
        """
        if table not in self.dfs:
            raise ValueError(f"Table '{table}' not found. Available: {list(self.dfs.keys())}")

        df = self.dfs[table]
        cols = set(df.columns)
        if preferred_field and preferred_field in cols:
            return preferred_field

        q = (query_context or "").lower()

        # Schedule-specific keywords
        if table == "schedule":
            if any(k in q for k in ["planned start", "start date", "planned_start", "began", "begin"]):
                for c in ["planned_start", "actual_start", "start_date"]:
                    if c in cols:
                        return c
            if any(k in q for k in ["planned end", "end date", "planned_end", "due", "finish", "complete"]):
                for c in ["planned_end", "actual_end", "due_date", "end_date"]:
                    if c in cols:
                        return c

        # Generic due/deadline semantics
        if any(k in q for k in ["overdue", "due", "deadline", "over due"]):
            for c in ["due_date", "planned_end", "actual_end", "end_date"]:
                if c in cols:
                    return c

        # Created/submitted/open semantics
        if any(k in q for k in ["created", "submitted", "new", "opened", "open ", "draft", "reported", "start"]):
            for c in ["created_date", "start_date", "planned_start", "actual_start", "response_date"]:
                if c in cols:
                    return c

        # Updated/recent semantics
        if any(k in q for k in ["updated", "recent", "activity", "progress", "changed"]):
            for c in ["updated_date", "closed_date", "response_date"]:
                if c in cols:
                    return c

        # Fallback priority
        for c in [
            "due_date",
            "created_date",
            "updated_date",
            "closed_date",
            "response_date",
            "start_date",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
        ]:
            if c in cols:
                return c

        # Last resort
        # Pick first datetime column if present.
        datetime_cols = [c for c in df.columns if str(df[c].dtype).startswith("datetime")]
        if datetime_cols:
            return datetime_cols[0]

        raise ValueError(f"No date-like columns found in table '{table}'. Columns: {list(df.columns)}")

    def get_summary_stats(self, table: str) -> Dict[str, Any]:
        """Get comprehensive summary statistics for a table"""
        if table not in self.dfs:
            raise ValueError(f"Table '{table}' not found")

        df = self.dfs[table]

        summary = {
            'table_name': table,
            'source_file': self.source_files.get(table),
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'date_range': self._get_date_range(df),
            'categorical_summary': self._get_categorical_summary(df),
            'numeric_summary': self._get_numeric_summary(df)
        }

        return summary

    def query_with_metadata(
        self,
        table: str,
        filters: Optional[Dict] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        ascending: bool = True,
        include_raw: bool = True
    ) -> Dict[str, Any]:
        """Query a table and return results with metadata including source file"""
        df = self.query(table, filters, columns, limit, order_by, ascending)

        result = {
            'table': table,
            'source_file': self.source_files.get(table),
            'total_rows': len(self.dfs.get(table, [])),
            'returned_rows': len(df),
            'columns': list(df.columns),
        }

        if include_raw:
            # Include raw data as list of records
            result['raw_data'] = df.to_dict('records')

        return result

    def _get_date_range(self, df: pd.DataFrame) -> Dict:
        """Get date range from date columns"""
        result = {}
        date_cols = df.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns

        for col in date_cols:
            valid_dates = df[col].dropna()
            if len(valid_dates) > 0:
                result[col] = {
                    'min': valid_dates.min().isoformat(),
                    'max': valid_dates.max().isoformat(),
                    'count': len(valid_dates)
                }

        return result

    def _get_categorical_summary(self, df: pd.DataFrame) -> Dict:
        """Get value counts for categorical columns"""
        result = {}
        for col in df.select_dtypes(include=['object']).columns:
            unique_count = df[col].nunique()
            if unique_count < 20:  # Only for low cardinality
                result[col] = df[col].value_counts().to_dict()
        return result

    def _get_numeric_summary(self, df: pd.DataFrame) -> Dict:
        """Get statistics for numeric columns"""
        result = {}
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            result[col] = {
                'min': float(df[col].min()) if pd.notna(df[col].min()) else None,
                'max': float(df[col].max()) if pd.notna(df[col].max()) else None,
                'mean': float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                'sum': float(df[col].sum()) if pd.notna(df[col].sum()) else None
            }
        return result

    def join_tables(
        self,
        left_table: str,
        right_table: str,
        on: str,
        how: str = 'inner'
    ) -> pd.DataFrame:
        """Join two tables"""
        if left_table not in self.dfs:
            raise ValueError(f"Table '{left_table}' not found")
        if right_table not in self.dfs:
            raise ValueError(f"Table '{right_table}' not found")

        left_df = self.dfs[left_table]
        right_df = self.dfs[right_table]

        return pd.merge(left_df, right_df, on=on, how=how)

    def get_trend_data(
        self,
        table: str,
        date_column: str,
        period: str = 'daily',
        count_column: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> pd.DataFrame:
        """Get trend data grouped by time period"""
        df = self.query(table, filters)

        if date_column not in df.columns:
            raise ValueError(f"Date column '{date_column}' not found")

        df = df[df[date_column].notna()].copy()

        # Set period frequency
        freq_map = {
            'daily': 'D',
            'weekly': 'W',
            'monthly': 'M',
            'quarterly': 'Q',
            'yearly': 'Y'
        }

        freq = freq_map.get(period, 'D')
        df['period'] = df[date_column].dt.to_period(freq)

        if count_column and count_column in df.columns:
            result = df.groupby('period')[count_column].sum().reset_index()
        else:
            result = df.groupby('period').size().reset_index(name='count')

        result['period'] = result['period'].astype(str)
        return result
