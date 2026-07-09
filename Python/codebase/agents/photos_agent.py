"""Photos and Markups Agent for document and photo analysis"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools


class PhotosAgent(BaseAgent):
    """Agent for analyzing photos, markups, and document sheets"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "photos"

    @property
    def description(self) -> str:
        return """Analyzes photos, markups, annotations, and document sheets.
        Tracks photo uploads, markup annotations, sheet versions,
        and provides insights on documentation status."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "photo_analysis",
            "markup_tracking",
            "sheet_management",
            "document_status",
            "photo_tags",
            "annotation_summary"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_photos",
                "description": "Query photos with filters for project, date, or tags",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_photo_stats",
                "description": "Get photo statistics - count by date, location, or tags",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "group_by": {
                            "type": "string",
                            "enum": ["date", "location", "user"],
                            "description": "How to group photos"
                        }
                    }
                }
            },
            {
                "name": "query_markups",
                "description": "Query markups and annotations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_markup_summary",
                "description": "Get summary of markups by type or layer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"}
                    }
                }
            },
            {
                "name": "query_sheets",
                "description": "Query document sheets",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "discipline": {"type": "string", "description": "Filter by discipline"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_sheet_disciplines",
                "description": "Get breakdown of sheets by discipline",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"}
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_photos":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            result = self.data_tools.query_table("photos_photos", filters, limit=tool_input.get("limit", 100))
            return result

        elif tool_name == "get_photo_stats":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            result = self.data_tools.query_table("photos_photos", filters)
            photos = result.get("data", []) if isinstance(result, dict) else result
            source_file = result.get("source_file") if isinstance(result, dict) else self.query_engine.get_source_file("photos_photos")

            if not photos:
                return {"message": "No photos found", "source_file": source_file, "table": "photos_photos"}

            group_by = tool_input.get("group_by", "date")

            if group_by == "date":
                # Group by date
                date_counts = {}
                for photo in photos:
                    created = photo.get("created_at")
                    if created:
                        date_key = str(created)[:10] if created else "unknown"
                        date_counts[date_key] = date_counts.get(date_key, 0) + 1
                return {
                    "source_file": source_file,
                    "table": "photos_photos",
                    "total_photos": len(photos),
                    "by_date": sorted(date_counts.items(), key=lambda x: x[0], reverse=True)[:30]
                }

            elif group_by == "user":
                user_counts = {}
                for photo in photos:
                    user = photo.get("created_by", "unknown")
                    user_counts[user] = user_counts.get(user, 0) + 1
                return {
                    "source_file": source_file,
                    "table": "photos_photos",
                    "total_photos": len(photos),
                    "by_user": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
                }

            return {
                "source_file": source_file,
                "table": "photos_photos",
                "total_photos": len(photos)
            }

        elif tool_name == "query_markups":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            return self.data_tools.query_table("markups_markup", filters, limit=tool_input.get("limit", 100))

        elif tool_name == "get_markup_summary":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            markups_result = self.data_tools.query_table("markups_markup", filters)
            markups = markups_result.get("data", []) if isinstance(markups_result, dict) else markups_result
            source_file = markups_result.get("source_file") if isinstance(markups_result, dict) else self.query_engine.get_source_file("markups_markup")

            layers_result = self.data_tools.query_table("markups_layer", filters)
            layers = layers_result.get("data", []) if isinstance(layers_result, dict) else layers_result

            return {
                "source_file": source_file,
                "table": "markups_markup",
                "total_markups": len(markups) if isinstance(markups, list) else 0,
                "total_layers": len(layers) if isinstance(layers, list) else 0
            }

        elif tool_name == "query_sheets":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            return self.data_tools.query_table("sheets_sheets", filters, limit=tool_input.get("limit", 100))

        elif tool_name == "get_sheet_disciplines":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            result = self.agg_tools.group_and_count("sheets_disciplines", "name", filters)
            return result

        return {"error": f"Unknown tool: {tool_name}"}
