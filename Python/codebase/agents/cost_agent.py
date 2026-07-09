"""Cost Agent for budget and financial analysis"""
from typing import List, Dict, Any, Optional

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools


class CostAgent(BaseAgent):
    """Agent for budget and cost analysis"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "cost"

    @property
    def description(self) -> str:
        return """Analyzes project budgets, costs, and financial metrics.
        Tracks budget vs actual spending, identifies variances, forecasts
        costs, and provides financial insights across projects."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "budget_analysis",
            "cost_tracking",
            "variance_analysis",
            "forecasting",
            "category_breakdown",
            "project_comparison"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_costs",
                "description": "Query cost data with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "category": {"type": "string", "description": "Filter by cost category"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_budget_summary",
                "description": "Get budget summary for a project or all projects",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_variance_analysis",
                "description": "Analyze budget vs actual variance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_costs_by_category",
                "description": "Get breakdown of costs by category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "compare_projects_budget",
                "description": "Compare budget metrics across projects",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_over_budget_items",
                "description": "Get items that are over budget",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "threshold_pct": {"type": "number", "description": "Variance threshold percentage", "default": 0}
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        # Note: ACC cost data is limited - check for available tables
        if tool_name == "query_costs":
            # Try budgets table first
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            result = self.data_tools.query_table("budgets", filters)
            if not result or (isinstance(result, list) and len(result) == 0):
                result = self.data_tools.query_table("cost_budget_code_segments", filters)

            if not result or (isinstance(result, list) and len(result) == 0):
                return {"message": "Cost data not available in current dataset. Check ACC Cost Management module."}

            limit = tool_input.get("limit", 100)
            if isinstance(result, list):
                result = result[:limit]
            return result

        elif tool_name == "get_budget_summary":
            # Try to get project budget from projects table
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            projects = self.data_tools.query_table("projects", filters)

            if isinstance(projects, list) and len(projects) > 0:
                total_budget = sum([(p.get("budget", 0) or 0) for p in projects])
                return {
                    "total_budgeted": round(total_budget, 2),
                    "message": "Limited cost data - only project-level budget available",
                    "project_count": len(projects)
                }

            return {"message": "Budget data not available in current dataset"}

        elif tool_name == "get_variance_analysis":
            return {"message": "Variance analysis not available - detailed cost data not in current export"}

        elif tool_name == "get_costs_by_category":
            # Try budget code segments
            result = self.data_tools.query_table("cost_budget_code_segments")
            if isinstance(result, list) and len(result) > 0:
                return result
            return {"message": "Cost category data not available in current dataset"}

        elif tool_name == "compare_projects_budget":
            projects = self.data_tools.query_table("projects")

            if isinstance(projects, dict) and "error" in projects:
                return projects

            comparisons = []
            for proj in projects:
                budget = proj.get("budget", 0) or 0
                comparisons.append({
                    "project_id": proj.get("project_id"),
                    "project_name": proj.get("project_name"),
                    "budget": round(budget, 2),
                    "currency": proj.get("currency", "USD"),
                    "status": proj.get("status")
                })

            # Sort by budget descending
            comparisons = sorted(comparisons, key=lambda x: x.get("budget", 0), reverse=True)

            return {
                "projects": comparisons,
                "total_budget": sum([c.get("budget", 0) for c in comparisons]),
                "note": "Only project-level budget data available"
            }

        elif tool_name == "get_over_budget_items":
            return {"message": "Over budget analysis not available - detailed actuals not in current export"}

        return {"error": f"Unknown tool: {tool_name}"}
