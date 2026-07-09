"""Data schemas and validation for Excel data"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums for status fields
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RFIStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class IncidentType(str, Enum):
    INJURY = "injury"
    NEAR_MISS = "near_miss"
    OBSERVATION = "observation"


class Severity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


# Pydantic models for data validation
class Project(BaseModel):
    project_id: str
    project_name: str
    status: ProjectStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    project_manager: Optional[str] = None
    budget: Optional[float] = None


class Issue(BaseModel):
    issue_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: IssueStatus
    priority: Priority
    issue_type: Optional[str] = None
    assignee: Optional[str] = None
    created_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    location: Optional[str] = None


class RFI(BaseModel):
    rfi_id: str
    project_id: str
    title: str
    status: RFIStatus
    priority: Priority
    discipline: Optional[str] = None
    submitted_by: Optional[str] = None
    assigned_to: Optional[str] = None
    created_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    days_open: Optional[int] = None


class SafetyIncident(BaseModel):
    incident_id: str
    project_id: str
    incident_type: IncidentType
    severity: Severity
    description: Optional[str] = None
    location: Optional[str] = None
    date: Optional[datetime] = None
    reported_by: Optional[str] = None
    status: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None


class ScheduleTask(BaseModel):
    task_id: str
    project_id: str
    task_name: str
    phase: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    percent_complete: Optional[float] = Field(None, ge=0, le=100)
    status: TaskStatus
    delay_days: Optional[int] = None
    is_milestone: Optional[bool] = False
    predecessor: Optional[str] = None


# Schema definitions for expected columns (mapped from ACC data extraction)
EXPECTED_SCHEMAS = {
    'projects': {
        'required': ['project_id', 'project_name', 'status'],
        'optional': ['start_date', 'end_date', 'location', 'project_type', 'budget', 'currency', 'team_size', 'company_count'],
        'date_columns': ['start_date', 'end_date'],
        'numeric_columns': ['budget', 'team_size', 'company_count']
    },
    'issues': {
        'required': ['issue_id', 'project_id', 'title', 'status'],
        'optional': ['description', 'display_id', 'issue_type_id', 'issue_subtype_id', 'assignee', 'owner',
                    'created_date', 'due_date', 'closed_date', 'updated_date', 'start_date', 'location', 'root_cause'],
        'date_columns': ['created_date', 'due_date', 'closed_date', 'updated_date', 'start_date'],
        'numeric_columns': []
    },
    'rfis': {
        'required': ['rfi_id', 'project_id', 'title', 'status'],
        'optional': ['rfi_number', 'question', 'priority', 'submitted_by', 'assigned_to',
                    'created_date', 'due_date', 'response_date', 'closed_date',
                    'cost_impact', 'schedule_impact', 'rfi_type', 'response'],
        'date_columns': ['created_date', 'due_date', 'response_date', 'closed_date'],
        'numeric_columns': []
    },
    'rfas': {
        'required': ['rfa_id', 'project_id', 'title'],
        'optional': ['rfa_code', 'status', 'priority', 'start_date', 'due_date',
                    'lagged_days', 'worklog_hours', 'work_hours', 'progress',
                    'review_step', 'review_status', 'created_date', 'updated_date'],
        'date_columns': ['start_date', 'due_date', 'created_date', 'updated_date'],
        'numeric_columns': ['lagged_days', 'worklog_hours', 'work_hours', 'progress']
    },
    'submittals': {
        'required': ['submittal_id', 'project_id', 'title'],
        'optional': ['submittal_number', 'description', 'status', 'submittal_type', 'priority',
                    'due_date', 'created_date', 'updated_date', 'manager', 'subcontractor', 'response', 'revision'],
        'date_columns': ['due_date', 'created_date', 'updated_date'],
        'numeric_columns': ['revision']
    },
    'schedule': {
        'required': ['task_id', 'project_id', 'task_name'],
        'optional': ['task_type', 'phase', 'planned_start', 'planned_end', 'actual_start', 'actual_end',
                    'percent_complete', 'is_critical', 'duration', 'remaining_duration', 'is_wbs', 'wbs_code'],
        'date_columns': ['planned_start', 'planned_end', 'actual_start', 'actual_end'],
        'numeric_columns': ['percent_complete', 'duration', 'remaining_duration']
    },
    'users': {
        'required': ['user_id', 'email', 'name'],
        'optional': ['autodesk_id', 'first_name', 'last_name', 'job_title', 'status', 'is_account_admin', 'is_project_admin'],
        'date_columns': [],
        'numeric_columns': []
    },
    'safety_observations': {
        'required': ['id', 'bim360_project_id'],
        'optional': ['safety_observation_category', 'updated_at', 'predicted_at'],
        'date_columns': ['updated_at', 'predicted_at'],
        'numeric_columns': []
    },
    'documents': {
        'required': ['document_id', 'project_id', 'title'],
        'optional': [
            'document_code', 'version', 'revision', 'updated_date', 'updated_by', 'document_type',
            'folder', 'project_name', 'size_mb', 'review_workflow', 'current_step', 'discipline_or_type',
            'discipline', 'checked_out_by', 'file_url', 'file_path', 'file_extension',
        ],
        'date_columns': ['updated_date'],
        'numeric_columns': ['size_mb']
    }
}


def validate_dataframe_schema(df, table_name: str) -> Dict[str, Any]:
    """Validate a DataFrame against expected schema"""
    if table_name not in EXPECTED_SCHEMAS:
        return {'valid': True, 'warnings': [], 'errors': []}

    schema = EXPECTED_SCHEMAS[table_name]
    errors = []
    warnings = []

    # Check required columns
    for col in schema['required']:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Check optional columns
    for col in schema['optional']:
        if col not in df.columns:
            warnings.append(f"Missing optional column: {col}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'found_columns': list(df.columns),
        'expected_required': schema['required'],
        'expected_optional': schema['optional']
    }
