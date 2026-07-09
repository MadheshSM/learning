"""Transmittals Agent for document transmittal tracking"""
from typing import List, Dict, Any, Optional

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools


class TransmittalsAgent(BaseAgent):
    """Agent for analyzing transmittals and document distribution"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "transmittals"

    @property
    def description(self) -> str:
        return """Analyzes transmittals and document distribution.
        Tracks document transmissions, recipients, and delivery status."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "transmittal_tracking",
            "recipient_analysis",
            "document_distribution",
            "transmittal_status"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_transmittals",
                "description": "Query transmittals with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by status"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                    }
                }
            },
            {
                "name": "get_transmittal_documents",
                "description": "Get documents included in transmittals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "transmittal_id": {"type": "string", "description": "Filter by transmittal ID"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_transmittal_recipients",
                "description": "Get recipients of transmittals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "transmittal_id": {"type": "string", "description": "Filter by transmittal ID"}
                    }
                }
            },
            {
                "name": "get_transmittal_stats",
                "description": "Get transmittal statistics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"}
                    }
                }
            }
        ]

    def _resolve_table(self, base_name: str) -> str:
        """Resolve the correct table name across data sources.

        ACC API uses standardized names like 'transmittals',
        CSV loader uses original file names like 'transmittals_workflow_transmittals'.
        """
        # Prefer standardized (API) name first
        if base_name in self.query_engine.dfs:
            return base_name

        # Fall back to CSV file-based names
        csv_fallbacks = {
            "transmittals": "transmittals_workflow_transmittals",
            "transmittal_documents": "transmittals_transmittal_documents",
            "transmittal_recipients": "transmittals_transmittal_recipients",
        }
        fallback = csv_fallbacks.get(base_name, base_name)
        if fallback in self.query_engine.dfs:
            return fallback

        return base_name  # Let it fail with a clear error downstream

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_transmittals":
            filters = {}
            if tool_input.get("project_id"):
                # ACC API uses 'project_id', CSV uses 'bim360_project_id'
                table = self._resolve_table("transmittals")
                pid_col = "project_id" if table == "transmittals" else "bim360_project_id"
                filters[pid_col] = tool_input["project_id"]
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            return self.data_tools.query_table(
                self._resolve_table("transmittals"),
                filters,
                limit=tool_input.get("limit", 50)
            )

        elif tool_name == "get_transmittal_documents":
            filters = {}
            if tool_input.get("transmittal_id"):
                filters["transmittal_id"] = tool_input["transmittal_id"]

            return self.data_tools.query_table(
                self._resolve_table("transmittal_documents"),
                filters,
                limit=tool_input.get("limit", 100)
            )

        elif tool_name == "get_transmittal_recipients":
            filters = {}
            if tool_input.get("transmittal_id"):
                filters["transmittal_id"] = tool_input["transmittal_id"]

            return self.data_tools.query_table(
                self._resolve_table("transmittal_recipients"),
                filters,
            )

        elif tool_name == "get_transmittal_stats":
            filters = {}
            if tool_input.get("project_id"):
                table = self._resolve_table("transmittals")
                pid_col = "project_id" if table == "transmittals" else "bim360_project_id"
                filters[pid_col] = tool_input["project_id"]

            transmittals_table = self._resolve_table("transmittals")
            transmittals_result = self.data_tools.query_table(transmittals_table, filters)
            transmittals = transmittals_result.get("data", []) if isinstance(transmittals_result, dict) else transmittals_result
            source_file = transmittals_result.get("source_file") if isinstance(transmittals_result, dict) else self.query_engine.get_source_file(transmittals_table)

            docs_table = self._resolve_table("transmittal_documents")
            docs_result = self.data_tools.query_table(docs_table)
            docs = docs_result.get("data", []) if isinstance(docs_result, dict) else docs_result

            recipients_table = self._resolve_table("transmittal_recipients")
            recipients_result = self.data_tools.query_table(recipients_table)
            recipients = recipients_result.get("data", []) if isinstance(recipients_result, dict) else recipients_result

            return {
                "source_file": source_file,
                "table": transmittals_table,
                "total_transmittals": len(transmittals) if isinstance(transmittals, list) else 0,
                "total_documents": len(docs) if isinstance(docs, list) else 0,
                "total_recipients": len(recipients) if isinstance(recipients, list) else 0
            }

        return {"error": f"Unknown tool: {tool_name}"}

