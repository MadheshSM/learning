"""Safety Agent for incident analysis and risk assessment"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools


class SafetyAgent(BaseAgent):
    """Agent for safety incident analysis and risk assessment"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "safety"

    @property
    def description(self) -> str:
        return """Analyzes safety incidents, identifies risks, tracks compliance,
        and monitors safety metrics across construction projects.
        Provides insights on incident trends, root causes, and corrective actions."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "incident_analysis",
            "risk_assessment",
            "safety_metrics",
            "compliance_tracking",
            "trend_analysis",
            "root_cause_analysis",
            "severity_distribution",
            "location_analysis"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_incidents",
                "description": "Query safety incidents with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "incident_type": {
                            "type": "string",
                            "enum": ["injury", "near_miss", "observation", "all"],
                            "description": "Type of incident"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "severe", "critical", "all"],
                            "description": "Severity level"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["open", "investigating", "closed", "all"],
                            "description": "Incident status"
                        },
                        "date_from": {"type": "string", "description": "Start date (ISO format)"},
                        "date_to": {"type": "string", "description": "End date (ISO format)"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_incident_trends",
                "description": "Get incident trends over time periods",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Grouping period"
                        },
                        "incident_type": {"type": "string", "description": "Optional incident type filter"}
                    },
                    "required": ["period"]
                }
            },
            {
                "name": "calculate_safety_metrics",
                "description": "Calculate safety KPIs like TRIR, DART, near miss ratio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "metric": {
                            "type": "string",
                            "enum": ["all", "incident_rate", "near_miss_ratio", "severity_breakdown", "open_incidents"],
                            "description": "Specific metric to calculate"
                        }
                    }
                }
            },
            {
                "name": "get_incidents_by_type",
                "description": "Get breakdown of incidents by type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_incidents_by_severity",
                "description": "Get breakdown of incidents by severity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_incidents_by_location",
                "description": "Get breakdown of incidents by location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_root_cause_analysis",
                "description": "Get breakdown of incidents by root cause",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "incident_type": {"type": "string", "description": "Optional incident type filter"}
                    }
                }
            },
            {
                "name": "get_open_incidents",
                "description": "Get all open or investigating incidents that need attention",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "compare_projects_safety",
                "description": "Compare safety metrics across projects",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_incidents":
            # Try safety_observations first, fall back to issues with quality/safety types
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            # Try ACC safety observations table
            result = self.data_tools.query_table("safety_observations", filters)

            # If empty or error, try issues table with quality observation filter
            if not result or (isinstance(result, list) and len(result) == 0):
                # Look for issues that might be safety/quality related
                issue_filters = {}
                if tool_input.get("project_id"):
                    issue_filters["project_id"] = tool_input["project_id"]
                if tool_input.get("status") and tool_input["status"] != "all":
                    issue_filters["status"] = tool_input["status"]

                issues = self.data_tools.query_table("issues", issue_filters)
                if isinstance(issues, list):
                    # Filter for safety/quality related issues by title
                    safety_keywords = ["safety", "quality", "observation", "hazard", "risk", "incident"]
                    result = [i for i in issues if any(kw in (i.get("title", "") or "").lower() for kw in safety_keywords)]

            limit = tool_input.get("limit", 100)
            if isinstance(result, list):
                result = result[:limit]
            return result if result else {"message": "No safety data available in this dataset"}

        elif tool_name == "get_incident_trends":
            # Safety data may not be available in ACC export
            return {"message": "Safety incident trend data not available in current dataset"}

        elif tool_name == "calculate_safety_metrics":
            # Return message indicating limited safety data
            return {
                "message": "Limited safety data available in current dataset",
                "total_incidents": 0,
                "note": "Use issues table to track quality and safety observations"
            }

        elif tool_name == "get_incidents_by_type":
            return {"message": "Safety incident type data not available"}

        elif tool_name == "get_incidents_by_severity":
            return {"message": "Safety incident severity data not available"}

        elif tool_name == "get_incidents_by_location":
            return {"message": "Safety incident location data not available"}

        elif tool_name == "get_root_cause_analysis":
            # Try to get root cause from issues table
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            try:
                return self.agg_tools.group_and_count("issues", "root_cause", filters)
            except:
                return {"message": "Root cause analysis data not available"}

        elif tool_name == "get_open_incidents":
            # Return open issues that might be safety related
            filters = {"status": ["open", "in_review"]}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            issues = self.data_tools.query_table("issues", filters)
            if isinstance(issues, list):
                # Filter for safety/quality related
                safety_keywords = ["safety", "quality", "observation", "hazard", "risk"]
                result = [i for i in issues if any(kw in (i.get("title", "") or "").lower() for kw in safety_keywords)]
                return result if result else {"message": "No open safety-related issues found"}
            return issues

        elif tool_name == "compare_projects_safety":
            return {"message": "Safety comparison data not available in current dataset"}

        return {"error": f"Unknown tool: {tool_name}"}
