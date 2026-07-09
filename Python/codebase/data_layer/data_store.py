"""In-memory data store for managing DataFrames"""
import pandas as pd
from typing import Dict, Optional, List, Any
from pathlib import Path
import logging
from .csv_loader import CSVDataLoader
from .excel_loader import ExcelDataLoader
from .query_engine import QueryEngine

logger = logging.getLogger(__name__)


class DataStore:
    """Central data store managing all loaded DataFrames"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for data store"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_directory: str = "data", extraction_folder: str = "Data extraction 29.08.25"):
        if self._initialized:
            return

        self.data_directory = data_directory
        self.extraction_folder = extraction_folder
        # Use CSV loader for ACC data extraction (primary)
        self.loader = CSVDataLoader(data_directory, extraction_folder)
        # Keep Excel loader as fallback
        self.excel_loader = ExcelDataLoader(data_directory)
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.query_engine: Optional[QueryEngine] = None
        self._initialized = True

    def initialize(self) -> bool:
        """Load all data and initialize query engine"""
        try:
            self.dataframes = self.loader.load_all()
            self.query_engine = QueryEngine(self.dataframes)
            logger.info(f"DataStore initialized with {len(self.dataframes)} tables")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DataStore: {e}")
            return False

    def reload_all(self) -> bool:
        """Reload all data from Excel files"""
        try:
            self.dataframes = self.loader.load_all()
            if self.query_engine:
                self.query_engine.update_dataframes(self.dataframes)
            logger.info(f"DataStore reloaded with {len(self.dataframes)} tables")
            return True
        except Exception as e:
            logger.error(f"Failed to reload DataStore: {e}")
            return False

    def reload_table(self, table_name: str) -> bool:
        """Reload a specific table"""
        df = self.loader.reload(table_name)
        if df is not None:
            self.dataframes[table_name] = df
            if self.query_engine:
                self.query_engine.update_dataframes(self.dataframes)
            return True
        return False

    def get_table(self, table_name: str) -> Optional[pd.DataFrame]:
        """Get a table by name"""
        return self.dataframes.get(table_name)

    def get_tables(self) -> List[str]:
        """Get list of available tables"""
        return list(self.dataframes.keys())

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a table"""
        df = self.dataframes.get(table_name)
        if df is None:
            return None

        return {
            'name': table_name,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'memory_usage': int(df.memory_usage(deep=True).sum())
        }

    def get_all_tables_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all tables"""
        return {
            name: self.get_table_info(name)
            for name in self.dataframes.keys()
        }

    def get_query_engine(self) -> Optional[QueryEngine]:
        """Get the query engine instance"""
        return self.query_engine

    def add_dataframe(self, name: str, df: pd.DataFrame) -> None:
        """Add a new DataFrame to the store"""
        self.dataframes[name] = df
        if self.query_engine:
            self.query_engine.update_dataframes(self.dataframes)

    def remove_table(self, table_name: str) -> bool:
        """Remove a table from the store"""
        if table_name in self.dataframes:
            del self.dataframes[table_name]
            if self.query_engine:
                self.query_engine.update_dataframes(self.dataframes)
            return True
        return False
