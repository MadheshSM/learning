"""Load and manage Excel data files"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ExcelDataLoader:
    """Load and manage Excel data files exported from ACC"""

    def __init__(self, data_directory: str = "data"):
        self.data_dir = Path(data_directory)
        self.dataframes: Dict[str, pd.DataFrame] = {}

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all Excel files from data directory"""
        if not self.data_dir.exists():
            logger.warning(f"Data directory '{self.data_dir}' does not exist")
            return self.dataframes

        excel_files = list(self.data_dir.glob("*.xlsx"))

        for file_path in excel_files:
            name = file_path.stem  # filename without extension
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                # Convert date columns
                df = self._convert_dates(df)
                self.dataframes[name] = df
                logger.info(f"Loaded {name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        return self.dataframes

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-convert date columns based on column names"""
        date_keywords = ['date', 'start', 'end', 'created', 'updated', 'due', 'closed']

        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass  # Skip if conversion fails
        return df

    def get_dataframe(self, name: str) -> Optional[pd.DataFrame]:
        """Get a specific dataframe by name"""
        return self.dataframes.get(name)

    def reload(self, name: str) -> Optional[pd.DataFrame]:
        """Reload a specific Excel file"""
        file_path = self.data_dir / f"{name}.xlsx"
        if file_path.exists():
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                df = self._convert_dates(df)
                self.dataframes[name] = df
                logger.info(f"Reloaded {name}: {len(df)} rows")
                return df
            except Exception as e:
                logger.error(f"Failed to reload {name}: {e}")
        return None

    def get_table_names(self) -> List[str]:
        """Get list of loaded table names"""
        return list(self.dataframes.keys())

    def get_schema(self, name: str) -> Optional[Dict]:
        """Get schema information for a table"""
        df = self.dataframes.get(name)
        if df is None:
            return None

        schema = {
            'name': name,
            'row_count': len(df),
            'columns': []
        }

        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'non_null_count': int(df[col].count()),
                'null_count': int(df[col].isnull().sum())
            }

            # Add unique values for categorical columns
            if df[col].dtype == 'object' and df[col].nunique() < 20:
                col_info['unique_values'] = df[col].dropna().unique().tolist()

            schema['columns'].append(col_info)

        return schema
