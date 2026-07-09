"""Base agent class for all specialist agents"""
from abc import ABC, abstractmethod
from collections import Counter
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import logging

from llm_providers.base import BaseLLMProvider, LLMResponse
from data_layer.query_engine import QueryEngine
from .interaction_logger import get_tracer
from .tools.drill_down_tools import DrillDownTools
from data_layer.time_period_parser import TimePeriodContext

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Configuration for a chart visualization"""
    chart_type: str  # 'bar', 'pie', 'line', 'doughnut', 'table', 'kpi'
    title: str
    data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Standardized agent response"""
    success: bool
    data: Any
    message: str
    charts: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "charts": self.charts or [],
            "metadata": self.metadata or {},
            "error": self.error
        }


class BaseAgent(ABC):
    """Base class for all specialist agents"""

    def __init__(self, llm_provider: BaseLLMProvider, query_engine: QueryEngine):
        self.llm = llm_provider
        self.query_engine = query_engine
        self.tools = self._register_tools()
        self._append_drill_down_tool()
        self._drill_down_tools = DrillDownTools()
        self.max_iterations = 15  # Increased to handle complex multi-step queries
        self._current_context = None  # Store context for auto-injection

    def _append_drill_down_tool(self) -> None:
        """
        Ensure all agents have access to drill-down follow-up generation.
        """
        tool_name = "generate_drill_down_followups"
        if any(t.get("name") == tool_name for t in self.tools):
            return

        self.tools.append(
            {
                "name": tool_name,
                "description": "Generate time drill-down follow-up questions from the provided time period (or from context.time_filter).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity": {
                            "type": "string",
                            "description": "Entity/table to drill down, e.g. issues, rfis, submittals, schedule"
                        },
                        "period_type": {
                            "type": "string",
                            "description": "Optional; if omitted uses context time_filter"
                        },
                        "period_label": {
                            "type": "string",
                            "description": "Optional; if omitted uses context time_filter"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Optional; YYYY-MM-DD. If omitted uses context time_filter"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Optional; YYYY-MM-DD. If omitted uses context time_filter"
                        },
                    },
                    "required": ["entity"],
                },
            }
        )

    def _handle_generate_drill_down_followups(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic tool handler (no LLM calls).
        """
        entity = tool_input.get("entity") or "items"

        # Prefer explicit tool inputs; otherwise use context.time_filter
        tf = self._current_context.get("time_filter") if self._current_context else None

        period_type = tool_input.get("period_type") or (tf.get("period_type") if isinstance(tf, dict) else None)
        period_label = tool_input.get("period_label") or (tf.get("period_label") if isinstance(tf, dict) else None)
        start_date = tool_input.get("start_date") or (tf.get("start_date") if isinstance(tf, dict) else None)
        end_date = tool_input.get("end_date") or (tf.get("end_date") if isinstance(tf, dict) else None)

        if not (period_type and period_label and start_date and end_date):
            return {"follow_up_questions": []}

        period = TimePeriodContext(
            period_type=period_type,
            period_label=str(period_label),
            start_date=str(start_date),
            end_date=str(end_date),
        )

        return self._drill_down_tools.generate_drill_down_followups(
            entity=entity,
            period=period,
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name identifier"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this agent does"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of capabilities for routing"""
        pass

    @abstractmethod
    def _register_tools(self) -> List[Dict]:
        """Register agent-specific tools"""
        pass

    @abstractmethod
    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific tool"""
        pass

    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent"""
        available_tables = self.query_engine.get_tables()

        return f"""You are the {self.name} agent in a construction project analytics system.

Your role: {self.description}

Your capabilities: {', '.join(self.capabilities)}

You have access to Excel data exported from Autodesk Construction Cloud (ACC).
Available data tables: {', '.join(available_tables)}

Instructions:
1. Analyze the user's query to understand what data or insights they need
2. Use your tools to query and analyze the data
3. Provide clear, actionable insights based on the data
4. When appropriate, suggest visualizations (charts) to display the data

TIME PERIOD AWARENESS (drill-down ready):
If the system/user provides a `time_filter` in the context (JSON-encoded under "Additional context"),
the time_filter will include:
  - start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
  - period_type (week|month|quarter|year|custom)
  - period_label (human readable)

When `time_filter` is present:
  - Apply the date range when filtering/grouping (use the tools that support date ranges).
  - Produce charts/tables scoped to the requested period.
  - Prefer these tools when available:
      - `get_data_by_period` for lists/tables scoped to the selected date range
      - `get_trend_over_period` for time-series charts grouped by week/month/quarter/year
  - Always generate drill-down follow-up questions at the *next granularity* when possible:
      year -> quarter -> month -> week -> day
  - Use the tool `generate_drill_down_followups` to generate the drill-down follow-up questions.
  - Example follow-ups:
      - "Show issues by quarter within Q1 2025"
      - "Show RFIs by week within March 2025"
      - "Show overdue issues on 2025-03-12"

If you cannot apply the time_filter to a given data/table, explain it in `insights` and still provide useful follow-up questions.

When generating chart configurations, use this format for bar/pie/line/doughnut:
{{
    "type": "bar|pie|line|doughnut",
    "title": "Chart title",
    "data": {{
        "labels": ["Label1", "Label2", ...],
        "datasets": [{{
            "label": "Dataset name",
            "data": [value1, value2, ...]
        }}]
    }}
}}

For TABLE widgets (required for tabular results — the UI needs explicit column names):
{{
    "type": "table",
    "title": "Table title",
    "data": {{
        "headers": ["column_name_1", "column_name_2", "start_date", "due_date"],
        "rows": [
            ["value row1 col1", "value row1 col2", "2026-02-20", "2026-03-15"],
            ["value row2 col1", "value row2 col2", "2026-02-21", "2026-03-20"]
        ]
    }}
}}
- "headers" MUST be the human-readable or schema column names (same order as each row array).
- Each "rows" entry MUST be an array of cell values aligned with "headers" (not a JSON object per row).
- When showing dates, use ISO strings or the same formatting as the source data.

For KPI widgets:
{{
    "type": "kpi",
    "title": "Metric Name",
    "data": {{
        "value": 42,
        "unit": "items",
        "trend": "up|down|stable",
        "change": "+5%"
    }}
}}

Always respond with a JSON object containing:
{{
    "data": <query results or processed data>,
    "insights": "Your analysis and key findings",
    "charts": [<chart configurations>],
    "follow_up_questions": ["question 1", "question 2", "question 3"]
}}

CRITICAL — charts vs text only:
- If the user asks for a chart, graph, plot, visualization, breakdown, trend, distribution, or counts by category/status, you MUST set "charts" to a non-empty array with at least one valid chart object matching the formats above.
- When you used group_and_count, get_trend_data, get_trend_over_period, get_data_by_period, or compare_projects, copy the tool output into "data" and build charts from that same data — do not leave "charts" empty while summarizing aggregated numbers in "insights".

FOLLOW-UP QUESTIONS:
- Always include 2-3 relevant follow-up questions the user might want to ask next
- Questions should be specific to the data/context of the current query
- Make them actionable and useful for deeper analysis
- Examples: "Show overdue items", "Break down by assignee", "Compare with last month"
"""

    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process a query using the agentic loop"""
        tracer = get_tracer()
        system_prompt = self._build_system_prompt()

        # Store context for auto-injection into tool calls
        self._current_context = context

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Add context if provided
        if context:
            context_str = f"\n\nAdditional context: {json.dumps(context)}"
            messages[-1]["content"] += context_str

        # Agentic loop
        drill_followups: Optional[List[str]] = None
        for iteration in range(self.max_iterations):
            try:
                # Log thinking state
                if iteration > 0:
                    tracer.log_agent_thinking(
                        self.name,
                        f"Processing iteration {iteration + 1}/{self.max_iterations}..."
                    )

                response = await self.llm.chat(messages, tools=self.tools)

                # If no tool calls, we have the final response
                if not response.tool_calls:
                    agent_response = self._parse_final_response(response.content)
                    agent_response = self._supplement_charts_if_missing(agent_response)
                    if drill_followups:
                        existing = None
                        if agent_response.metadata and isinstance(agent_response.metadata, dict):
                            existing = agent_response.metadata.get("follow_up_questions")
                        if not existing:
                            agent_response.metadata = agent_response.metadata or {}
                            agent_response.metadata["follow_up_questions"] = drill_followups
                    return agent_response

                # Execute each tool call
                for tool_call in response.tool_calls:
                    logger.info(f"Executing tool: {tool_call.tool_name}")

                    # Auto-inject project_id from context if not already specified
                    tool_input = tool_call.tool_input.copy() if tool_call.tool_input else {}
                    if self._current_context and self._current_context.get("project_id"):
                        if "project_id" not in tool_input or not tool_input["project_id"]:
                            tool_input["project_id"] = self._current_context["project_id"]
                            logger.info(f"Auto-injected project_id: {tool_input['project_id']}")

                    # Log tool call
                    tracer.log_tool_call(
                        self.name,
                        tool_call.tool_name,
                        tool_input
                    )

                    try:
                        if tool_call.tool_name == "generate_drill_down_followups":
                            result = self._handle_generate_drill_down_followups(tool_input)
                            if isinstance(result, dict) and isinstance(result.get("follow_up_questions"), list):
                                drill_followups = result.get("follow_up_questions")
                        else:
                            result = await self._execute_tool(tool_call.tool_name, tool_input)

                        # Log full result for frontend display
                        tracer.log_tool_result(
                            self.name,
                            tool_call.tool_name,
                            result
                        )

                        # Truncate large data results for LLM context
                        result_for_llm = self._truncate_result_for_llm(result)
                        result_str = json.dumps(result_for_llm, default=str)

                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        result_str = json.dumps({"error": str(e)})

                        # Log tool error
                        tracer.log_tool_result(
                            self.name,
                            tool_call.tool_name,
                            {"error": str(e)}
                        )

                    # Add assistant message with tool call
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [tool_call]
                    })

                    # Add tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.tool_id,
                        "content": result_str
                    })

            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                return AgentResponse(
                    success=False,
                    data=None,
                    message=f"Error processing query: {str(e)}",
                    error=str(e)
                )

        # Max iterations reached
        return AgentResponse(
            success=False,
            data=None,
            message="Maximum iterations reached without completing the query",
            error="max_iterations_reached"
        )

    @staticmethod
    def _table_cell_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _discover_dict_row_keys(rows: List[Any]) -> List[str]:
        order: List[str] = []
        seen = set()
        for rec in rows:
            if isinstance(rec, dict):
                for k in rec.keys():
                    if k not in seen:
                        seen.add(k)
                        order.append(k)
        return order

    @classmethod
    def _normalize_table_charts(cls, charts: Any) -> List[Any]:
        """Ensure table charts have headers and row arrays aligned for the frontend."""
        if not isinstance(charts, list):
            return []

        normalized: List[Any] = []
        for chart in charts:
            if not isinstance(chart, dict) or chart.get("type") != "table":
                normalized.append(chart)
                continue

            data = chart.get("data")
            if not isinstance(data, dict):
                normalized.append(chart)
                continue

            inner = dict(data)
            headers = inner.get("headers")
            rows = inner.get("rows")
            if rows is None and isinstance(inner.get("data"), list):
                rows = inner["data"]

            if not isinstance(rows, list):
                normalized.append(chart)
                continue

            if not rows:
                inner["headers"] = list(headers) if isinstance(headers, list) else []
                inner["rows"] = []
                normalized.append({**chart, "data": inner})
                continue

            first = rows[0]

            if isinstance(first, dict):
                if isinstance(headers, list) and headers:
                    hdr = [
                        h for h in headers
                        if any(isinstance(rec, dict) and h in rec for rec in rows)
                    ]
                    if not hdr:
                        hdr = cls._discover_dict_row_keys(rows)
                else:
                    hdr = cls._discover_dict_row_keys(rows)
                rows_out = [
                    [cls._table_cell_str(rec.get(k)) for k in hdr]
                    for rec in rows
                    if isinstance(rec, dict)
                ]
                inner["headers"] = hdr
                inner["rows"] = rows_out
            elif isinstance(first, (list, tuple)):
                lengths = [len(r) for r in rows if isinstance(r, (list, tuple))]
                n = max(lengths) if lengths else 0
                if isinstance(headers, list) and headers:
                    hdr = list(headers)
                    if len(hdr) < n:
                        hdr.extend(f"Column {i + 1}" for i in range(len(hdr), n))
                    elif len(hdr) > n:
                        hdr = hdr[:n]
                else:
                    hdr = [f"Column {i + 1}" for i in range(n)]
                rows_out = []
                for r in rows:
                    if isinstance(r, (list, tuple)):
                        padded = list(r) + [""] * (n - len(r))
                        rows_out.append([cls._table_cell_str(c) for c in padded[:n]])
                    else:
                        rows_out.append([cls._table_cell_str(r)] + [""] * (n - 1))
                inner["headers"] = hdr
                inner["rows"] = rows_out
            else:
                inner["headers"] = list(headers) if isinstance(headers, list) and headers else ["Value"]
                inner["rows"] = [[cls._table_cell_str(r)] for r in rows]

            normalized.append({**chart, "data": inner})

        return normalized

    def _supplement_charts_if_missing(self, agent_response: AgentResponse) -> AgentResponse:
        """Build Chart.js configs from structured tool results when the LLM omitted charts.

        The dashboard only renders visuals when `charts` is non-empty; models often
        return insights text without populating charts.
        """
        if agent_response.charts:
            return agent_response
        ct = getattr(self, "chart_tools", None)
        if ct is None:
            return agent_response
        raw = agent_response.data
        if raw is None:
            return agent_response
        if isinstance(raw, dict) and raw.get("error"):
            return agent_response

        new_charts: List[Dict[str, Any]] = []

        # Time-series: get_trend_data / get_trend_over_period envelope
        if isinstance(raw, dict) and isinstance(raw.get("data"), list) and raw["data"]:
            rows = raw["data"]
            r0 = rows[0] if isinstance(rows[0], dict) else {}
            if r0 and "period" in r0:
                value_key = "count" if "count" in r0 else next(
                    (k for k in r0.keys() if k != "period"), None
                )
                if value_key:
                    labels = [str(r.get("period", "")) for r in rows if isinstance(r, dict)]
                    vals = [
                        float(r.get(value_key, 0) or 0)
                        for r in rows
                        if isinstance(r, dict)
                    ]
                    title = f"{raw.get('table', 'Activity')} over time"
                    pt = str(raw.get("period") or "")
                    new_charts.append(
                        ct.create_timeline_line_chart(
                            labels,
                            [{"label": value_key, "data": vals}],
                            title,
                            period_type=pt,
                        )
                    )

        # group_and_count envelope (skip if we already added a trend chart for same dict)
        if not new_charts and isinstance(raw, dict) and isinstance(raw.get("data"), list):
            rows = raw["data"]
            gb = raw.get("group_by")
            if (
                rows
                and isinstance(rows[0], dict)
                and "count" in rows[0]
                and gb
                and "period" not in rows[0]
            ):
                table = raw.get("table", "Breakdown")
                if isinstance(gb, list) and len(gb) > 1:
                    labels = [
                        " / ".join(str(r.get(c, "")) for c in gb)
                        for r in rows
                        if isinstance(r, dict)
                    ]
                    vals = [float(r.get("count", 0) or 0) for r in rows if isinstance(r, dict)]
                    title = f"{table} by ({', '.join(gb)})"
                    horiz = len(labels) > 8
                    new_charts.append(
                        ct.create_bar_chart(
                            labels,
                            vals,
                            title,
                            dataset_label="Count",
                            horizontal=horiz,
                        )
                    )
                else:
                    col = gb[0] if isinstance(gb, list) else gb
                    if isinstance(col, str) and col in rows[0]:
                        title = f"{table} by {col}"
                        new_charts.append(ct.auto_chart(rows, col, "count", title))
                    else:
                        keys = [k for k in rows[0].keys() if k != "count"]
                        if keys:
                            col = keys[0]
                            title = f"{table} by {col}"
                            new_charts.append(ct.auto_chart(rows, col, "count", title))

        # Plain query_* tool rows (list of records, no group_by / no pre-aggregated count)
        if not new_charts:
            rows_list: Optional[List[Dict[str, Any]]] = None
            table_label = "Items"
            if isinstance(raw, list) and len(raw) >= 2 and isinstance(raw[0], dict):
                rows_list = raw
                table_label = "Results"
            elif (
                isinstance(raw, dict)
                and isinstance(raw.get("data"), list)
                and len(raw["data"]) >= 2
                and isinstance(raw["data"][0], dict)
                and "group_by" not in raw
                and "period" not in raw["data"][0]
            ):
                rows_list = raw["data"]
                table_label = str(raw.get("table") or "Items")

            if rows_list:
                br = self._breakdown_chart_from_rows(ct, rows_list, table_label)
                if br:
                    new_charts.append(br)

        if new_charts:
            agent_response.charts = self._normalize_table_charts(new_charts)
            logger.info(
                "Supplemented %d chart(s) from structured data (LLM omitted charts)",
                len(agent_response.charts or []),
            )
        return agent_response

    @staticmethod
    def _breakdown_chart_from_rows(
        chart_tools: Any,
        rows: List[Dict[str, Any]],
        table_label: str,
    ) -> Optional[Dict[str, Any]]:
        """Build one bar/doughnut chart by counting a categorical column in raw rows."""
        if not rows or not isinstance(rows[0], dict):
            return None

        # Order matters: after filtering by one person, submitted_by is often a single value —
        # skip to status/priority by trying columns until we get multiple buckets.
        preferred = (
            "review_status",
            "status",
            "priority",
            "discipline",
            "submitted_by",
            "assignee",
            "assigned_to",
            "manager",
            "submittal_type",
        )

        def bucket_counts(col: str) -> List[tuple]:
            ctr = Counter(
                str(r.get(col) if r.get(col) is not None else "")
                for r in rows
                if isinstance(r, dict)
            )
            non_empty = [(k, v) for k, v in ctr.most_common(30) if k != ""]
            if len(non_empty) >= 2:
                return non_empty
            if len(non_empty) < 2 and "" in ctr:
                return [(k, v) for k, v in ctr.most_common(30) if k != ""]
            return non_empty

        for col in preferred:
            if col not in rows[0]:
                continue
            filtered = bucket_counts(col)
            if len(filtered) >= 2:
                chart_rows = [{col: k, "count": v} for k, v in filtered]
                title = f"{table_label} by {col}"
                return chart_tools.auto_chart(chart_rows, col, "count", title)

        # Single-bucket dimensions (e.g. one status) — still show one slice / bar
        for col in preferred:
            if col not in rows[0]:
                continue
            filtered = bucket_counts(col)
            if len(filtered) >= 1:
                chart_rows = [{col: k, "count": v} for k, v in filtered]
                title = f"{table_label} by {col}"
                return chart_tools.auto_chart(chart_rows, col, "count", title)

        return None

    def _parse_final_response(self, content: str) -> AgentResponse:
        """Parse the LLM's final response into AgentResponse"""
        try:
            # Try to parse as JSON
            # Handle potential markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            data = json.loads(content)

            metadata = data.get('metadata') or {}
            follow_ups = data.get('follow_up_questions', [])
            if follow_ups:
                metadata['follow_up_questions'] = follow_ups

            return AgentResponse(
                success=True,
                data=data.get('data'),
                message=data.get('insights', data.get('message', '')),
                charts=self._normalize_table_charts(data.get('charts', [])),
                metadata=metadata
            )
        except json.JSONDecodeError:
            # If not valid JSON, return the content as message
            return AgentResponse(
                success=True,
                data=None,
                message=content,
                charts=[]
            )

    def _create_chart_config(
        self,
        chart_type: str,
        title: str,
        labels: List[str],
        data: List[Any],
        dataset_label: str = "Value"
    ) -> Dict:
        """Helper to create chart configuration"""
        return {
            "type": chart_type,
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": dataset_label,
                    "data": data
                }]
            }
        }

    def _create_kpi_config(
        self,
        title: str,
        value: Any,
        unit: str = "",
        trend: str = "stable",
        change: str = ""
    ) -> Dict:
        """Helper to create KPI widget configuration"""
        return {
            "type": "kpi",
            "title": title,
            "data": {
                "value": value,
                "unit": unit,
                "trend": trend,
                "change": change
            }
        }

    def _truncate_result_for_llm(self, result: Any, max_rows: int = 25, max_str_len: int = 500) -> Any:
        """Truncate large results to fit within LLM context limits.

        Preserves metadata (source_file, table, counts) but limits data arrays.
        """
        if isinstance(result, dict):
            truncated = {}
            for key, value in result.items():
                if key == 'data' and isinstance(value, list):
                    # Truncate data arrays
                    if len(value) > max_rows:
                        truncated[key] = value[:max_rows]
                        truncated['_truncated'] = True
                        truncated['_shown_rows'] = max_rows
                        truncated['_total_rows_in_result'] = len(value)
                    else:
                        truncated[key] = value
                elif isinstance(value, str) and len(value) > max_str_len:
                    # Truncate long strings
                    truncated[key] = value[:max_str_len] + "..."
                elif isinstance(value, dict):
                    # Recursively truncate nested dicts
                    truncated[key] = self._truncate_result_for_llm(value, max_rows, max_str_len)
                elif isinstance(value, list) and len(value) > max_rows:
                    # Truncate other lists
                    truncated[key] = value[:max_rows]
                    truncated[f'_{key}_truncated'] = True
                else:
                    truncated[key] = value
            return truncated
        elif isinstance(result, list):
            if len(result) > max_rows:
                return {
                    'data': result[:max_rows],
                    '_truncated': True,
                    '_shown_rows': max_rows,
                    '_total_rows_in_result': len(result)
                }
            return result
        elif isinstance(result, str) and len(result) > max_str_len:
            return result[:max_str_len] + "..."
        return result
