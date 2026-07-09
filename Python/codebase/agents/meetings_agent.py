"""Meeting Minutes Agent for meeting tracking and analysis"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools


class MeetingsAgent(BaseAgent):
    """Agent for analyzing meeting minutes and action items"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "meetings"

    @property
    def description(self) -> str:
        return """Analyzes meeting minutes, action items, and attendance.
        Tracks meeting schedules, assignees, topic discussions,
        and outstanding action items."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "meeting_tracking",
            "action_item_status",
            "attendance_analysis",
            "topic_summary",
            "assignee_workload",
            "meeting_schedule"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_meetings",
                "description": "Query meetings with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by meeting status"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                    }
                }
            },
            {
                "name": "get_meeting_details",
                "description": "Get detailed information about a specific meeting including topics and items",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "Meeting ID to look up"}
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "query_action_items",
                "description": "Query meeting action items/minutes items",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by item status"},
                        "assignee": {"type": "string", "description": "Filter by assignee"}
                    }
                }
            },
            {
                "name": "get_pending_actions",
                "description": "Get pending/open action items across meetings",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "assignee": {"type": "string", "description": "Filter by assignee name"}
                    }
                }
            },
            {
                "name": "get_meeting_stats",
                "description": "Get meeting statistics - count, topics, attendance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"}
                    }
                }
            },
            {
                "name": "get_assignee_workload",
                "description": "Get action item workload by assignee",
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

        if tool_name == "query_meetings":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            result = self.data_tools.query_table(
                "meetingminutes_meetings",
                filters,
                limit=tool_input.get("limit", 50)
            )
            # Krion6d mode uses a normalized "meetings" table.
            if (
                isinstance(result, dict)
                and result.get("returned_rows", len(result.get("data", []))) == 0
            ):
                k_filters = {}
                if tool_input.get("project_id"):
                    k_filters["project_id"] = tool_input["project_id"]
                if tool_input.get("status"):
                    k_filters["status"] = tool_input["status"]
                return self.data_tools.query_table("meetings", k_filters, limit=tool_input.get("limit", 50))
            return result

        elif tool_name == "get_meeting_details":
            meeting_id = tool_input.get("meeting_id")

            meetings_result = self.data_tools.query_table("meetingminutes_meetings", {"id": meeting_id})
            meetings = meetings_result.get("data", []) if isinstance(meetings_result, dict) else meetings_result
            source_file = meetings_result.get("source_file") if isinstance(meetings_result, dict) else self.query_engine.get_source_file("meetingminutes_meetings")

            if not meetings:
                return {"error": f"Meeting {meeting_id} not found", "source_file": source_file, "table": "meetingminutes_meetings"}

            meeting = meetings[0] if isinstance(meetings, list) else meetings

            # Get topics
            topics_result = self.data_tools.query_table("meetingminutes_topics", {"meeting_id": meeting_id})
            topics = topics_result.get("data", []) if isinstance(topics_result, dict) else topics_result

            # Get items
            items_result = self.data_tools.query_table("meetingminutes_items", {"meeting_id": meeting_id})
            items = items_result.get("data", []) if isinstance(items_result, dict) else items_result

            # Get participants
            participants_result = self.data_tools.query_table("meetingminutes_participants", {"meeting_id": meeting_id})
            participants = participants_result.get("data", []) if isinstance(participants_result, dict) else participants_result

            return {
                "source_file": source_file,
                "table": "meetingminutes_meetings",
                "meeting": meeting,
                "topics": topics if isinstance(topics, list) else [],
                "items": items if isinstance(items, list) else [],
                "participants": participants if isinstance(participants, list) else [],
                "topic_count": len(topics) if isinstance(topics, list) else 0,
                "item_count": len(items) if isinstance(items, list) else 0,
                "participant_count": len(participants) if isinstance(participants, list) else 0
            }

        elif tool_name == "query_action_items":
            filters = {}
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            items_result = self.data_tools.query_table("meetingminutes_items", filters)
            items = items_result.get("data", []) if isinstance(items_result, dict) else items_result
            source_file = items_result.get("source_file") if isinstance(items_result, dict) else self.query_engine.get_source_file("meetingminutes_items")

            # Filter by assignee if specified
            if tool_input.get("assignee") and isinstance(items, list):
                assignee_filter = tool_input["assignee"].lower()
                assignees_result = self.data_tools.query_table("meetingminutes_assignees")
                assignees = assignees_result.get("data", []) if isinstance(assignees_result, dict) else assignees_result

                if isinstance(assignees, list):
                    matching_item_ids = set()
                    for a in assignees:
                        if assignee_filter in (a.get("name", "") or "").lower():
                            matching_item_ids.add(a.get("item_id"))
                    items = [i for i in items if i.get("id") in matching_item_ids]

            return {
                "source_file": source_file,
                "table": "meetingminutes_items",
                "total_rows": len(items),
                "data": items
            }

        elif tool_name == "get_pending_actions":
            items_result = self.data_tools.query_table("meetingminutes_items")
            items = items_result.get("data", []) if isinstance(items_result, dict) else items_result
            source_file = items_result.get("source_file") if isinstance(items_result, dict) else self.query_engine.get_source_file("meetingminutes_items")

            if not isinstance(items, list):
                return {"message": "No items found", "source_file": source_file, "table": "meetingminutes_items"}

            # Filter for pending/open items
            pending_items = [i for i in items if i.get("status") in ["open", "pending", "in_progress", None]]

            # Get assignees
            assignees_result = self.data_tools.query_table("meetingminutes_assignees")
            assignees = assignees_result.get("data", []) if isinstance(assignees_result, dict) else assignees_result

            # Map items to assignees
            item_assignee_map = {}
            if isinstance(assignees, list):
                for a in assignees:
                    item_id = a.get("item_id")
                    if item_id not in item_assignee_map:
                        item_assignee_map[item_id] = []
                    item_assignee_map[item_id].append(a.get("name", "Unknown"))

            # Build result
            result_items = []
            for item in pending_items:
                item_id = item.get("id")
                result_items.append({
                    "item_id": item_id,
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "due_date": item.get("due_date"),
                    "assignees": item_assignee_map.get(item_id, [])
                })

            # Filter by assignee if specified
            if tool_input.get("assignee"):
                assignee_filter = tool_input["assignee"].lower()
                result_items = [
                    i for i in result_items
                    if any(assignee_filter in a.lower() for a in i.get("assignees", []))
                ]

            return {
                "source_file": source_file,
                "table": "meetingminutes_items",
                "total_pending": len(result_items),
                "data": result_items[:50]
            }

        elif tool_name == "get_meeting_stats":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            meetings_result = self.data_tools.query_table("meetingminutes_meetings", filters)
            meetings = meetings_result.get("data", []) if isinstance(meetings_result, dict) else meetings_result
            source_file = meetings_result.get("source_file") if isinstance(meetings_result, dict) else self.query_engine.get_source_file("meetingminutes_meetings")

            # Krion6d mode fallback
            if not meetings:
                k_filters = {}
                if tool_input.get("project_id"):
                    k_filters["project_id"] = tool_input["project_id"]
                k_result = self.data_tools.query_table("meetings", k_filters)
                k_meetings = k_result.get("data", []) if isinstance(k_result, dict) else k_result
                k_source = k_result.get("source_file") if isinstance(k_result, dict) else self.query_engine.get_source_file("meetings")
                if isinstance(k_meetings, list) and len(k_meetings) > 0:
                    return {
                        "source_file": k_source,
                        "table": "meetings",
                        "total_meetings": len(k_meetings),
                        "total_topics": 0,
                        "total_items": 0,
                        "total_participants": 0
                    }

            topics_result = self.data_tools.query_table("meetingminutes_topics")
            topics = topics_result.get("data", []) if isinstance(topics_result, dict) else topics_result

            items_result = self.data_tools.query_table("meetingminutes_items")
            items = items_result.get("data", []) if isinstance(items_result, dict) else items_result

            participants_result = self.data_tools.query_table("meetingminutes_participants")
            participants = participants_result.get("data", []) if isinstance(participants_result, dict) else participants_result

            return {
                "source_file": source_file,
                "table": "meetingminutes_meetings",
                "total_meetings": len(meetings) if isinstance(meetings, list) else 0,
                "total_topics": len(topics) if isinstance(topics, list) else 0,
                "total_items": len(items) if isinstance(items, list) else 0,
                "total_participants": len(participants) if isinstance(participants, list) else 0
            }

        elif tool_name == "get_assignee_workload":
            assignees_result = self.data_tools.query_table("meetingminutes_assignees")
            assignees = assignees_result.get("data", []) if isinstance(assignees_result, dict) else assignees_result
            source_file = assignees_result.get("source_file") if isinstance(assignees_result, dict) else self.query_engine.get_source_file("meetingminutes_assignees")

            if not isinstance(assignees, list):
                return {"message": "No assignee data", "source_file": source_file, "table": "meetingminutes_assignees"}

            # Count items per assignee
            assignee_counts = {}
            for a in assignees:
                name = a.get("name", "Unknown")
                assignee_counts[name] = assignee_counts.get(name, 0) + 1

            workload = sorted(
                [{"assignee": k, "item_count": v} for k, v in assignee_counts.items()],
                key=lambda x: x["item_count"],
                reverse=True
            )

            return {
                "source_file": source_file,
                "table": "meetingminutes_assignees",
                "total_assignees": len(workload),
                "data": workload[:20]
            }

        return {"error": f"Unknown tool: {tool_name}"}
