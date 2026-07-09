"""Forms Agent for form tracking and review analysis"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .krion6d_review_query import (
    project_id_filter_values as _project_id_filter_values,
    row_is_pending_review as _row_is_pending_review,
)


class FormsAgent(BaseAgent):
    """Agent for forms and reviews analysis"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "forms"

    @property
    def description(self) -> str:
        return """Analyzes forms, form sections, and review workflows.
        Tracks form status, assignees, section completion times, review TAT,
        and identifies pending reviews and stakeholder performance."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "form_status_tracking",
            "form_assignment_lookup",
            "section_time_analysis",
            "review_tat_analysis",
            "reviewer_performance",
            "pending_reviews",
            "pour_card_forms",
            "form_template_analysis"
        ]

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_forms",
                "description": "Query forms data with filters. Can filter by status (in_progress, completed, draft), template name, or assignee.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by form status (in_progress, completed, draft, etc.)"},
                        "template_name": {"type": "string", "description": "Filter by template name (e.g., pour card, inspection)"},
                        "assignee_id": {"type": "string", "description": "Filter by assignee user ID"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "get_form_details",
                "description": "Get detailed information about a specific form by ID, including sections and assignments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "form_id": {"type": "string", "description": "The form ID to look up"}
                    },
                    "required": ["form_id"]
                }
            },
            {
                "name": "get_forms_by_template",
                "description": "Get forms grouped by template type (e.g., pour cards, inspections)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_name": {"type": "string", "description": "Template name to filter (optional)"},
                        "status": {"type": "string", "description": "Filter by status"}
                    }
                }
            },
            {
                "name": "get_section_time_analysis",
                "description": "Analyze time spent by stakeholders on form sections",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "form_id": {"type": "string", "description": "Optional form ID filter"},
                        "assignee_id": {"type": "string", "description": "Optional assignee filter"}
                    }
                }
            },
            {
                "name": "query_reviews",
                "description": "Query reviews with filters for status, reviewer, or pending items",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by review status"},
                        "assignee": {"type": "string", "description": "Filter by reviewer/assignee"},
                        "pending_only": {"type": "boolean", "description": "Show only pending reviews"}
                    }
                }
            },
            {
                "name": "get_review_tat_analysis",
                "description": "Analyze review Turn Around Time (TAT) and find reviews exceeding thresholds",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tat_threshold_days": {"type": "integer", "description": "TAT threshold in days", "default": 3},
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_reviewer_performance",
                "description": "Analyze reviewer performance - who is punctual, who has delays",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    }
                }
            },
            {
                "name": "get_pending_reviews_by_user",
                "description": "Get reviews pending with a specific user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID to check"},
                        "user_name": {"type": "string", "description": "User name to search for"}
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_forms":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]
            if tool_input.get("assignee_id"):
                filters["assignee_id"] = tool_input["assignee_id"]

            result = self.data_tools.query_table("forms_forms", filters, limit=tool_input.get("limit", 100))

            # Handle metadata format from query_table
            if isinstance(result, dict) and "data" in result:
                forms = result.get("data", [])
                source_file = result.get("source_file")
                table = result.get("table")
            else:
                forms = result if isinstance(result, list) else []
                source_file = self.query_engine.get_source_file("forms_forms")
                table = "forms_forms"

            # Filter by template name if specified
            if tool_input.get("template_name"):
                template_name = tool_input["template_name"].lower()
                templates_result = self.data_tools.query_table("forms_form_templates")
                templates = templates_result.get("data", []) if isinstance(templates_result, dict) else templates_result
                if isinstance(templates, list):
                    matching_template_ids = [
                        t.get("id") for t in templates
                        if template_name in (t.get("name", "") or "").lower()
                    ]
                    forms = [f for f in forms if f.get("template_id") in matching_template_ids]

            return {
                "source_file": source_file,
                "table": table,
                "total_rows": len(forms),
                "data": forms
            }

        elif tool_name == "get_form_details":
            form_id = tool_input.get("form_id")

            forms_result = self.data_tools.query_table("forms_forms", {"id": form_id})
            forms = forms_result.get("data", []) if isinstance(forms_result, dict) else forms_result
            source_file = forms_result.get("source_file") if isinstance(forms_result, dict) else self.query_engine.get_source_file("forms_forms")

            if not forms or len(forms) == 0:
                return {"error": f"Form {form_id} not found", "source_file": source_file, "table": "forms_forms"}

            form = forms[0] if isinstance(forms, list) else forms

            sections_result = self.data_tools.query_table("forms_form_sections", {"form_uid": form_id})
            sections = sections_result.get("data", []) if isinstance(sections_result, dict) else sections_result

            assignee_id = form.get("assignee_id")
            assignee = None
            if assignee_id:
                users_result = self.data_tools.query_table("users", {"user_id": assignee_id})
                users = users_result.get("data", []) if isinstance(users_result, dict) else users_result
                if isinstance(users, list) and len(users) > 0:
                    assignee = users[0]

            return {
                "source_file": source_file,
                "table": "forms_forms",
                "form": form,
                "sections": sections if isinstance(sections, list) else [],
                "assignee": assignee,
                "section_count": len(sections) if isinstance(sections, list) else 0
            }

        elif tool_name == "get_forms_by_template":
            templates_result = self.data_tools.query_table("forms_form_templates")
            templates = templates_result.get("data", []) if isinstance(templates_result, dict) else templates_result
            source_file = templates_result.get("source_file") if isinstance(templates_result, dict) else self.query_engine.get_source_file("forms_form_templates")

            if tool_input.get("template_name") and isinstance(templates, list):
                template_name = tool_input["template_name"].lower()
                templates = [t for t in templates if template_name in (t.get("name", "") or "").lower()]

            forms_result = self.data_tools.query_table("forms_forms")
            forms = forms_result.get("data", []) if isinstance(forms_result, dict) else forms_result

            if tool_input.get("status") and isinstance(forms, list):
                forms = [f for f in forms if f.get("status") == tool_input["status"]]

            template_counts = {}
            for form in forms if isinstance(forms, list) else []:
                template_id = form.get("template_id")
                if template_id not in template_counts:
                    template_counts[template_id] = {"count": 0, "forms": []}
                template_counts[template_id]["count"] += 1
                if len(template_counts[template_id]["forms"]) < 5:
                    template_counts[template_id]["forms"].append(form)

            template_result = []
            for t in templates if isinstance(templates, list) else []:
                tid = t.get("id")
                if tid in template_counts:
                    template_result.append({
                        "template_id": tid,
                        "template_name": t.get("name"),
                        "form_count": template_counts[tid]["count"],
                        "sample_forms": template_counts[tid]["forms"]
                    })

            return {
                "source_file": source_file,
                "table": "forms_form_templates",
                "total_rows": len(template_result),
                "data": sorted(template_result, key=lambda x: x["form_count"], reverse=True)
            }

        elif tool_name == "get_section_time_analysis":
            filters = {}
            if tool_input.get("form_id"):
                filters["form_uid"] = tool_input["form_id"]
            if tool_input.get("assignee_id"):
                filters["assignee_id"] = tool_input["assignee_id"]

            sections_result = self.data_tools.query_table("forms_form_sections", filters)
            sections = sections_result.get("data", []) if isinstance(sections_result, dict) else sections_result
            source_file = sections_result.get("source_file") if isinstance(sections_result, dict) else self.query_engine.get_source_file("forms_form_sections")

            if not isinstance(sections, list) or len(sections) == 0:
                return {"message": "No section data available", "source_file": source_file, "table": "forms_form_sections"}

            assignee_times = {}
            for section in sections:
                assignee = section.get("assignee_id", "unassigned")
                created = section.get("created_at")
                updated = section.get("updated_at")

                if assignee not in assignee_times:
                    assignee_times[assignee] = {"section_count": 0, "total_time_hours": 0}

                assignee_times[assignee]["section_count"] += 1

                if created and updated:
                    try:
                        if hasattr(created, 'timestamp') and hasattr(updated, 'timestamp'):
                            hours = (updated.timestamp() - created.timestamp()) / 3600
                            assignee_times[assignee]["total_time_hours"] += hours
                    except:
                        pass

            users_result = self.data_tools.query_table("users")
            users = users_result.get("data", []) if isinstance(users_result, dict) else users_result
            user_map = {u.get("user_id"): u.get("name") for u in users} if isinstance(users, list) else {}

            time_result = []
            for assignee_id, data in assignee_times.items():
                time_result.append({
                    "assignee_id": assignee_id,
                    "assignee_name": user_map.get(assignee_id, "Unknown"),
                    "section_count": data["section_count"],
                    "total_time_hours": round(data["total_time_hours"], 2),
                    "avg_time_per_section_hours": round(data["total_time_hours"] / data["section_count"], 2) if data["section_count"] > 0 else 0
                })

            return {
                "source_file": source_file,
                "table": "forms_form_sections",
                "total_rows": len(sections),
                "data": sorted(time_result, key=lambda x: x["section_count"], reverse=True)
            }

        elif tool_name == "query_reviews":
            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            result = self.data_tools.query_table("reviews_reviews", filters)

            # Handle metadata format from query_table
            if isinstance(result, dict) and "data" in result:
                reviews = result.get("data", [])
                source_file = result.get("source_file")
                table = result.get("table")
            else:
                reviews = result if isinstance(result, list) else []
                source_file = self.query_engine.get_source_file("reviews_reviews")
                table = "reviews_reviews"

            dfs = getattr(self.query_engine, "dfs", {})
            rr_missing_or_empty = (
                "reviews_reviews" not in dfs
                or not isinstance(reviews, list)
                or len(reviews) == 0
            )
            if rr_missing_or_empty and "schedule" in dfs and len(dfs["schedule"]) > 0:
                sfilters: Dict[str, Any] = {}
                if tool_input.get("project_id"):
                    sfilters["project_id"] = _project_id_filter_values(tool_input["project_id"])
                if tool_input.get("status"):
                    sfilters["status"] = tool_input["status"]
                sresult = self.data_tools.query_table("schedule", sfilters)
                if isinstance(sresult, dict) and "data" in sresult:
                    reviews = sresult.get("data", [])
                    source_file = sresult.get("source_file")
                    table = "schedule"
                else:
                    reviews = []

            if tool_input.get("pending_only"):
                reviews = [r for r in reviews if _row_is_pending_review(r)]

            if tool_input.get("assignee"):
                tasks_result = self.data_tools.query_table("reviews_review_tasks")
                tasks = tasks_result.get("data", []) if isinstance(tasks_result, dict) else tasks_result
                if isinstance(tasks, list):
                    assignee = tool_input["assignee"].lower()
                    matching_review_ids = set()
                    for task in tasks:
                        task_assignee = task.get("assignee", "") or ""
                        if assignee in task_assignee.lower():
                            matching_review_ids.add(task.get("review_id"))
                    reviews = [r for r in reviews if r.get("id") in matching_review_ids]

            return {
                "source_file": source_file,
                "table": table,
                "total_rows": len(reviews),
                "data": reviews
            }

        elif tool_name == "get_review_tat_analysis":
            threshold_days = tool_input.get("tat_threshold_days", 3)

            filters = {}
            if tool_input.get("project_id"):
                filters["bim360_project_id"] = tool_input["project_id"]

            result = self.data_tools.query_table("reviews_reviews", filters)

            # Handle metadata format from query_table
            if isinstance(result, dict) and "data" in result:
                reviews = result.get("data", [])
                source_file = result.get("source_file")
                table = result.get("table")
            else:
                reviews = result if isinstance(result, list) else []
                source_file = self.query_engine.get_source_file("reviews_reviews")
                table = "reviews_reviews"

            if not reviews:
                return {"message": "No review data available", "source_file": source_file, "table": table}

            now = datetime.now()
            exceeding_tat = []
            within_tat = []

            for review in reviews:
                created_at = review.get("created_at")
                status = review.get("status")

                if created_at:
                    try:
                        if hasattr(created_at, 'timestamp'):
                            days_open = (now - created_at.replace(tzinfo=None)).days
                        else:
                            days_open = 0

                        review_info = {
                            "review_id": review.get("id"),
                            "review_name": review.get("review_name"),
                            "status": status,
                            "days_open": days_open,
                            "created_at": str(created_at)
                        }

                        if days_open > threshold_days and status not in ["completed", "closed"]:
                            exceeding_tat.append(review_info)
                        else:
                            within_tat.append(review_info)
                    except:
                        pass

            return {
                "source_file": source_file,
                "table": table,
                "total_rows": len(reviews),
                "threshold_days": threshold_days,
                "total_reviews": len(reviews),
                "exceeding_tat_count": len(exceeding_tat),
                "within_tat_count": len(within_tat),
                "exceeding_tat_reviews": sorted(exceeding_tat, key=lambda x: x["days_open"], reverse=True)[:20],
                "percentage_exceeding": round(len(exceeding_tat) / len(reviews) * 100, 2) if len(reviews) > 0 else 0
            }

        elif tool_name == "get_reviewer_performance":
            result = self.data_tools.query_table("reviews_review_tasks")

            # Handle metadata format from query_table
            if isinstance(result, dict) and "data" in result:
                tasks = result.get("data", [])
                source_file = result.get("source_file")
                table = result.get("table")
            else:
                tasks = result if isinstance(result, list) else []
                source_file = self.query_engine.get_source_file("reviews_review_tasks")
                table = "reviews_review_tasks"

            if not tasks:
                return {"message": "No review task data available", "source_file": source_file, "table": table}

            assignee_stats = {}
            for task in tasks:
                assignee = task.get("assignee", "Unknown")
                state = task.get("state", "")

                if assignee not in assignee_stats:
                    assignee_stats[assignee] = {"total": 0, "completed": 0, "pending": 0}

                assignee_stats[assignee]["total"] += 1
                if state in ["completed", "approved", "done"]:
                    assignee_stats[assignee]["completed"] += 1
                else:
                    assignee_stats[assignee]["pending"] += 1

            perf_result = []
            for assignee, stats in assignee_stats.items():
                completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                perf_result.append({
                    "assignee": assignee,
                    "total_tasks": stats["total"],
                    "completed": stats["completed"],
                    "pending": stats["pending"],
                    "completion_rate": round(completion_rate, 2)
                })

            punctual = sorted([r for r in perf_result if r["completion_rate"] >= 80], key=lambda x: x["completion_rate"], reverse=True)
            delayed = sorted([r for r in perf_result if r["completion_rate"] < 80], key=lambda x: x["completion_rate"])

            return {
                "source_file": source_file,
                "table": table,
                "total_rows": len(tasks),
                "punctual_reviewers": punctual[:10],
                "reviewers_with_delays": delayed[:10],
                "total_reviewers": len(perf_result)
            }

        elif tool_name == "get_pending_reviews_by_user":
            user_id = tool_input.get("user_id")
            user_name = tool_input.get("user_name", "").lower()

            tasks_result = self.data_tools.query_table("reviews_review_tasks")
            tasks = tasks_result.get("data", []) if isinstance(tasks_result, dict) else tasks_result
            source_file = tasks_result.get("source_file") if isinstance(tasks_result, dict) else self.query_engine.get_source_file("reviews_review_tasks")

            if not tasks:
                return {"message": "No review task data available", "source_file": source_file, "table": "reviews_review_tasks"}

            pending_tasks = []
            for task in tasks:
                assignee = task.get("assignee", "")
                state = task.get("state", "")

                is_match = False
                if user_id and str(task.get("assignee")) == str(user_id):
                    is_match = True
                elif user_name and user_name in (assignee or "").lower():
                    is_match = True

                if is_match and state not in ["completed", "approved", "done", "closed"]:
                    pending_tasks.append(task)

            review_ids = set(t.get("review_id") for t in pending_tasks)
            reviews_result = self.data_tools.query_table("reviews_reviews")
            reviews = reviews_result.get("data", []) if isinstance(reviews_result, dict) else reviews_result

            review_map = {}
            if isinstance(reviews, list):
                review_map = {r.get("id"): r for r in reviews}

            pending_result = []
            for task in pending_tasks:
                review = review_map.get(task.get("review_id"), {})
                pending_result.append({
                    "task_id": task.get("id"),
                    "task_name": task.get("name"),
                    "state": task.get("state"),
                    "review_id": task.get("review_id"),
                    "review_name": review.get("review_name"),
                    "review_status": review.get("status")
                })

            return {
                "source_file": source_file,
                "table": "reviews_review_tasks",
                "user": user_name or user_id,
                "pending_count": len(pending_result),
                "pending_reviews": pending_result[:50]
            }

        return {"error": f"Unknown tool: {tool_name}"}
