"""Pytest configuration and shared fixtures for ACC Dashboard tests"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import sys
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_layer.excel_loader import ExcelDataLoader
from data_layer.query_engine import QueryEngine
from data_layer.data_store import DataStore


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_projects_df():
    """Sample projects DataFrame"""
    return pd.DataFrame({
        'project_id': ['PROJ-001', 'PROJ-002', 'PROJ-003'],
        'project_name': ['Tower A', 'Tower B', 'Parking Structure'],
        'status': ['active', 'active', 'completed'],
        'start_date': pd.to_datetime(['2024-01-15', '2024-03-01', '2023-06-01']),
        'end_date': pd.to_datetime(['2025-06-30', '2025-09-30', '2024-08-31']),
        'location': ['Downtown', 'Midtown', 'Suburbs'],
        'project_manager': ['John Smith', 'Jane Doe', 'Bob Wilson'],
        'budget': [15000000, 22000000, 5000000]
    })


@pytest.fixture
def sample_issues_df():
    """Sample issues DataFrame"""
    return pd.DataFrame({
        'issue_id': ['ISS-001', 'ISS-002', 'ISS-003', 'ISS-004', 'ISS-005'],
        'project_id': ['PROJ-001', 'PROJ-001', 'PROJ-002', 'PROJ-002', 'PROJ-001'],
        'title': ['HVAC issue', 'Electrical problem', 'Water leak', 'Concrete crack', 'Paint defect'],
        'description': ['HVAC not working', 'Panel malfunction', 'Leak in basement', 'Crack observed', 'Quality issue'],
        'status': ['open', 'in_progress', 'resolved', 'open', 'closed'],
        'priority': ['high', 'critical', 'medium', 'high', 'low'],
        'issue_type': ['defect', 'defect', 'punch', 'defect', 'observation'],
        'assignee': ['John Smith', 'Jane Doe', 'Bob Wilson', 'John Smith', 'Jane Doe'],
        'created_date': pd.to_datetime([
            '2024-10-01', '2024-10-05', '2024-10-10', '2024-10-15', '2024-09-20'
        ]),
        'due_date': pd.to_datetime([
            '2024-10-15', '2024-10-12', '2024-10-25', '2024-10-20', '2024-10-01'
        ]),
        'closed_date': pd.to_datetime([None, None, None, None, '2024-10-02']),
        'location': ['Level 1', 'Level 2', 'Basement', 'Level 3', 'Exterior']
    })


@pytest.fixture
def sample_rfis_df():
    """Sample RFIs DataFrame"""
    return pd.DataFrame({
        'rfi_id': ['RFI-001', 'RFI-002', 'RFI-003', 'RFI-004'],
        'project_id': ['PROJ-001', 'PROJ-001', 'PROJ-002', 'PROJ-002'],
        'title': ['Clarification needed', 'Spec question', 'Material inquiry', 'Design conflict'],
        'status': ['open', 'answered', 'draft', 'closed'],
        'priority': ['high', 'medium', 'low', 'high'],
        'discipline': ['Electrical', 'Mechanical', 'Structural', 'Architectural'],
        'submitted_by': ['Contractor A', 'Contractor B', 'Contractor A', 'Contractor C'],
        'assigned_to': ['Architect', 'Engineer', 'Owner Rep', 'Architect'],
        'created_date': pd.to_datetime(['2024-10-01', '2024-10-05', '2024-10-10', '2024-09-15']),
        'due_date': pd.to_datetime(['2024-10-08', '2024-10-12', '2024-10-17', '2024-09-22']),
        'response_date': pd.to_datetime([None, '2024-10-11', None, '2024-09-20']),
        'days_open': [30, 0, 20, 0]
    })


@pytest.fixture
def sample_safety_incidents_df():
    """Sample safety incidents DataFrame"""
    return pd.DataFrame({
        'incident_id': ['INC-001', 'INC-002', 'INC-003', 'INC-004'],
        'project_id': ['PROJ-001', 'PROJ-001', 'PROJ-002', 'PROJ-002'],
        'incident_type': ['injury', 'near_miss', 'observation', 'near_miss'],
        'severity': ['minor', 'moderate', 'minor', 'severe'],
        'description': ['Slip hazard', 'Fall near miss', 'PPE violation', 'Equipment issue'],
        'location': ['Level 1', 'Level 2', 'Exterior', 'Basement'],
        'date': pd.to_datetime(['2024-10-01', '2024-10-05', '2024-10-10', '2024-10-12']),
        'reported_by': ['John Smith', 'Jane Doe', 'Safety Officer', 'Bob Wilson'],
        'status': ['closed', 'investigating', 'closed', 'open'],
        'root_cause': ['Procedural', 'Human Error', 'Training Gap', None],
        'corrective_action': ['Training provided', None, 'Warning issued', None]
    })


@pytest.fixture
def sample_schedule_df():
    """Sample schedule DataFrame"""
    return pd.DataFrame({
        'task_id': ['TSK-001', 'TSK-002', 'TSK-003', 'TSK-004', 'TSK-005'],
        'project_id': ['PROJ-001', 'PROJ-001', 'PROJ-001', 'PROJ-002', 'PROJ-002'],
        'task_name': ['Foundation', 'Structure', 'Envelope', 'Site Prep', 'Foundation'],
        'phase': ['Foundation', 'Structure', 'Envelope', 'Preconstruction', 'Foundation'],
        'planned_start': pd.to_datetime(['2024-01-15', '2024-03-01', '2024-06-01', '2024-03-01', '2024-04-15']),
        'planned_end': pd.to_datetime(['2024-02-28', '2024-05-31', '2024-08-31', '2024-03-31', '2024-06-30']),
        'actual_start': pd.to_datetime(['2024-01-15', '2024-03-05', None, '2024-03-01', '2024-04-20']),
        'actual_end': pd.to_datetime(['2024-03-05', None, None, '2024-04-05', None]),
        'percent_complete': [100, 75, 0, 100, 50],
        'status': ['completed', 'in_progress', 'not_started', 'delayed', 'in_progress'],
        'delay_days': [5, 0, 0, 5, 5],
        'is_milestone': [True, False, True, False, True],
        'predecessor': [None, 'TSK-001', 'TSK-002', None, 'TSK-004']
    })


@pytest.fixture
def sample_cost_df():
    """Sample cost DataFrame"""
    return pd.DataFrame({
        'cost_id': ['CST-001', 'CST-002', 'CST-003', 'CST-004', 'CST-005', 'CST-006'],
        'project_id': ['PROJ-001', 'PROJ-001', 'PROJ-001', 'PROJ-002', 'PROJ-002', 'PROJ-002'],
        'category': ['Labor', 'Materials', 'Equipment', 'Labor', 'Materials', 'Equipment'],
        'budgeted': [4500000, 5250000, 1500000, 6600000, 7700000, 2200000],
        'actual': [4800000, 5100000, 1400000, 6200000, 8000000, 2100000],
        'variance': [-300000, 150000, 100000, 400000, -300000, 100000],
        'variance_pct': [-6.67, 2.86, 6.67, 6.06, -3.90, 4.55],
        'forecast': [5000000, 5300000, 1450000, 6500000, 8200000, 2150000]
    })


@pytest.fixture
def sample_dataframes(
    sample_projects_df,
    sample_issues_df,
    sample_rfis_df,
    sample_safety_incidents_df,
    sample_schedule_df,
    sample_cost_df
):
    """Combined sample dataframes dictionary"""
    return {
        'projects': sample_projects_df,
        'issues': sample_issues_df,
        'rfis': sample_rfis_df,
        'safety_incidents': sample_safety_incidents_df,
        'schedule': sample_schedule_df,
        'cost': sample_cost_df
    }


@pytest.fixture
def query_engine(sample_dataframes):
    """QueryEngine instance with sample data"""
    return QueryEngine(sample_dataframes)


@pytest.fixture
def temp_data_dir(sample_dataframes):
    """Create temporary directory with Excel files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        for name, df in sample_dataframes.items():
            file_path = Path(tmp_dir) / f"{name}.xlsx"
            df.to_excel(file_path, index=False)
        yield tmp_dir


@pytest.fixture
def excel_loader(temp_data_dir):
    """ExcelDataLoader instance with temp directory"""
    loader = ExcelDataLoader(temp_data_dir)
    loader.load_all()
    return loader


class MockLLMResponse:
    """Mock LLM response for testing"""
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage = {"input_tokens": 100, "output_tokens": 50}
        self.model = "mock-model"
        self.finish_reason = "stop"


class MockToolCall:
    """Mock tool call for testing"""
    def __init__(self, tool_id, tool_name, tool_input):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.tool_input = tool_input


class MockLLMProvider:
    """Mock LLM provider for testing agents without actual API calls"""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.messages_history = []

    async def chat(self, messages, tools=None, **kwargs):
        self.messages_history.append(messages)
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return MockLLMResponse(content='{"data": null, "insights": "No data", "charts": []}')

    @property
    def provider_name(self):
        return "mock"

    @property
    def default_model(self):
        return "mock-model"


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider"""
    return MockLLMProvider()
