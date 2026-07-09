"""Data Analyst Agent for issues, RFIs, RFAs, submittals, transmittals, tickets, and BOM/BOQ analysis"""
from typing import Any, Dict, List, Optional
import json
import time

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools
from data_layer.time_period_parser import TimePeriodContext

# Shared tool schema: Krion6d-style workflow entities expose review_status separately from workflow "status".
_REVIEW_STATUS_PARAM = {
    "type": "integer",
    "enum": [1, 2, 3, 4, 5],
    "description": (
        "Review outcome: 1=open/pending, 2=answered/approved, 3=rejected, 4=comment, 5=auto approved. "
        "Use for pending/answered/rejected wording; do not use workflow status (nameForApproval) for that."
    ),
}
_WORKFLOW_STATUS_PARAM_DESC = (
    "Workflow step from nameForApproval (e.g. Create, In Progress, Close). "
    "Only when the user asks for that step by name — not for pending vs approved/rejected; use review_status."
)


class DataAnalystAgent(BaseAgent):
    """Agent for analyzing issues, RFIs, RFAs, submittals, transmittals, tickets, BOM/BOQ, and general project data"""

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "data_analyst"

    @property
    def description(self) -> str:
        return """Analyzes issues, RFIs, RFAs, submittals, transmittals, tickets, BOM/BOQ (bill of materials and bill of quantities — same data in the boms table), project document files (Krion6d documents table — PDF, RVT, etc.), and general project data.
        Creates reports, identifies trends, generates status breakdowns,
        and provides visualizations for construction project metrics.
        Note: RFAs (Request for Approval) are different from RFIs (Request for Information)."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "issues_analysis",
            "rfi_analysis",
            "rfa_analysis",
            "submittal_tracking",
            "transmittal_tracking",
            "ticket_tracking",
            "bom_boq_analysis",
            "project_document_files",
            "trend_analysis",
            "status_breakdown",
            "overdue_items",
            "assignee_workload",
            "priority_analysis",
            "project_comparison"
        ]

    async def process(self, query: str, context=None):
        """Override to pass context to system prompt for workflow statuses"""
        self._workflow_context = context
        return await super().process(query, context)

    @staticmethod
    def _apply_review_status_filter(tool_input: Dict, filters: Dict) -> None:
        if tool_input.get("review_status") is not None:
            rs = tool_input["review_status"]
            filters["review_status"] = int(rs) if isinstance(rs, (int, float)) else rs

    @staticmethod
    def _apply_name_contains_filters(
        tool_input: Dict, filters: Dict, fields: tuple
    ) -> None:
        """Partial, case-insensitive match on person / name columns (QueryEngine contains)."""
        for param in fields:
            val = tool_input.get(param)
            if val is None or val == "":
                continue
            filters[param] = {"contains": str(val).strip()}

    @staticmethod
    def _is_worklog_hours_query(query_text: str) -> bool:
        q = (query_text or "").lower()
        return any(token in q for token in ["worklog", "work log", "logged hours", "worklog hours", "work log hours"])

    @staticmethod
    def _is_work_hours_query(query_text: str) -> bool:
        q = (query_text or "").lower()
        if DataAnalystAgent._is_worklog_hours_query(q):
            return False
        return "work hours" in q or "working hours" in q

    @staticmethod
    def _project_id_filter_values(project_id: str) -> List[Any]:
        """Match project_id stored as string or int in DataFrames."""
        vals: List[Any] = [project_id]
        s = str(project_id).strip()
        if s.isdigit():
            vals.append(int(s))
        return vals

    @staticmethod
    def _normalize_file_extension_filter(ext: Optional[str]) -> Optional[str]:
        if ext is None or (isinstance(ext, str) and not ext.strip()):
            return None
        s = str(ext).strip().lower()
        return s if s.startswith(".") else f".{s}"

    @staticmethod
    def _infer_extension(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        clean = text.rstrip("/").split("?", 1)[0]
        if "." not in clean:
            return ""
        ext = clean.rsplit(".", 1)[-1].strip().lower()
        return f".{ext}" if ext else ""

    @staticmethod
    def _to_list_payload(value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [item for item in parsed if isinstance(item, dict)]
            except Exception:
                return []
        return []

    def _build_system_prompt(self, context=None) -> str:
        """Override to add workflow status knowledge from actual data"""
        base_prompt = super()._build_system_prompt()

        # Build workflow status section from actual data
        ctx = getattr(self, '_workflow_context', None) or context or {}
        workflow_statuses = ctx.get("workflow_statuses", {}) if isinstance(ctx, dict) else {}

        workflow_section = """

IMPORTANT - Workflow-backed entities: review outcome vs workflow step

For issues, RFIs, RFAs, submittals, transmittals, tickets, and any other table that has a
"review_status" column, these are separate — do not confuse them:

1. "review_status" (numeric) — pending vs answered/approved vs rejected (review outcome).
   Use for ANY user wording like: pending, open (awaiting response), answered, approved,
   accepted, rejected, "still open", etc.
   Codes: 1 = open/pending, 2 = answered/approved, 3 = rejected.
   (If present: 4 = comment, 5 = auto approved — treat like answered when the user means "resolved".)

2. "status" — workflow step label from nameForApproval (e.g. Create, In Progress, Close).
   Use ONLY when the user explicitly asks for that workflow stage by name, not for
   pending/answered/rejected in the sense above.

3. "review_step" — named review step from reviewStepName (which gate the item is in).
   Use for "what step is this in" / "which review stage", not for pending vs answered.

When the table has "review_status": filter and explain pending/answered/rejected using
review_status and the numeric meanings above — not using "status" (nameForApproval).
If a table has no review_status column, use workflow "status" and project-specific values only.

BOM and BOQ (bill of quantities) are the same domain for users: use the "boms" table and query_boms for either wording.

Project document files (PDF, Revit, DWG, etc.): use the "documents" table and query_documents — not photos/markups.
"""
        if workflow_statuses:
            workflow_section += "\nACTUAL STATUS VALUES FROM THIS PROJECT'S DATA:\n"
            for entity, info in workflow_statuses.items():
                if isinstance(info, dict):
                    statuses = info.get("statuses", [])
                    steps = info.get("review_steps", [])
                    rev_stat = info.get("review_statuses", [])
                    workflow_section += f"- {entity}:\n"
                    if statuses:
                        workflow_section += f"    status values: {statuses}\n"
                    if steps:
                        workflow_section += f"    review_step values: {steps}\n"
                    if rev_stat:
                        workflow_section += f"    review_status values in data: {rev_stat}\n"
                else:
                    workflow_section += f"- {entity}: status values: {info}\n"
            workflow_section += """
CRITICAL: For workflow "status" and "review_step", use ONLY the exact values listed above
when filtering those columns. For any entity that has review_status in the data, pending /
answered / rejected / open (awaiting response) MUST use review_status integers
(1 = pending, 2 = answered/approved, 3 = rejected), not the workflow "status" list above.
"""
        else:
            workflow_section += """
Default workflow statuses (may differ per organization):
- Most entities: "Create" (new), "In Progress" (active), "Close" (done)
"""

        workflow_section += """
STATUS MAPPING FOR USER QUERIES:
- Tables with review_status (issues, RFIs, RFAs, submittals, transmittals, tickets, etc.):
  "pending", "open" (awaiting answer), "not answered" -> review_status = 1
  "answered", "approved", "accepted" -> review_status = 2
  "rejected" -> review_status = 3
  Counts/breakdowns of pending vs answered -> group_by "review_status", not workflow "status".
- Tables without review_status: map "open"/"pending" to workflow "status" using project-specific
  values when listed above.
- Workflow-only phrasing ("Create", "In Progress", "Close", "closed" as last step) -> filter "status"
  with the exact strings from the data.
- "new" / "draft" -> often first workflow status (often "Create")
- "what step" / "current step" / "review stage" -> review_step field

RFIs — person wording (uses name columns after ACC resolution):
- "Raised by" / "created by" / "submitted by [name]" -> query_rfis with parameter submitted_by (partial name, e.g. "Manoj").
- "Assigned to [name]" -> query_rfis with assigned_to.
- After filtering, put that tool result in the response "data" and include charts (e.g. breakdown by status or review_status).

IMPORTANT: If unsure, use group_and_count on "review_status" (if present), else "status" or "review_step".

PROJECT "REVIEWS" BY OUTCOME (pending / completed / rejected):
- Questions that categorize or count reviews by outcome (review_status 1 vs 2 vs 3) refer to workflow
  entities such as issues, RFIs, RFAs, submittals, transmittals, tickets — use group_and_count with
  group_by "review_status" on those tables (often start with "issues" when the user says "all reviews").
- Do not treat the "schedule" table as the full set of project reviews for outcome breakdowns; schedule
  holds schedule/task rows, which are a different slice than issue/RFI review workflows.

RFA HOURS MAPPING:
- RFAs expose two different hour fields:
  - work_hours: derived planned working hours between start_date and due_date excluding weekends, multiplied by 8.
  - worklog_hours: logged/tracked worklog hours.
- If user asks "work hours" for RFAs, prioritize `work_hours`.
- Use `worklog_hours` only when user explicitly asks for work log/worklog/logged hours.

"""
        return base_prompt + workflow_section

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_issues",
                "description": "Query issues with filters. For pending/answered/rejected use review_status when present, not workflow status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {
                            "type": "string",
                            "enum": ["Create", "In Progress", "Close", "all"],
                            "description": _WORKFLOW_STATUS_PARAM_DESC + " Enum examples when applicable."
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assignee display name (partial match).",
                        },
                        "issue_type_id": {"type": "string", "description": "Filter by issue type ID"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_rfis",
                "description": (
                    "Query RFIs data with filters. For pending/answered/rejected/open RFIs use review_status, not workflow status. "
                    "For 'raised by' / 'created by' / 'submitted by' questions use submitted_by (creator). "
                    "For 'assigned to' use assigned_to. Names match partially (e.g. 'Manoj' matches 'Manoj M')."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {
                            "type": "string",
                            "enum": ["Create", "In Progress", "Close", "all"],
                            "description": _WORKFLOW_STATUS_PARAM_DESC,
                        },
                        "priority": {"type": "string", "description": "Filter by priority"},
                        "discipline": {"type": "string", "description": "Filter by discipline"},
                        "submitted_by": {
                            "type": "string",
                            "description": "Who raised/created the RFI (maps to submitted_by column; partial name match).",
                        },
                        "assigned_to": {
                            "type": "string",
                            "description": "Assignee name (partial match; column assigned_to).",
                        },
                        "overdue_only": {"type": "boolean", "description": "Show only overdue RFIs"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_submittals",
                "description": "Query submittals with filters. For pending/answered/rejected use review_status when present.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {"type": "string", "description": _WORKFLOW_STATUS_PARAM_DESC},
                        "submittal_type": {"type": "string", "description": "Filter by submittal type"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_rfas",
                "description": "Query RFAs (Request for Approval) with filters. For pending/answered/rejected use review_status, not workflow status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {"type": "string", "description": _WORKFLOW_STATUS_PARAM_DESC},
                        "priority": {"type": "string", "description": "Filter by priority"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_tickets",
                "description": "Query tickets with filters. For pending/answered/rejected use review_status when present.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {"type": "string", "description": _WORKFLOW_STATUS_PARAM_DESC},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_transmittals",
                "description": "Query transmittals with filters. For pending/answered/rejected use review_status when present.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "review_status": _REVIEW_STATUS_PARAM,
                        "status": {"type": "string", "description": _WORKFLOW_STATUS_PARAM_DESC},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_boms",
                "description": "Query BOM (Bill of Materials) rows. BOQ / bill-of-quantities questions use this same table and tool.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "status": {"type": "string", "description": "Filter by workflow or item status when present"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                    }
                }
            },
            {
                "name": "query_documents",
                "description": "Query project document files (Krion6d). List all files, PDFs, RVT/Revit files, etc. Uses file_extension (e.g. .pdf, .rvt).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Filter by project ID"},
                        "file_extension": {
                            "type": "string",
                            "description": "Optional extension filter: pdf, .pdf, RVT, .rvt — normalized automatically",
                        },
                        "limit": {"type": "integer", "description": "Maximum results", "default": 500},
                    },
                },
            },
            {
                "name": "group_and_count",
                "description": "Group data by a field and count occurrences. For pending vs completed vs rejected, group_by review_status on issues/rfis/etc.; not schedule (schedule is tasks, not full workflow review counts).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "enum": ["issues", "rfis", "rfas", "submittals", "transmittals", "tickets", "boms", "documents", "projects"],
                            "description": "Table to query"
                        },
                        "group_by": {"type": "string", "description": "Column to group by (e.g. review_status for pending vs approved, else status, priority, assignee)"},
                        "filters": {"type": "object", "description": "Optional filters to apply"}
                    },
                    "required": ["table", "group_by"]
                }
            },
            {
                "name": "get_overdue_items",
                "description": "Get overdue issues or RFIs that are past their due date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "enum": ["issues", "rfis", "rfas", "submittals", "transmittals", "tickets"],
                            "description": "Table to query"
                        },
                        "project_id": {"type": "string", "description": "Optional project filter"}
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "get_trend_data",
                "description": "Get trend data over time periods for analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table to query"},
                        "date_column": {"type": "string", "description": "Date column to use"},
                        "period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Grouping period"
                        }
                    },
                    "required": ["table", "date_column", "period"]
                }
            },
            {
                "name": "get_data_by_period",
                "description": "Query a table filtered to the provided time period (from context.time_filter if not explicitly provided).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "enum": ["issues", "rfis", "rfas", "submittals", "transmittals", "tickets", "projects", "schedule", "safety_observations", "boms", "documents"],
                            "description": "Table to query"
                        },
                        "date_column": {
                            "type": "string",
                            "description": "Optional override for the date column (e.g. due_date, created_date, updated_date). If omitted, chosen automatically."
                        },
                        "period_type": {
                            "type": "string",
                            "description": "Optional override for period type"
                        },
                        "period_label": {
                            "type": "string",
                            "description": "Optional override for human readable label"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Optional override start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Optional override end date (YYYY-MM-DD)"
                        },
                        "limit": {"type": "integer", "description": "Max rows", "default": 200},
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional column subset"
                        }
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "get_trend_over_period",
                "description": "Get trend data grouped by a granularity (daily/weekly/monthly/quarterly/yearly) within the provided time period (from context.time_filter if not provided).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {
                            "type": "string",
                            "enum": ["issues", "rfis", "rfas", "submittals", "transmittals", "tickets", "projects", "schedule", "safety_observations", "boms", "documents"],
                            "description": "Table to query"
                        },
                        "date_column": {
                            "type": "string",
                            "description": "Optional override for the date column (e.g. due_date, created_date, updated_date). If omitted, chosen automatically."
                        },
                        "group_period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"],
                            "description": "Grouping granularity"
                        },
                        "period_type": {
                            "type": "string",
                            "description": "Optional override for period type"
                        },
                        "period_label": {
                            "type": "string",
                            "description": "Optional override for human readable label"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Optional override start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Optional override end date (YYYY-MM-DD)"
                        },
                        "count_column": {
                            "type": "string",
                            "description": "Optional metric column; if omitted, counts records"
                        }
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "get_summary_stats",
                "description": "Get summary statistics for a table",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"}
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "compare_projects",
                "description": "Compare metrics across projects",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table to analyze"},
                        "metric": {
                            "type": "string",
                            "enum": ["count", "status_breakdown", "priority_breakdown"],
                            "description": "Metric to compare. status_breakdown uses review_status when that column exists on the table, else workflow status."
                        }
                    },
                    "required": ["table"]
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""

        if tool_name == "query_issues":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status") and tool_input["status"] != "all":
                filters["status"] = tool_input["status"]
            if tool_input.get("assignee"):
                filters["assignee"] = {"contains": str(tool_input["assignee"]).strip()}
            if tool_input.get("issue_type_id"):
                filters["issue_type_id"] = tool_input["issue_type_id"]

            limit = tool_input.get("limit", 100)
            return self.data_tools.query_table("issues", filters, limit=limit)

        elif tool_name == "query_rfis":
            if tool_input.get("overdue_only"):
                return self.data_tools.get_overdue_items(
                    "rfis",
                    open_statuses=["Create", "In Progress"]
                )

            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status") and tool_input["status"] != "all":
                filters["status"] = tool_input["status"]
            if tool_input.get("priority"):
                filters["priority"] = tool_input["priority"]
            if tool_input.get("discipline"):
                filters["discipline"] = tool_input["discipline"]
            self._apply_name_contains_filters(
                tool_input,
                filters,
                ("submitted_by", "assigned_to"),
            )

            limit = tool_input.get("limit", 100)
            return self.data_tools.query_table("rfis", filters, limit=limit)

        elif tool_name == "query_submittals":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]
            if tool_input.get("submittal_type"):
                filters["submittal_type"] = tool_input["submittal_type"]

            limit = tool_input.get("limit", 100)
            result = self.data_tools.query_table("submittals", filters, limit=limit)
            if (
                isinstance(result, dict)
                and result.get("returned_rows", len(result.get("data", []))) == 0
            ):
                dashboard = self.data_tools.query_table("dashboard_summary", {"entity": "submittal"}, limit=200)
                if isinstance(dashboard, dict) and dashboard.get("data"):
                    return {
                        "source_file": dashboard.get("source_file"),
                        "table": "submittals",
                        "total_rows": len(dashboard.get("data", [])),
                        "returned_rows": len(dashboard.get("data", [])),
                        "data": dashboard.get("data", []),
                        "note": "Submittals list endpoint returned empty; showing dashboard status data fallback.",
                    }
            return result

        elif tool_name == "query_rfas":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]
            if tool_input.get("priority"):
                filters["priority"] = tool_input["priority"]

            limit = tool_input.get("limit", 100)
            query_text = ""
            if self._current_context and isinstance(self._current_context.get("original_query"), str):
                query_text = self._current_context.get("original_query", "")

            columns = None
            if self._is_work_hours_query(query_text):
                columns = [
                    "rfa_id",
                    "project_id",
                    "title",
                    "status",
                    "start_date",
                    "due_date",
                    "work_hours",
                    "worklog_hours",
                ]
            elif self._is_worklog_hours_query(query_text):
                columns = [
                    "rfa_id",
                    "project_id",
                    "title",
                    "status",
                    "start_date",
                    "due_date",
                    "worklog_hours",
                    "work_hours",
                ]

            return self.data_tools.query_table("rfas", filters, columns=columns, limit=limit)

        elif tool_name == "query_tickets":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            limit = tool_input.get("limit", 100)
            return self.data_tools.query_table("tickets", filters, limit=limit)

        elif tool_name == "query_transmittals":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = tool_input["project_id"]
            self._apply_review_status_filter(tool_input, filters)
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]

            limit = tool_input.get("limit", 100)
            result = self.data_tools.query_table("transmittals", filters, limit=limit)
            if (
                isinstance(result, dict)
                and result.get("returned_rows", len(result.get("data", []))) == 0
            ):
                dashboard = self.data_tools.query_table("dashboard_summary", {"entity": "transmittal"}, limit=200)
                if isinstance(dashboard, dict) and dashboard.get("data"):
                    return {
                        "source_file": dashboard.get("source_file"),
                        "table": "transmittals",
                        "total_rows": len(dashboard.get("data", [])),
                        "returned_rows": len(dashboard.get("data", [])),
                        "data": dashboard.get("data", []),
                        "note": "Transmittals list endpoint returned empty; showing dashboard status data fallback.",
                    }
            return result

        elif tool_name == "query_boms":
            filters = {}
            if tool_input.get("project_id"):
                filters["project_id"] = self._project_id_filter_values(tool_input["project_id"])
            if tool_input.get("status"):
                filters["status"] = tool_input["status"]
            limit = tool_input.get("limit", 100)
            return self.data_tools.query_table("boms", filters, limit=limit)

        elif tool_name == "query_documents":
            filters: Dict[str, Any] = {}
            if tool_input.get("project_id"):
                filters["project_id"] = self._project_id_filter_values(tool_input["project_id"])
            ext = self._normalize_file_extension_filter(tool_input.get("file_extension"))
            if ext:
                filters["file_extension"] = ext
            limit = tool_input.get("limit", 500)
            original_query = ""
            if self._current_context and isinstance(self._current_context.get("original_query"), str):
                original_query = self._current_context.get("original_query")
            q_lower = original_query.lower()
            attachment_scope_query = (
                ("submittal" in q_lower or "transmittal" in q_lower)
                and any(k in q_lower for k in ("attach", "attachment", "document", "file"))
            )
            result = self.data_tools.query_table("documents", filters, limit=limit)
            # For "submittals with attached documents", never return project-wide docs:
            # return only attachment-linked docs derived from workflow_attachments.
            if attachment_scope_query:
                workflow_filters: Dict[str, Any] = {
                    "project_id": filters.get("project_id", [])
                }
                if ext:
                    workflow_filters["file_extension"] = ext
                mentions_submittal = "submittal" in q_lower
                mentions_transmittal = "transmittal" in q_lower
                if mentions_submittal and not mentions_transmittal:
                    workflow_filters["entity_type"] = ["submittal"]
                elif mentions_transmittal and not mentions_submittal:
                    workflow_filters["entity_type"] = ["transmittal"]
                else:
                    workflow_filters["entity_type"] = ["submittal", "transmittal"]

                workflow_rows_result = self.data_tools.query_table(
                    "workflow_attachments", workflow_filters, limit=5000
                )
                workflow_rows = (
                    workflow_rows_result.get("data", [])
                    if isinstance(workflow_rows_result, dict)
                    else []
                )
                attachment_rows: List[Dict[str, Any]] = []
                for row in workflow_rows:
                    if not isinstance(row, dict):
                        continue
                    entity_type = str(row.get("entity_type", "")).lower()
                    entity_id = row.get("entity_id")
                    attachment_rows.append(
                        {
                            "project_id": row.get("project_id"),
                            "submittal_id": entity_id if entity_type == "submittal" else None,
                            "transmittal_id": entity_id if entity_type == "transmittal" else None,
                            "document_id": row.get("document_id"),
                            "document_name": row.get("document_name"),
                            "file_extension": row.get("file_extension") or "unknown",
                            "version": row.get("version"),
                            "revision": row.get("revision"),
                            "file_url": row.get("file_url"),
                            "action": row.get("action"),
                            "created_at": row.get("created_at"),
                            "created_by": row.get("created_by"),
                            "source": "workflow_attachments",
                        }
                    )
                if attachment_rows:
                    return {
                        "source_file": "Krion6d API: workflow_attachments",
                        "table": "documents",
                        "total_rows": len(attachment_rows),
                        "returned_rows": len(attachment_rows),
                        "data": attachment_rows[:limit],
                        "note": "Showing only documents attached to submittals/transmittals.",
                    }
                return {
                    "source_file": (
                        workflow_rows_result.get("source_file")
                        if isinstance(workflow_rows_result, dict)
                        else None
                    ),
                    "table": "documents",
                    "total_rows": 0,
                    "returned_rows": 0,
                    "data": [],
                    "note": (
                        "No attachment-linked document rows are available from submittal records "
                        "for this project in the current data source."
                    ),
                }

            if isinstance(result, dict):
                has_error = bool(result.get("error"))
                returned_rows = int(result.get("returned_rows", len(result.get("data", [])) or 0))
                if has_error or returned_rows == 0:
                    submittals = self.data_tools.query_table("submittals", {}, limit=5000)
                    records = submittals.get("data", []) if isinstance(submittals, dict) else []
                    allowed_project_ids = {str(v) for v in filters.get("project_id", [])}
                    attachment_rows: List[Dict[str, Any]] = []
                    for row in records:
                        if not isinstance(row, dict):
                            continue
                        row_project_id = row.get("project_id")
                        if allowed_project_ids and str(row_project_id) not in allowed_project_ids:
                            continue
                        for att in self._to_list_payload(row.get("attachments")):
                            if str(att.get("type", "")).lower() != "document":
                                continue
                            document_name = att.get("name") or att.get("title")
                            file_url = att.get("path") or att.get("url")
                            file_extension = (
                                self._infer_extension(att.get("extension"))
                                or self._infer_extension(document_name)
                                or self._infer_extension(file_url)
                            )
                            if ext and file_extension != ext:
                                continue
                            attachment_rows.append(
                                {
                                    "project_id": row_project_id,
                                    "submittal_id": row.get("submittal_id") or row.get("id"),
                                    "submittal_code": row.get("submittal_code") or row.get("code"),
                                    "submittal_title": row.get("title"),
                                    "document_id": att.get("id"),
                                    "document_name": document_name,
                                    "file_extension": file_extension or "unknown",
                                    "version": att.get("version"),
                                    "revision": att.get("revision"),
                                    "file_url": file_url,
                                    "review_status": att.get("reviewStatus"),
                                    "source": "submittal_attachments",
                                }
                            )
                    if attachment_rows:
                        result = {
                            "source_file": "Krion6d API: submittals/attachments",
                            "table": "documents",
                            "total_rows": len(attachment_rows),
                            "returned_rows": len(attachment_rows),
                            "data": attachment_rows[:limit],
                            "note": (
                                "Documents extracted from submittal attachments because "
                                "documents table was empty or unavailable."
                            ),
                        }
            return result

        elif tool_name == "group_and_count":
            return self.agg_tools.group_and_count(
                tool_input["table"],
                tool_input["group_by"],
                tool_input.get("filters")
            )

        elif tool_name == "get_overdue_items":
            table = tool_input["table"]
            # Workflow status values (nameForApproval field)
            open_statuses = {
                "issues": ["Create", "In Progress"],
                "rfis": ["Create", "In Progress"],
                "rfas": ["Create", "In Progress"],
                "submittals": ["Create", "In Progress"],
                "transmittals": ["Create", "In Progress"],
                "tickets": ["Create", "In Progress"],
            }.get(table, ["Create", "In Progress"])

            items = self.data_tools.get_overdue_items(table, open_statuses=open_statuses)

            # Filter by project if specified
            if tool_input.get("project_id") and isinstance(items, list):
                items = [i for i in items if i.get("project_id") == tool_input["project_id"]]

            return items

        elif tool_name == "get_trend_data":
            return self.agg_tools.get_trend_data(
                tool_input["table"],
                tool_input["date_column"],
                tool_input["period"]
            )

        elif tool_name == "get_data_by_period":
            table = tool_input["table"]

            tf = {}
            if self._current_context and isinstance(self._current_context.get("time_filter"), dict):
                tf = self._current_context.get("time_filter") or {}

            period = TimePeriodContext(
                period_type=tool_input.get("period_type") or tf.get("period_type") or "custom",
                period_label=tool_input.get("period_label") or tf.get("period_label") or "",
                start_date=tool_input.get("start_date") or tf.get("start_date"),
                end_date=tool_input.get("end_date") or tf.get("end_date"),
            )

            if not period.start_date or not period.end_date:
                return {"error": "time_filter is missing start_date/end_date and tool_input didn't provide them"}

            original_query = ""
            if self._current_context and isinstance(self._current_context.get("original_query"), str):
                original_query = self._current_context.get("original_query")

            date_column = tool_input.get("date_column")
            if not date_column:
                date_column = self.query_engine.get_relevant_date_field(table, original_query)

            return self.data_tools.get_data_by_period(
                table,
                date_column,
                period,
                columns=tool_input.get("columns"),
                limit=tool_input.get("limit", 200),
            )

        elif tool_name == "get_trend_over_period":
            table = tool_input["table"]

            tf = {}
            if self._current_context and isinstance(self._current_context.get("time_filter"), dict):
                tf = self._current_context.get("time_filter") or {}

            period = TimePeriodContext(
                period_type=tool_input.get("period_type") or tf.get("period_type") or "custom",
                period_label=tool_input.get("period_label") or tf.get("period_label") or "",
                start_date=tool_input.get("start_date") or tf.get("start_date"),
                end_date=tool_input.get("end_date") or tf.get("end_date"),
            )

            if not period.start_date or not period.end_date:
                return {"error": "time_filter is missing start_date/end_date and tool_input didn't provide them"}

            original_query = ""
            if self._current_context and isinstance(self._current_context.get("original_query"), str):
                original_query = self._current_context.get("original_query")

            date_column = tool_input.get("date_column")
            if not date_column:
                date_column = self.query_engine.get_relevant_date_field(table, original_query)

            # Default drill grouping = next granularity relative to the selected period.
            group_period = tool_input.get("group_period")
            if not group_period:
                group_period = {
                    "year": "quarterly",
                    "quarter": "monthly",
                    "month": "weekly",
                    "week": "daily",
                    "custom": "weekly",
                    "day": "daily",
                }.get(period.period_type, "weekly")

            return self.data_tools.get_trend_over_period(
                table,
                date_column,
                group_period,
                period,
                count_column=tool_input.get("count_column"),
            )

        elif tool_name == "get_summary_stats":
            return self.query_engine.get_summary_stats(tool_input["table"])

        elif tool_name == "compare_projects":
            table = tool_input["table"]
            metric = tool_input.get("metric", "count")

            if metric == "count":
                return self.agg_tools.group_and_count(table, "project_id")
            elif metric == "status_breakdown":
                df = self.query_engine.dfs.get(table)
                use_review = df is not None and "review_status" in df.columns
                breakdown_col = "review_status" if use_review else "status"
                return self.agg_tools.cross_tabulate(table, "project_id", breakdown_col)
            elif metric == "priority_breakdown":
                return self.agg_tools.cross_tabulate(table, "project_id", "priority")

        return {"error": f"Unknown tool: {tool_name}"}
