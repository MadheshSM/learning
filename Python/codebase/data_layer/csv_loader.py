"""Load and manage CSV data files from ACC Data Extraction"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List
import logging
import warnings

logger = logging.getLogger(__name__)


# Mapping from ACC CSV files to standardized table names
FILE_TO_TABLE_MAPPING = {
    'admin_projects': 'projects',
    'admin_users': 'users',
    'admin_project_users': 'project_users',
    'admin_companies': 'companies',
    'issues_issues': 'issues',
    'issues_issue_types': 'issue_types',
    'issues_issue_subtypes': 'issue_subtypes',
    'rfis_rfis': 'rfis',
    'rfis_rfi_types': 'rfi_types',
    'submittalsacc_items': 'submittals',
    'submittalsacc_specs': 'submittal_specs',
    'schedule_activities': 'schedule',
    'schedule_schedules': 'schedules',
    'schedule_dependencies': 'schedule_dependencies',
    'schedule_activity_codes': 'schedule_activity_codes',
    'schedule_resources': 'schedule_resources',
    'schedule_comments': 'schedule_comments',
    'transmittals_workflow_transmittals': 'transmittals',
    'transmittals_transmittal_documents': 'transmittal_documents',
    'transmittals_transmittal_recipients': 'transmittal_recipients',
    'cost_budgets': 'budgets',
    'cost_contracts': 'contracts',
    'cost_change_orders': 'change_orders',
    'iq_issues_safety_observations': 'safety_observations',
}

# Column mappings from ACC format to standardized format
COLUMN_MAPPINGS = {
    'projects': {
        'id': 'project_id',
        'name': 'project_name',
        'status': 'status',
        'start_date': 'start_date',
        'end_date': 'end_date',
        'city': 'location',
        'type': 'project_type',
        'value': 'budget',
        'currency': 'currency',
        'total_member_size': 'team_size',
        'total_company_size': 'company_count',
    },
    'issues': {
        'issue_id': 'issue_id',
        'bim360_project_id': 'project_id',
        'display_id': 'display_id',
        'title': 'title',
        'description': 'description',
        'status': 'status',
        'type_id': 'issue_type_id',
        'subtype_id': 'issue_subtype_id',
        'assignee_id': 'assignee',
        'owner_id': 'owner',
        'due_date': 'due_date',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
        'closed_at': 'closed_date',
        'start_date': 'start_date',
        'location_id': 'location',
        'root_cause_id': 'root_cause',
    },
    'rfis': {
        'id': 'rfi_id',
        'bim360_project_id': 'project_id',
        'custom_identifier': 'rfi_number',
        'title': 'title',
        'question': 'question',
        'status': 'status',
        'priority': 'priority',
        'due_date': 'due_date',
        'created_at': 'created_date',
        'responded_at': 'response_date',
        'closed_at': 'closed_date',
        'created_by': 'submitted_by',
        'manager_id': 'assigned_to',
        'cost_impact': 'cost_impact',
        'schedule_impact': 'schedule_impact',
        'rfi_type': 'rfi_type',
        'official_response': 'response',
    },
    'submittals': {
        'id': 'submittal_id',
        'bim360_project_id': 'project_id',
        'identifier': 'submittal_number',
        'title': 'title',
        'description': 'description',
        'status_value': 'status',
        'type_value': 'submittal_type',
        'priority_value': 'priority',
        'due_date': 'due_date',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
        'manager': 'manager',
        'subcontractor': 'subcontractor',
        'response_value': 'response',
        'revision': 'revision',
    },
    'schedule': {
        'id': 'task_id',
        'bim360_project_id': 'project_id',
        'schedule_id': 'schedule_id',
        'unique_id': 'unique_id',
        'name': 'task_name',
        'type': 'task_type',
        'planned_start': 'planned_start',
        'planned_finish': 'planned_end',
        'actual_start': 'actual_start',
        'actual_finish': 'actual_end',
        'start': 'start_date',
        'finish': 'end_date',
        'completion_percentage': 'percent_complete',
        'is_critical_path': 'is_critical',
        'duration': 'duration',
        'actual_duration': 'actual_duration',
        'remaining_duration': 'remaining_duration',
        'is_wbs': 'is_wbs',
        'wbs_code': 'wbs_code',
        'wbs_path': 'wbs_path',
        'wbs_path_text': 'phase',
        'free_slack_duration': 'free_slack',
        'total_slack_duration': 'total_slack',
    },
    'schedule_dependencies': {
        'id': 'dependency_id',
        'schedule_id': 'schedule_id',
        'bim360_project_id': 'project_id',
        'source_unique_id': 'predecessor_id',
        'target_unique_id': 'successor_id',
        'type': 'dependency_type',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
    },
    'schedule_activity_codes': {
        'id': 'code_id',
        'schedule_id': 'schedule_id',
        'bim360_project_id': 'project_id',
        'activity_unique_id': 'task_unique_id',
        'name': 'code_name',
        'value': 'code_value',
        'value_description': 'code_description',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
    },
    'schedule_resources': {
        'id': 'resource_id',
        'schedule_id': 'schedule_id',
        'resource_unique_id': 'resource_unique_id',
        'bim360_project_id': 'project_id',
        'activity_unique_id': 'task_unique_id',
        'name': 'resource_name',
        'type': 'resource_type',
        'email_address': 'email',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
    },
    'schedule_comments': {
        'id': 'comment_id',
        'schedule_id': 'schedule_id',
        'bim360_project_id': 'project_id',
        'activity_unique_id': 'task_unique_id',
        'body': 'comment_text',
        'created_by': 'created_by',
        'created_at': 'created_date',
    },
    'transmittals': {
        'id': 'transmittal_id',
        'bim360_project_id': 'project_id',
        'sequence_id': 'sequence_id',
        'title': 'title',
        'status': 'status',
        'create_user_id': 'created_by_id',
        'create_user_name': 'created_by',
        'docs_count': 'docs_count',
        'created_at': 'created_date',
        'updated_at': 'updated_date',
        'create_user_company_id': 'company_id',
        'create_user_company_name': 'company_name',
    },
    'users': {
        'id': 'user_id',
        'autodesk_id': 'autodesk_id',
        'email': 'email',
        'name': 'name',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'job_title': 'job_title',
        'status': 'status',
        'access_level_account_admin': 'is_account_admin',
        'access_level_project_admin': 'is_project_admin',
    },
}


class CSVDataLoader:
    """Load and manage CSV data files from ACC Data Extraction"""

    def __init__(self, data_directory: str = "data", extraction_folder: str = "Data extraction 29.08.25"):
        self.data_dir = Path(data_directory)
        self.extraction_folder = extraction_folder
        self.extraction_path = self.data_dir / extraction_folder
        self.dataframes: Dict[str, pd.DataFrame] = {}
        # Track source file for each table
        self.source_files: Dict[str, str] = {}

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV files from the extraction directory"""
        if not self.extraction_path.exists():
            logger.warning(f"Extraction directory '{self.extraction_path}' does not exist")
            # Fall back to loading xlsx files from the main data directory
            return self._load_xlsx_fallback()

        csv_files = list(self.extraction_path.glob("*.csv"))
        logger.info(f"Found {len(csv_files)} CSV files in {self.extraction_path}")

        for file_path in csv_files:
            original_name = file_path.stem  # filename without extension
            # Map to standardized table name or use original
            table_name = FILE_TO_TABLE_MAPPING.get(original_name, original_name)

            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')

                # Skip empty files (only header row)
                if len(df) == 0:
                    logger.debug(f"Skipping empty file: {original_name}")
                    continue

                # Apply column mapping if available
                df = self._apply_column_mapping(df, table_name)

                # Convert date columns
                df = self._convert_dates(df)

                self.dataframes[table_name] = df
                # Track source file
                self.source_files[table_name] = str(file_path.relative_to(self.data_dir))
                logger.info(f"Loaded {table_name} (from {original_name}): {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        return self.dataframes

    def _load_xlsx_fallback(self) -> Dict[str, pd.DataFrame]:
        """Fall back to loading xlsx files if CSV extraction not found"""
        logger.info("Falling back to xlsx files in data directory")
        xlsx_files = list(self.data_dir.glob("*.xlsx"))

        for file_path in xlsx_files:
            name = file_path.stem
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                df = self._convert_dates(df)
                self.dataframes[name] = df
                self.source_files[name] = str(file_path.relative_to(self.data_dir))
                logger.info(f"Loaded {name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        return self.dataframes

    def _apply_column_mapping(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Apply column name mappings to standardize column names"""
        if table_name not in COLUMN_MAPPINGS:
            return df

        mapping = COLUMN_MAPPINGS[table_name]
        # Only rename columns that exist in the DataFrame
        rename_dict = {old: new for old, new in mapping.items() if old in df.columns}

        if rename_dict:
            df = df.rename(columns=rename_dict)
            logger.debug(f"Renamed {len(rename_dict)} columns in {table_name}")

        return df

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-convert date columns based on column names"""
        date_keywords = ['date', 'start', 'end', 'created', 'updated', 'due', 'closed',
                        'responded', 'opened', 'finish', '_at', 'sign_in']

        for col in df.columns:
            col_lower = col.lower()
            # Check if column name ends with date keywords or contains them
            if any(keyword in col_lower for keyword in date_keywords):
                try:
                    # Suppress the format inference warning
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass  # Skip if conversion fails
        return df

    def get_dataframe(self, name: str) -> Optional[pd.DataFrame]:
        """Get a specific dataframe by name"""
        return self.dataframes.get(name)

    def reload(self, name: str) -> Optional[pd.DataFrame]:
        """Reload a specific CSV file"""
        # Find original file name from mapping
        original_name = None
        for orig, mapped in FILE_TO_TABLE_MAPPING.items():
            if mapped == name:
                original_name = orig
                break

        if original_name is None:
            original_name = name

        file_path = self.extraction_path / f"{original_name}.csv"
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                df = self._apply_column_mapping(df, name)
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

    def get_source_file(self, table_name: str) -> Optional[str]:
        """Get the source file path for a table"""
        return self.source_files.get(table_name)

    def get_all_source_files(self) -> Dict[str, str]:
        """Get mapping of all tables to their source files"""
        return self.source_files.copy()

    def get_schema(self, name: str) -> Optional[Dict]:
        """Get schema information for a table"""
        df = self.dataframes.get(name)
        if df is None:
            return None

        schema = {
            'name': name,
            'source_file': self.source_files.get(name),
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

    def get_project_summary(self) -> Dict:
        """Get summary of projects and their related data"""
        projects_df = self.dataframes.get('projects')
        if projects_df is None:
            return {}

        summary = {
            'total_projects': len(projects_df),
            'projects': []
        }

        for _, project in projects_df.iterrows():
            project_id = project.get('project_id')
            project_info = {
                'id': project_id,
                'name': project.get('project_name'),
                'status': project.get('status'),
                'type': project.get('project_type'),
            }

            # Count related items
            for table_name in ['issues', 'rfis', 'submittals', 'schedule']:
                df = self.dataframes.get(table_name)
                if df is not None and 'project_id' in df.columns:
                    count = len(df[df['project_id'] == project_id])
                    project_info[f'{table_name}_count'] = count

            summary['projects'].append(project_info)

        return summary
