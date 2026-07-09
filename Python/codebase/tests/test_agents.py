"""Tests for agent system"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent, AgentResponse, ChartConfig
from agents.orchestrator import OrchestratorAgent
from agents.data_analyst_agent import DataAnalystAgent
from agents.safety_agent import SafetyAgent
from agents.schedule_agent import ScheduleAgent
from agents.cost_agent import CostAgent
from tests.conftest import MockLLMProvider, MockLLMResponse, MockToolCall


class TestAgentResponse:
    """Tests for AgentResponse dataclass"""

    def test_create_success_response(self):
        """Test creating a successful response"""
        response = AgentResponse(
            success=True,
            data={"count": 10},
            message="Found 10 items",
            charts=[{"type": "bar", "title": "Test"}]
        )

        assert response.success is True
        assert response.data == {"count": 10}
        assert response.message == "Found 10 items"
        assert len(response.charts) == 1

    def test_create_error_response(self):
        """Test creating an error response"""
        response = AgentResponse(
            success=False,
            data=None,
            message="Error occurred",
            error="Connection failed"
        )

        assert response.success is False
        assert response.error == "Connection failed"

    def test_to_dict(self):
        """Test converting response to dictionary"""
        response = AgentResponse(
            success=True,
            data={"test": 1},
            message="Test message"
        )

        result = response.to_dict()

        assert result["success"] is True
        assert result["data"] == {"test": 1}
        assert result["message"] == "Test message"
        assert result["charts"] == []


class TestDataAnalystAgent:
    """Tests for DataAnalystAgent"""

    def test_agent_properties(self, query_engine, mock_llm_provider):
        """Test agent name, description, capabilities"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        assert agent.name == "data_analyst"
        assert "issues" in agent.description.lower()
        assert "issues_analysis" in agent.capabilities
        assert "rfi_analysis" in agent.capabilities

    def test_tools_registered(self, query_engine, mock_llm_provider):
        """Test that tools are properly registered"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        tool_names = [t["name"] for t in agent.tools]

        assert "query_issues" in tool_names
        assert "query_rfis" in tool_names
        assert "group_and_count" in tool_names
        assert "get_overdue_items" in tool_names

    @pytest.mark.asyncio
    async def test_execute_query_issues(self, query_engine, mock_llm_provider):
        """Test executing query_issues tool"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("query_issues", {
            "status": "open"
        })

        assert isinstance(result, list)
        for item in result:
            assert item.get("status") == "open"

    @pytest.mark.asyncio
    async def test_execute_group_and_count(self, query_engine, mock_llm_provider):
        """Test executing group_and_count tool"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("group_and_count", {
            "table": "issues",
            "group_by": "status"
        })

        assert isinstance(result, list)
        assert all("status" in item and "count" in item for item in result)

    @pytest.mark.asyncio
    async def test_execute_get_overdue_items(self, query_engine, mock_llm_provider):
        """Test executing get_overdue_items tool"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_overdue_items", {
            "table": "issues"
        })

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_process_query(self, query_engine):
        """Test processing a query end-to-end"""
        # Create mock LLM that returns a final response
        mock_provider = MockLLMProvider([
            MockLLMResponse(content='{"data": [], "insights": "No issues found", "charts": []}')
        ])

        agent = DataAnalystAgent(mock_provider, query_engine)
        result = await agent.process("Show me open issues")

        assert result.success is True


class TestSafetyAgent:
    """Tests for SafetyAgent"""

    def test_agent_properties(self, query_engine, mock_llm_provider):
        """Test agent name, description, capabilities"""
        agent = SafetyAgent(mock_llm_provider, query_engine)

        assert agent.name == "safety"
        assert "incident" in agent.description.lower()
        assert "incident_analysis" in agent.capabilities
        assert "risk_assessment" in agent.capabilities

    def test_tools_registered(self, query_engine, mock_llm_provider):
        """Test that tools are properly registered"""
        agent = SafetyAgent(mock_llm_provider, query_engine)

        tool_names = [t["name"] for t in agent.tools]

        assert "query_incidents" in tool_names
        assert "get_incident_trends" in tool_names
        assert "calculate_safety_metrics" in tool_names

    @pytest.mark.asyncio
    async def test_execute_query_incidents(self, query_engine, mock_llm_provider):
        """Test executing query_incidents tool"""
        agent = SafetyAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("query_incidents", {
            "incident_type": "injury"
        })

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_calculate_safety_metrics(self, query_engine, mock_llm_provider):
        """Test executing calculate_safety_metrics tool"""
        agent = SafetyAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("calculate_safety_metrics", {})

        assert "total_incidents" in result
        assert "injuries" in result
        assert "near_misses" in result
        assert "near_miss_ratio" in result

    @pytest.mark.asyncio
    async def test_execute_get_open_incidents(self, query_engine, mock_llm_provider):
        """Test executing get_open_incidents tool"""
        agent = SafetyAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_open_incidents", {})

        assert isinstance(result, list)


class TestScheduleAgent:
    """Tests for ScheduleAgent"""

    def test_agent_properties(self, query_engine, mock_llm_provider):
        """Test agent name, description, capabilities"""
        agent = ScheduleAgent(mock_llm_provider, query_engine)

        assert agent.name == "schedule"
        assert "schedule" in agent.description.lower()
        assert "delay_analysis" in agent.capabilities
        assert "milestone_tracking" in agent.capabilities

    def test_tools_registered(self, query_engine, mock_llm_provider):
        """Test that tools are properly registered"""
        agent = ScheduleAgent(mock_llm_provider, query_engine)

        tool_names = [t["name"] for t in agent.tools]

        assert "query_schedule" in tool_names
        assert "get_delayed_tasks" in tool_names
        assert "get_schedule_summary" in tool_names
        assert "get_milestones" in tool_names

    @pytest.mark.asyncio
    async def test_execute_query_schedule(self, query_engine, mock_llm_provider):
        """Test executing query_schedule tool"""
        agent = ScheduleAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("query_schedule", {
            "status": "in_progress"
        })

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_get_schedule_summary(self, query_engine, mock_llm_provider):
        """Test executing get_schedule_summary tool"""
        agent = ScheduleAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_schedule_summary", {})

        assert "total_tasks" in result
        assert "completed" in result
        assert "delayed" in result
        assert "completion_rate" in result

    @pytest.mark.asyncio
    async def test_execute_get_milestones(self, query_engine, mock_llm_provider):
        """Test executing get_milestones tool"""
        agent = ScheduleAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_milestones", {})

        assert isinstance(result, list)
        # All results should be milestones
        for item in result:
            assert item.get("is_milestone") is True


class TestCostAgent:
    """Tests for CostAgent"""

    def test_agent_properties(self, query_engine, mock_llm_provider):
        """Test agent name, description, capabilities"""
        agent = CostAgent(mock_llm_provider, query_engine)

        assert agent.name == "cost"
        assert "budget" in agent.description.lower()
        assert "budget_analysis" in agent.capabilities
        assert "variance_analysis" in agent.capabilities

    def test_tools_registered(self, query_engine, mock_llm_provider):
        """Test that tools are properly registered"""
        agent = CostAgent(mock_llm_provider, query_engine)

        tool_names = [t["name"] for t in agent.tools]

        assert "query_costs" in tool_names
        assert "get_budget_summary" in tool_names
        assert "get_variance_analysis" in tool_names

    @pytest.mark.asyncio
    async def test_execute_get_budget_summary(self, query_engine, mock_llm_provider):
        """Test executing get_budget_summary tool"""
        agent = CostAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_budget_summary", {})

        assert "total_budgeted" in result
        assert "total_actual" in result
        assert "variance" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_get_costs_by_category(self, query_engine, mock_llm_provider):
        """Test executing get_costs_by_category tool"""
        agent = CostAgent(mock_llm_provider, query_engine)

        result = await agent._execute_tool("get_costs_by_category", {})

        assert isinstance(result, list)
        for item in result:
            assert "category" in item
            assert "budgeted" in item
            assert "actual" in item


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent"""

    @pytest.fixture
    def orchestrator(self, query_engine, mock_llm_provider):
        """Create orchestrator with agents"""
        agents = [
            DataAnalystAgent(mock_llm_provider, query_engine),
            SafetyAgent(mock_llm_provider, query_engine),
            ScheduleAgent(mock_llm_provider, query_engine),
            CostAgent(mock_llm_provider, query_engine),
        ]
        return OrchestratorAgent(mock_llm_provider, agents)

    def test_orchestrator_init(self, orchestrator):
        """Test orchestrator initialization"""
        assert len(orchestrator.agents) == 4
        assert "data_analyst" in orchestrator.agents
        assert "safety" in orchestrator.agents
        assert "schedule" in orchestrator.agents
        assert "cost" in orchestrator.agents

    def test_build_agent_descriptions(self, orchestrator):
        """Test agent descriptions are built correctly"""
        descriptions = orchestrator.agent_descriptions

        assert "data_analyst" in descriptions
        assert "safety" in descriptions
        assert "schedule" in descriptions

    def test_get_available_agents(self, orchestrator):
        """Test getting available agents info"""
        agents_info = orchestrator.get_available_agents()

        assert len(agents_info) == 4
        for info in agents_info:
            assert "name" in info
            assert "description" in info
            assert "capabilities" in info

    def test_default_routing_issues(self, orchestrator):
        """Test default routing for issues query"""
        routing = orchestrator._default_routing("Show me open issues")

        assert "data_analyst" in routing["agents"]

    def test_default_routing_safety(self, orchestrator):
        """Test default routing for safety query"""
        routing = orchestrator._default_routing("Safety incidents this month")

        assert "safety" in routing["agents"]

    def test_default_routing_schedule(self, orchestrator):
        """Test default routing for schedule query"""
        routing = orchestrator._default_routing("Show delayed tasks")

        assert "schedule" in routing["agents"]

    def test_default_routing_cost(self, orchestrator):
        """Test default routing for cost query"""
        routing = orchestrator._default_routing("Budget variance")

        assert "cost" in routing["agents"]

    @pytest.mark.asyncio
    async def test_analyze_and_route(self, query_engine):
        """Test query analysis and routing"""
        mock_provider = MockLLMProvider([
            MockLLMResponse(content='{"intent": "find issues", "agents": ["data_analyst"], "refined_query": "show issues", "reasoning": "data query"}')
        ])

        agents = [DataAnalystAgent(mock_provider, query_engine)]
        orchestrator = OrchestratorAgent(mock_provider, agents)

        routing = await orchestrator._analyze_and_route("Show me issues")

        assert "agents" in routing
        assert "data_analyst" in routing["agents"]

    @pytest.mark.asyncio
    async def test_process_query_single_agent(self, query_engine):
        """Test processing query with single agent"""
        # Mock LLM responses
        mock_provider = MockLLMProvider([
            # Routing response
            MockLLMResponse(content='{"intent": "analyze issues", "agents": ["data_analyst"], "refined_query": "show issues", "reasoning": "data query"}'),
            # Agent response
            MockLLMResponse(content='{"data": [], "insights": "No issues", "charts": []}')
        ])

        agents = [DataAnalystAgent(mock_provider, query_engine)]
        orchestrator = OrchestratorAgent(mock_provider, agents)

        result = await orchestrator.process_query("Show me issues")

        assert result["success"] is True
        assert "data_analyst" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_process_query_handles_error(self, query_engine):
        """Test that orchestrator handles errors gracefully"""
        mock_provider = MockLLMProvider([])
        mock_provider.chat = AsyncMock(side_effect=Exception("API Error"))

        agents = [DataAnalystAgent(mock_provider, query_engine)]
        orchestrator = OrchestratorAgent(mock_provider, agents)

        result = await orchestrator.process_query("Show me issues")

        assert result["success"] is False
        assert "error" in result


class TestBaseAgentParsing:
    """Tests for BaseAgent response parsing"""

    def test_parse_json_response(self, query_engine, mock_llm_provider):
        """Test parsing valid JSON response"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        content = '{"data": [1, 2, 3], "insights": "Found 3 items", "charts": []}'
        result = agent._parse_final_response(content)

        assert result.success is True
        assert result.data == [1, 2, 3]
        assert result.message == "Found 3 items"

    def test_parse_json_with_markdown(self, query_engine, mock_llm_provider):
        """Test parsing JSON wrapped in markdown code blocks"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        content = '```json\n{"data": null, "insights": "Test", "charts": []}\n```'
        result = agent._parse_final_response(content)

        assert result.success is True
        assert result.message == "Test"

    def test_parse_plain_text(self, query_engine, mock_llm_provider):
        """Test parsing plain text (non-JSON) response"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        content = "This is a plain text response without JSON."
        result = agent._parse_final_response(content)

        assert result.success is True
        assert result.message == content

    def test_create_chart_config(self, query_engine, mock_llm_provider):
        """Test chart configuration helper"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        chart = agent._create_chart_config(
            "bar",
            "Test Chart",
            ["A", "B", "C"],
            [1, 2, 3]
        )

        assert chart["type"] == "bar"
        assert chart["title"] == "Test Chart"
        assert chart["data"]["labels"] == ["A", "B", "C"]

    def test_create_kpi_config(self, query_engine, mock_llm_provider):
        """Test KPI configuration helper"""
        agent = DataAnalystAgent(mock_llm_provider, query_engine)

        kpi = agent._create_kpi_config(
            "Total Issues",
            42,
            "items",
            "up",
            "+10%"
        )

        assert kpi["type"] == "kpi"
        assert kpi["data"]["value"] == 42
        assert kpi["data"]["trend"] == "up"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
