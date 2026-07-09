"""Load and manage ERP Excel data files (Project Plan, BOM, ERP Costing)"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List
import logging
import warnings
import shutil

logger = logging.getLogger(__name__)

# Default ERP data directory
DEFAULT_ERP_DIR = "erp"


class ERPDataLoader:
    """Load and manage ERP Excel data files.

    Three source files:
      - project_plan.xlsx: Tasks with WBSCode (float, e.g. 1.1), dates, durations
      - bom.xlsx: Bill of Materials with WBSCode (string, e.g. "WBS-1.1"), ItemCode
      - erp_costing.xlsx: Cost data with ItemCode (e.g. "MAT-CEM-OPC43")

    Relationships:
      - project_plan <-> bom: linked via WBSCode (after normalization)
      - bom <-> erp_costing: linked via ItemCode
    """

    EXPECTED_FILES = ["project_plan.xlsx", "bom.xlsx", "erp_costing.xlsx"]

    def __init__(self, erp_directory: str = DEFAULT_ERP_DIR):
        self.erp_dir = Path(erp_directory)
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.source_files: Dict[str, str] = {}

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all ERP Excel files and create derived joined tables."""
        if not self.erp_dir.exists():
            logger.warning(f"ERP directory '{self.erp_dir}' does not exist")
            return self.dataframes

        for filename in self.EXPECTED_FILES:
            file_path = self.erp_dir / filename
            table_name = file_path.stem  # project_plan, bom, erp_costing
            if not file_path.exists():
                logger.warning(f"ERP file not found: {file_path}")
                continue
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
                df = self._convert_dates(df)
                self.dataframes[table_name] = df
                self.source_files[table_name] = str(file_path)
                logger.info(f"ERP: Loaded {table_name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"ERP: Failed to load {file_path}: {e}")

        # Normalize WBSCode so project_plan and bom can be joined
        self._normalize_wbs_codes()

        # Create derived joined tables for easier querying
        self._create_joined_tables()

        return self.dataframes

    def _normalize_wbs_codes(self):
        """Normalize WBSCode columns so project_plan and bom can be joined.

        project_plan has WBSCode as float (1.0, 1.1, 2.1, ...)
        bom has WBSCode as string ("WBS-1.1", "WBS-2.1", ...)

        We add a normalized 'WBSCodeNorm' column to both tables as string "X.Y".
        """
        if "project_plan" in self.dataframes:
            df = self.dataframes["project_plan"]
            # Convert float WBSCode to string like "1.1"
            df["WBSCodeNorm"] = df["WBSCode"].apply(
                lambda x: str(x) if pd.notna(x) else ""
            )
            self.dataframes["project_plan"] = df

        if "bom" in self.dataframes:
            df = self.dataframes["bom"]
            # Strip "WBS-" prefix to get "1.1" from "WBS-1.1"
            df["WBSCodeNorm"] = df["WBSCode"].apply(
                lambda x: str(x).replace("WBS-", "") if pd.notna(x) else ""
            )
            self.dataframes["bom"] = df

    def _create_joined_tables(self):
        """Create pre-joined tables for cross-table queries."""

        # 1. plan_bom: project_plan joined with bom on WBSCodeNorm
        if "project_plan" in self.dataframes and "bom" in self.dataframes:
            try:
                plan = self.dataframes["project_plan"]
                bom = self.dataframes["bom"]
                plan_bom = pd.merge(
                    plan, bom,
                    on="WBSCodeNorm",
                    how="inner",
                    suffixes=("_plan", "_bom"),
                )
                self.dataframes["plan_bom"] = plan_bom
                self.source_files["plan_bom"] = "derived: project_plan + bom"
                logger.info(f"ERP: Created plan_bom join: {len(plan_bom)} rows")
            except Exception as e:
                logger.error(f"ERP: Failed to create plan_bom join: {e}")

        # 2. plan_bom_cost: full chain project_plan -> bom -> erp_costing
        if "plan_bom" in self.dataframes and "erp_costing" in self.dataframes:
            try:
                plan_bom = self.dataframes["plan_bom"]
                costing = self.dataframes["erp_costing"]
                # bom.ItemCode maps semantically to erp_costing.ItemCode
                # But they use different code systems (BOQ- vs MAT-).
                # We'll keep both tables available for the agent to reason over.
                # For a direct join we provide the full chain as separate tables.
                self.dataframes["erp_costing_summary"] = costing.copy()
                self.source_files["erp_costing_summary"] = self.source_files.get("erp_costing", "")
                logger.info("ERP: erp_costing_summary available for agent reasoning")
            except Exception as e:
                logger.error(f"ERP: Failed to create cost summary: {e}")

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-convert date columns based on column names."""
        date_keywords = ["date", "start", "end", "finish", "created", "updated", "due"]
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
        return df

    def get_table_names(self) -> List[str]:
        return list(self.dataframes.keys())

    def get_dataframe(self, name: str) -> Optional[pd.DataFrame]:
        return self.dataframes.get(name)

    def get_all_source_files(self) -> Dict[str, str]:
        return self.source_files.copy()

    def save_uploaded_file(self, filename: str, content: bytes) -> bool:
        """Save an uploaded Excel file to the ERP directory."""
        valid_names = {f.replace(".xlsx", "") for f in self.EXPECTED_FILES}
        stem = filename.replace(".xlsx", "").replace(".xls", "")
        if stem not in valid_names:
            logger.warning(f"ERP: Rejected upload with invalid filename: {filename}")
            return False

        self.erp_dir.mkdir(parents=True, exist_ok=True)
        target = self.erp_dir / f"{stem}.xlsx"

        # Backup existing file
        if target.exists():
            backup = self.erp_dir / f"{stem}_backup.xlsx"
            shutil.copy2(target, backup)
            logger.info(f"ERP: Backed up {target} to {backup}")

        target.write_bytes(content)
        logger.info(f"ERP: Saved uploaded file to {target}")
        return True

    def reload(self) -> Dict[str, pd.DataFrame]:
        """Reload all ERP data from disk."""
        self.dataframes.clear()
        self.source_files.clear()
        return self.load_all()

    def get_schema(self, name: str) -> Optional[Dict]:
        """Get schema information for a table."""
        df = self.dataframes.get(name)
        if df is None:
            return None

        schema = {
            "name": name,
            "source_file": self.source_files.get(name),
            "row_count": len(df),
            "columns": [],
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].count()),
                "null_count": int(df[col].isnull().sum()),
            }
            if df[col].dtype == "object" and df[col].nunique() < 20:
                col_info["unique_values"] = df[col].dropna().unique().tolist()
            schema["columns"].append(col_info)

        return schema
