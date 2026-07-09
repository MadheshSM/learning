"""Schedule Agent for timeline and delay analysis"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools
from .krion6d_review_query import project_id_filter_values, row_is_pending_review


class ScheduleAgent(BaseAgent):
    """Agent for schedule and timeline analysis"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "schedule"

    @property
    def description(self) -> str:
        return """Analyzes project schedules, identifies delays, tracks milestones,
        and provides timeline insights. Monitors task progress, calculates schedule
        variance, and identifies critical path issues."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "delay_analysis",
            "milestone_tracking",
            "critical_path",
            "schedule_variance",
            "progress_tracking",
            "phase_analysis",
            "lookahead_planning"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_schedule",
                "description": "Query schedule/task data with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "task_type": {"type": "string", "description": "Filter by task type"},
                        "is_critical": {"type": "boolean", "description": "Filter critical path tasks only"},
                        "is_wbs": {"type": "boolean", "description": "Filter WBS items only"},
                        "phase": {"type": "string", "description": "Filter by phase/WBS path"},
                        "pending_only": {
                            "type": "boolean",
                            "description": "Krion6d: only pending/open review workflow items (same data as tasks; uses review_status and workflow status).",
                        },
                        "review_status": {
                            "type": "integer",
                            "description": "Optional: 1=open/pending, 2=answered, 3=rejected (Krion6d review outcome).",
                        },
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_delayed_tasks",
                "description": "Get tasks that are behind schedule",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "min_delay_days": {"type": "integer", "description": "Minimum days delayed", "default": 0}
                    }
                }
            },
            {
                "name": "get_schedule_summary",
                "description": "Get overall schedule health summary for a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project to analyze"}
                    }
                }
            },
            {
                "name": "get_milestones",
                "description": "Get all milestones with their status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "include_completed": {"type": "boolean", "description": "Include completed milestones", "default": True}
                    }
                }
            },
            {
                "name": "get_tasks_by_phase",
                "description": "Get breakdown of tasks by phase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_tasks_by_status",
                "description": "Get breakdown of tasks by status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_progress_metrics",
                "description": "Calculate overall progress metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_upcoming_tasks",
                "description": "Get tasks starting or due soon",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"},
                        "days_ahead": {"type": "integer", "description": "Number of days to look ahead", "default": 14}
                    }
                }
            },
            {
                "name": "compare_projects_schedule",
                "description": "Compare schedule metrics across projects",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_schedule":
            tool_input = dict(tool_input or {})
            ctx = getattr(self, "_current_context", None) or {}
            if ctx.get("data_source") == "krion6d" and tool_input.get("pending_only") is not True:
                oq = (ctx.get("original_query") or "").lower()
                if "pending" in oq and (
                    re.search(r"\breviews?\b", oq)
                    or re.search(r"\btasks?\b", oq)
                    or "schedule" in oq
                    or "milestone" in oq
                ):
                    tool_input["pending_only"] = True

            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = project_id_filter_values(tool_input["project_id"])
            if tool_input.get("task_type"):
                filters["task_type"] = tool_input["task_type"]
            if tool_input.get("is_critical"):
                filters["is_critical"] = True
            if tool_input.get("is_wbs"):
                filters["is_wbs"] = True
            if tool_input.get("phase"):
                filters["phase"] = {"contains": tool_input["phase"]}
            if tool_input.get("review_status") is not None:
                try:
                    filters["review_status"] = int(tool_input["review_status"])
                except (TypeError, ValueError):
                    pass

            limit = tool_input.get("limit", 100)
            result = self.data_tools.query_table("schedule", filters, limit=limit)

            if tool_input.get("pending_only") and isinstance(result, dict) and "data" in result:
                raw = result["data"]
                rows = [r for r in raw if row_is_pending_review(r)]
                result = {
                    **result,
                    "data": rows,
                    "returned_rows": len(rows),
                    "total_rows": len(rows),
                }
            return result

        elif tool_name == "get_delayed_tasks":
            # Get tasks where actual dates are later than planned dates
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            tasks = self.data_tools.query_table("schedule", filters)

            if isinstance(tasks, dict) and "error" in tasks:
                return tasks

            # Calculate delay for each task
            delayed = []
            now = datetime.now()
            for task in tasks:
                planned_end = task.get("planned_end")
                actual_end = task.get("actual_end")
                percent_complete = task.get("percent_complete", 0) or 0

                # Task is delayed if: not complete AND past planned end date
                if planned_end and percent_complete < 100:
                    if isinstance(planned_end, str):
                        try:
                            planned_end = datetime.fromisoformat(planned_end.replace('Z', '+00:00'))
                        except:
                            continue
                    if hasattr(planned_end, 'to_pydatetime'):
                        planned_end = planned_end.to_pydatetime()

                    if planned_end and planned_end < now:
                        delay_days = (now - planned_end).days
                        task["delay_days"] = delay_days
                        task["status"] = "delayed"
                        delayed.append(task)

            # Sort by delay days descending
            delayed = sorted(delayed, key=lambda x: x.get("delay_days", 0), reverse=True)
            return delayed

        elif tool_name == "get_schedule_summary":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            tasks = self.data_tools.query_table("schedule", filters)

            if isinstance(tasks, dict) and "error" in tasks:
                return tasks

            total_tasks = len(tasks)
            now = datetime.now()

            # Calculate status based on percent_complete and dates
            completed = 0
            in_progress = 0
            not_started = 0
            delayed = 0
            critical_path_tasks = 0

            for t in tasks:
                pct = t.get("percent_complete", 0) or 0
                if pct >= 100:
                    completed += 1
                elif pct > 0:
                    in_progress += 1
                else:
                    not_started += 1

                # Check if delayed
                planned_end = t.get("planned_end")
                if planned_end and pct < 100:
                    if hasattr(planned_end, 'to_pydatetime'):
                        planned_end = planned_end.to_pydatetime()
                    try:
                        if planned_end and planned_end < now:
                            delayed += 1
                    except:
                        pass

                if t.get("is_critical"):
                    critical_path_tasks += 1

            # Calculate average progress
            progress_values = [(t.get("percent_complete", 0) or 0) for t in tasks]
            avg_progress = sum(progress_values) / len(progress_values) if progress_values else 0

            return {
                "total_tasks": total_tasks,
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started,
                "delayed": delayed,
                "critical_path_tasks": critical_path_tasks,
                "completion_rate": round((completed / total_tasks) * 100, 2) if total_tasks > 0 else 0,
                "average_progress": round(avg_progress, 2),
                "delay_rate": round((delayed / total_tasks) * 100, 2) if total_tasks > 0 else 0
            }

        elif tool_name == "get_milestones":
            # In ACC data, filter for tasks with zero duration (milestones)
            filters = {"duration": 0}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            tasks = self.data_tools.query_table("schedule", filters)

            # Also include critical path items as key milestones
            if isinstance(tasks, list) and len(tasks) == 0:
                filters = {"is_critical": True}
                if tool_input.get("project_id"):
                    filters["project_id"] = tool_input["project_id"]
                tasks = self.data_tools.query_table("schedule", filters)

            return tasks

        elif tool_name == "get_tasks_by_phase":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            return self.agg_tools.group_and_count("schedule", "phase", filters)

        elif tool_name == "get_tasks_by_status":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            return self.agg_tools.group_and_count("schedule", "status", filters)

        elif tool_name == "get_progress_metrics":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            # Calculate metrics
            metrics = self.agg_tools.calculate_metrics("schedule", "percent_complete", filters)

            # Add status counts
            status_counts = self.data_tools.count_by_status("schedule")

            return {
                "progress_metrics": metrics,
                "status_breakdown": status_counts
            }

        elif tool_name == "get_upcoming_tasks":
            days_ahead = tool_input.get("days_ahead", 14)
            now = datetime.now()
            future_date = now + timedelta(days=days_ahead)

            filters = {
                "status": ["not_started", "in_progress"],
                "planned_start": {"lte": future_date}
            }
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]

            tasks = self.data_tools.query_table("schedule", filters)

            # Sort by planned start date
            if isinstance(tasks, list):
                tasks = sorted(tasks, key=lambda x: x.get("planned_start") or datetime.max)

            return tasks

        elif tool_name == "compare_projects_schedule":
            # Get summary for each project
            projects = self.data_tools.query_table("projects")

            if isinstance(projects, dict) and "error" in projects:
                return projects

            comparisons = []
            for proj in projects:
                proj_id = proj.get("project_id")
                summary = await self._execute_tool("get_schedule_summary", {"project_id": proj_id})

                comparisons.append({
                    "project_id": proj_id,
                    "project_name": proj.get("project_name"),
                    **summary
                })

            return comparisons

        return {"error": f"Unknown tool: {tool_name}"}
