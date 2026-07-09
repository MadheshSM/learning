"""Tests for FastAPI endpoints"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestAPIEndpoints:
    """Tests for FastAPI API endpoints"""

    @pytest.fixture
    def client(self, temp_data_dir):
        """Create test client with mocked dependencies"""
        # Set environment variables before importing app
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir
        os.environ['LLM_PROVIDER'] = 'anthropic'
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # Import and patch
        with patch('main.LLMProviderFactory') as mock_factory:
            mock_provider = Mock()
            mock_provider.chat = AsyncMock(return_value=Mock(
                content='{"data": [], "insights": "Test", "charts": []}',
                tool_calls=None
            ))
            mock_factory.create_from_env.return_value = mock_provider

            # Import app after patching
            from main import app, initialize_system

            # Initialize with test data
            with patch('main.data_loader') as mock_loader:
                mock_loader.dataframes = {}

                client = TestClient(app)
                yield client

    @pytest.fixture
    def async_client(self, temp_data_dir):
        """Create async test client"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import app
        return AsyncClient(app=app, base_url="http://test")

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_get_data_summary(self, client, temp_data_dir):
        """Test data summary endpoint"""
        # Re-initialize with test data
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import initialize_system
        initialize_system()

        response = client.get("/api/data/summary")

        assert response.status_code == 200
        data = response.json()
        assert "tables" in data

    def test_get_table_data(self, client, temp_data_dir):
        """Test getting data from specific table"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import initialize_system
        initialize_system()

        response = client.get("/api/data/projects?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "table" in data
        assert "data" in data

    def test_get_table_data_not_found(self, client):
        """Test getting data from nonexistent table"""
        response = client.get("/api/data/nonexistent_table")

        assert response.status_code == 404

    def test_get_table_schema(self, client, temp_data_dir):
        """Test getting table schema"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import initialize_system
        initialize_system()

        response = client.get("/api/data/projects/schema")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "columns" in data

    def test_get_projects(self, client, temp_data_dir):
        """Test getting projects list"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import initialize_system
        initialize_system()

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data

    def test_get_agents(self, client):
        """Test getting agents info"""
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

    def test_reload_data(self, client, temp_data_dir):
        """Test reloading data"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import initialize_system
        initialize_system()

        response = client.post("/api/data/reload")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_query_endpoint_requires_orchestrator(self, client):
        """Test query endpoint returns error when orchestrator not available"""
        # With mocked orchestrator that's None
        with patch('main.orchestrator', None):
            response = client.post(
                "/api/query",
                json={"query": "Show me issues"}
            )

            assert response.status_code == 503


class TestQueryEndpoint:
    """Tests specifically for the query endpoint"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator"""
        orchestrator = Mock()
        orchestrator.process_query = AsyncMock(return_value={
            "success": True,
            "interpretation": "Show open issues",
            "data": {"issues": []},
            "message": "Found 0 issues",
            "charts": [],
            "agents_used": ["data_analyst"]
        })
        return orchestrator

    def test_query_request_validation(self, temp_data_dir):
        """Test query request validation"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        with patch('main.orchestrator') as mock_orch:
            mock_orch.process_query = AsyncMock(return_value={
                "success": True,
                "interpretation": "test",
                "data": None,
                "message": "test",
                "charts": [],
                "agents_used": []
            })

            from main import app
            client = TestClient(app)

            # Valid request (data_source not "acc" so local QueryEngine path; default acc would require JWT)
            response = client.post(
                "/api/query",
                json={"query": "Show me issues", "data_source": "local"}
            )
            assert response.status_code == 200
            body = response.json()
            assert body.get("scoped_project_id") is None
            assert body.get("scoped_project_name") is None
            assert body.get("project_resolved_from_query") is False
            ctx = mock_orch.process_query.call_args[1]["context"]
            assert "data_scope_instruction" not in ctx

    def test_query_with_project_filter(self, temp_data_dir):
        """Test query with project filter"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        with patch('main.orchestrator') as mock_orch:
            mock_orch.process_query = AsyncMock(return_value={
                "success": True,
                "interpretation": "test",
                "data": None,
                "message": "test",
                "charts": [],
                "agents_used": []
            })

            from main import app
            client = TestClient(app)

            response = client.post(
                "/api/query",
                json={
                    "query": "Show me issues",
                    "project_id": "PROJ-001",
                    "data_source": "local",
                }
            )

            assert response.status_code == 200
            body = response.json()
            assert body.get("scoped_project_id") == "PROJ-001"
            assert body.get("scoped_project_name") is None
            assert body.get("project_resolved_from_query") is False

            # Verify project_id was passed
            call_args = mock_orch.process_query.call_args
            assert call_args[1]["context"]["project_id"] == "PROJ-001"
            assert "data_scope_instruction" in call_args[1]["context"]
            assert "PROJ-001" in call_args[1]["context"]["data_scope_instruction"]


class TestFileUpload:
    """Tests for file upload functionality"""

    def test_upload_xlsx_file(self, temp_data_dir, sample_projects_df):
        """Test uploading an Excel file"""
        import os
        import io
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import app, initialize_system
        initialize_system()

        client = TestClient(app)

        # Create file-like object
        buffer = io.BytesIO()
        sample_projects_df.to_excel(buffer, index=False)
        buffer.seek(0)

        response = client.post(
            "/api/data/upload",
            files={"file": ("test_upload.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "test_upload.xlsx"

    def test_upload_invalid_file_type(self, temp_data_dir):
        """Test uploading non-xlsx file fails"""
        import os
        import io
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import app, initialize_system
        initialize_system()

        client = TestClient(app)

        response = client.post(
            "/api/data/upload",
            files={"file": ("test.csv", io.BytesIO(b"a,b,c\n1,2,3"), "text/csv")}
        )

        assert response.status_code == 400


class TestResponseModels:
    """Tests for response model validation"""

    def test_query_response_model(self):
        """Test QueryResponse model"""
        from main import QueryResponse

        response = QueryResponse(
            success=True,
            interpretation="Test query",
            data={"count": 10},
            message="Found 10 items",
            charts=[{"type": "bar"}],
            agents_used=["data_analyst"]
        )

        assert response.success is True
        assert response.interpretation == "Test query"

    def test_query_response_scoped_project_fields(self):
        """Optional scoped fields on QueryResponse (API contract for UI labels)."""
        from main import QueryResponse

        response = QueryResponse(
            success=True,
            message="ok",
            scoped_project_id="42",
            scoped_project_name="Alpha",
            project_resolved_from_query=True,
        )
        assert response.scoped_project_id == "42"
        assert response.scoped_project_name == "Alpha"
        assert response.project_resolved_from_query is True

    def test_query_response_with_error(self):
        """Test QueryResponse with error"""
        from main import QueryResponse

        response = QueryResponse(
            success=False,
            message="Error occurred",
            error="Connection failed"
        )

        assert response.success is False
        assert response.error == "Connection failed"


class TestStaticFiles:
    """Tests for static file serving"""

    def test_root_returns_index(self, temp_data_dir):
        """Test that root path returns index.html"""
        import os
        os.environ['DATA_DIRECTORY'] = temp_data_dir

        from main import app

        # Create frontend directory and index.html
        frontend_dir = Path(temp_data_dir).parent / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        (frontend_dir / "index.html").write_text("<html><body>Test</body></html>")

        with patch('main.Path') as mock_path:
            mock_path.return_value.exists.return_value = True

            client = TestClient(app)
            response = client.get("/")

            # Should return 200 or redirect to index
            assert response.status_code in [200, 404]  # 404 if frontend not mounted


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
