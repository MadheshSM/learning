"""ERP Agent for project planning, bill of materials, and costing analysis"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentResponse
from .tools.data_tools import DataTools
from .tools.aggregation_tools import AggregationTools
from .tools.chart_tools import ChartTools


class ERPAgent(BaseAgent):
    """Agent for ERP data analysis — project plan, BOM, and costing.

    Data tables available:
      - project_plan: Tasks with WBSCode, dates, durations, responsibility
      - bom: Bill of Materials with WBSCode, ItemCode, quantities, unit rates
      - erp_costing: Procurement/material costs with ItemCode, GST, totals
      - plan_bom: Pre-joined project_plan + bom (via normalized WBSCode)
    """

    def __init__(self, llm_provider, query_engine):
        self.data_tools = DataTools(query_engine)
        self.agg_tools = AggregationTools(query_engine)
        self.chart_tools = ChartTools(query_engine)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "erp"

    @property
    def description(self) -> str:
        return """Analyzes ERP data including project plans (tasks, schedules, WBS),
        bill of materials (BOM with quantities and unit rates), and ERP costing
        (material costs, GST, total amounts). Can answer questions about upcoming
        task costs by joining project plan dates with BOM items and their costs.
        Handles queries about weekly/monthly cost forecasts, material requirements,
        cost breakdowns by WBS, and budget analysis."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "erp_cost_forecast",
            "project_plan_analysis",
            "bom_analysis",
            "material_cost_breakdown",
            "weekly_cost_estimation",
            "wbs_cost_analysis",
            "task_schedule_analysis",
            "cost_by_responsibility",
        ]

    def _build_system_prompt(self) -> str:
        """Override to provide ERP-specific system prompt."""
        available_tables = self.query_engine.get_tables()

        # Build schema hints for each ERP table
        schema_hints = []
        for tbl in ["project_plan", "bom", "erp_costing", "plan_bom"]:
            if tbl in self.query_engine.dfs:
                cols = list(self.query_engine.dfs[tbl].columns)
                rows = len(self.query_engine.dfs[tbl])
                schema_hints.append(f"  - {tbl} ({rows} rows): {cols}")

        schema_text = "\n".join(schema_hints) if schema_hints else "  (no ERP tables loaded)"

        return f"""You are the ERP agent in a construction project analytics system.

Your role: {self.description}

Available data tables: {', '.join(available_tables)}

ERP Table Schemas:
{schema_text}

TABLE RELATIONSHIPS:
- project_plan and bom are linked via WBSCodeNorm (normalized WBS code).
  project_plan.WBSCode is a float like 1.1; bom.WBSCode is a string like "WBS-1.1".
  Both have a WBSCodeNorm column (string "1.1") for joining.
- plan_bom is the pre-joined table of project_plan + bom (inner join on WBSCodeNorm).
  It contains task dates AND BOM item details in one table.
- bom has ItemCode (e.g. "BOQ-EXC-001") — these are Bill of Quantities work items.
- erp_costing has ItemCode (e.g. "MAT-CEM-OPC43") — these are material procurement items.
  The ItemCodes between bom and erp_costing use DIFFERENT coding systems.
  To estimate costs, use AmountINR from bom for BOQ-level costs, or
  TotalAmountINR from erp_costing for material-level costs.

COST ESTIMATION APPROACH:
When asked "what will be the cost for the upcoming week/period":
1. Query project_plan to find tasks whose StartDate/FinishDate overlap the requested period.
2. Get those tasks' WBSCodeNorm values.
3. Query plan_bom (or join project_plan + bom) to find all BOM items for those tasks.
4. Sum up AmountINR from bom for the matched items — this gives the BOQ cost.
5. Optionally reference erp_costing for material-level cost details.
6. Present a breakdown by task/WBS and total cost.

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}
Use this to calculate "upcoming week", "next month", etc.

Instructions:
1. Analyze the user's query to understand what data or insights they need
2. Use your tools to query and analyze the data
3. Provide clear, actionable insights based on the data
4. When appropriate, suggest visualizations (charts) to display the data

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

For TABLE widgets:
{{
    "type": "table",
    "title": "Table title",
    "data": {{
        "headers": ["col1", "col2", ...],
        "rows": [["val1", "val2", ...], ...]
    }}
}}

For KPI widgets:
{{
    "type": "kpi",
    "title": "Metric Name",
    "data": {{
        "value": 42,
        "unit": "INR",
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

FOLLOW-UP QUESTIONS:
- Always include 2-3 relevant follow-up questions
- Examples: "Show cost breakdown by WBS", "What materials are needed next month?",
  "Which tasks are on the critical path?", "Compare planned vs actual costs"
"""

    def _register_tools(self) -> List[Dict]:
        return [
            {
                "name": "query_project_plan",
                "description": "Query project plan tasks. Can filter by date range, responsibility, WBSCode. Returns tasks with StartDate, FinishDate, DurationDays, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Filter tasks starting on or after this date (YYYY-MM-DD)"},
                        "end_date": {"type": "string", "description": "Filter tasks ending on or before this date (YYYY-MM-DD)"},
                        "responsibility": {"type": "string", "description": "Filter by responsibility (e.g. 'PM', 'Site Engineer')"},
                        "wbs_code": {"type": "string", "description": "Filter by WBSCodeNorm (e.g. '1.1')"},
                        "overlapping_period": {"type": "boolean", "description": "If true, find tasks that OVERLAP with start_date-end_date range (not just start within)", "default": True},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100},
                    },
                },
            },
            {
                "name": "query_bom",
                "description": "Query Bill of Materials. Can filter by WBSCode, WBSName, ItemCode. Returns items with quantities, unit rates, amounts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wbs_code_norm": {"type": "string", "description": "Filter by normalized WBSCode (e.g. '1.1')"},
                        "wbs_codes": {"type": "array", "items": {"type": "string"}, "description": "Filter by multiple WBSCodeNorm values"},
                        "wbs_name": {"type": "string", "description": "Filter by WBSName (e.g. 'Substructure')"},
                        "item_code": {"type": "string", "description": "Filter by ItemCode"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100},
                    },
                },
            },
            {
                "name": "query_erp_costing",
                "description": "Query ERP costing/procurement data. Returns material costs with GST, rates, and total amounts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_code": {"type": "string", "description": "Filter by ItemCode (e.g. 'MAT-CEM-OPC43')"},
                        "cost_center": {"type": "string", "description": "Filter by CostCenter"},
                        "min_amount": {"type": "number", "description": "Filter items with TotalAmountINR >= this value"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100},
                    },
                },
            },
            {
                "name": "query_plan_bom",
                "description": "Query the pre-joined project_plan + bom table. Contains task dates AND BOM items in one view. Best for date-based cost queries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Filter by task StartDate >= (YYYY-MM-DD)"},
                        "end_date": {"type": "string", "description": "Filter by task FinishDate <= (YYYY-MM-DD)"},
                        "overlapping_period": {"type": "boolean", "description": "Find tasks overlapping the date range", "default": True},
                        "wbs_name": {"type": "string", "description": "Filter by WBSName"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 100},
                    },
                },
            },
            {
                "name": "get_cost_for_period",
                "description": "Calculate total estimated cost for tasks within a date range. Joins project plan with BOM to find all items needed and sums AmountINR.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Period start date (YYYY-MM-DD)"},
                        "end_date": {"type": "string", "description": "Period end date (YYYY-MM-DD)"},
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "name": "get_cost_breakdown_by_wbs",
                "description": "Get cost breakdown grouped by WBS/task category from the BOM.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wbs_name": {"type": "string", "description": "Optional: filter to specific WBS category"},
                    },
                },
            },
            {
                "name": "get_material_summary",
                "description": "Get summary of all materials from erp_costing with their costs, GST, and totals.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sort_by": {"type": "string", "description": "Sort by column (default: TotalAmountINR)", "default": "TotalAmountINR"},
                    },
                },
            },
            {
                "name": "get_all_erp_tables",
                "description": "List all available ERP tables with row counts and column names. Use this first to understand what data is available.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a specific ERP tool."""

        if tool_name == "get_all_erp_tables":
            tables = {}
            for tbl in ["project_plan", "bom", "erp_costing", "plan_bom"]:
                if tbl in self.query_engine.dfs:
                    df = self.query_engine.dfs[tbl]
                    tables[tbl] = {
                        "row_count": len(df),
                        "columns": list(df.columns),
                        "sample": df.head(3).to_dict("records"),
                    }
            if not tables:
                return {"error": "No ERP tables loaded. Please upload ERP Excel files first."}
            return tables

        elif tool_name == "query_project_plan":
            if "project_plan" not in self.query_engine.dfs:
                return {"error": "project_plan table not loaded"}

            df = self.query_engine.dfs["project_plan"].copy()
            start_date = tool_input.get("start_date")
            end_date = tool_input.get("end_date")
            overlapping = tool_input.get("overlapping_period", True)

            if start_date and end_date and overlapping:
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                # Tasks that overlap: task starts before period ends AND task finishes after period starts
                df = df[
                    (df["StartDate"] <= ed) & (df["FinishDate"] >= sd)
                ]
            else:
                if start_date:
                    df = df[df["StartDate"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["FinishDate"] <= pd.to_datetime(end_date)]

            if tool_input.get("responsibility"):
                df = df[df["Responsibility"].str.contains(tool_input["responsibility"], case=False, na=False)]
            if tool_input.get("wbs_code"):
                df = df[df["WBSCodeNorm"] == tool_input["wbs_code"]]

            limit = tool_input.get("limit", 100)
            result = df.head(limit).to_dict("records")
            return {"data": result, "total_rows": len(df), "returned_rows": len(result)}

        elif tool_name == "query_bom":
            if "bom" not in self.query_engine.dfs:
                return {"error": "bom table not loaded"}

            df = self.query_engine.dfs["bom"].copy()

            if tool_input.get("wbs_code_norm"):
                df = df[df["WBSCodeNorm"] == tool_input["wbs_code_norm"]]
            if tool_input.get("wbs_codes"):
                df = df[df["WBSCodeNorm"].isin(tool_input["wbs_codes"])]
            if tool_input.get("wbs_name"):
                df = df[df["WBSName"].str.contains(tool_input["wbs_name"], case=False, na=False)]
            if tool_input.get("item_code"):
                df = df[df["ItemCode"].str.contains(tool_input["item_code"], case=False, na=False)]

            limit = tool_input.get("limit", 100)
            result = df.head(limit).to_dict("records")
            return {"data": result, "total_rows": len(df), "returned_rows": len(result)}

        elif tool_name == "query_erp_costing":
            if "erp_costing" not in self.query_engine.dfs:
                return {"error": "erp_costing table not loaded"}

            df = self.query_engine.dfs["erp_costing"].copy()

            if tool_input.get("item_code"):
                df = df[df["ItemCode"].str.contains(tool_input["item_code"], case=False, na=False)]
            if tool_input.get("cost_center"):
                df = df[df["CostCenter"].str.contains(tool_input["cost_center"], case=False, na=False)]
            if tool_input.get("min_amount"):
                df = df[df["TotalAmountINR"] >= tool_input["min_amount"]]

            limit = tool_input.get("limit", 100)
            result = df.head(limit).to_dict("records")
            return {"data": result, "total_rows": len(df), "returned_rows": len(result)}

        elif tool_name == "query_plan_bom":
            if "plan_bom" not in self.query_engine.dfs:
                return {"error": "plan_bom joined table not available. Ensure both project_plan and bom are loaded."}

            df = self.query_engine.dfs["plan_bom"].copy()
            start_date = tool_input.get("start_date")
            end_date = tool_input.get("end_date")
            overlapping = tool_input.get("overlapping_period", True)

            if start_date and end_date and overlapping:
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                df = df[(df["StartDate"] <= ed) & (df["FinishDate"] >= sd)]
            else:
                if start_date:
                    df = df[df["StartDate"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["FinishDate"] <= pd.to_datetime(end_date)]

            if tool_input.get("wbs_name"):
                df = df[df["WBSName"].str.contains(tool_input["wbs_name"], case=False, na=False)]

            limit = tool_input.get("limit", 100)
            result = df.head(limit).to_dict("records")
            total_amount = float(df["AmountINR"].sum()) if "AmountINR" in df.columns else 0
            return {
                "data": result,
                "total_rows": len(df),
                "returned_rows": len(result),
                "total_amount_inr": total_amount,
            }

        elif tool_name == "get_cost_for_period":
            start_date = tool_input["start_date"]
            end_date = tool_input["end_date"]

            if "plan_bom" not in self.query_engine.dfs:
                # Fallback: try to manually join
                if "project_plan" not in self.query_engine.dfs or "bom" not in self.query_engine.dfs:
                    return {"error": "Need project_plan and bom tables to calculate period costs."}

                plan = self.query_engine.dfs["project_plan"].copy()
                bom = self.query_engine.dfs["bom"].copy()

                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)

                tasks_in_period = plan[(plan["StartDate"] <= ed) & (plan["FinishDate"] >= sd)]
                wbs_codes = tasks_in_period["WBSCodeNorm"].unique().tolist()

                matched_bom = bom[bom["WBSCodeNorm"].isin(wbs_codes)]
                total_cost = float(matched_bom["AmountINR"].sum())

                breakdown = []
                for _, task in tasks_in_period.iterrows():
                    wbs = task["WBSCodeNorm"]
                    task_bom = matched_bom[matched_bom["WBSCodeNorm"] == wbs]
                    task_cost = float(task_bom["AmountINR"].sum())
                    breakdown.append({
                        "task": task.get("TaskName", ""),
                        "wbs_code": wbs,
                        "start_date": str(task.get("StartDate", "")),
                        "finish_date": str(task.get("FinishDate", "")),
                        "bom_items": len(task_bom),
                        "cost_inr": task_cost,
                    })
            else:
                df = self.query_engine.dfs["plan_bom"].copy()
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)

                period_data = df[(df["StartDate"] <= ed) & (df["FinishDate"] >= sd)]
                total_cost = float(period_data["AmountINR"].sum()) if "AmountINR" in period_data.columns else 0

                # Group by task
                breakdown = []
                task_col = "TaskName" if "TaskName" in period_data.columns else "TaskName_plan"
                wbs_col = "WBSCodeNorm"

                for wbs_code in period_data[wbs_col].unique():
                    task_data = period_data[period_data[wbs_col] == wbs_code]
                    task_name = task_data[task_col].iloc[0] if task_col in task_data.columns else wbs_code
                    task_cost = float(task_data["AmountINR"].sum()) if "AmountINR" in task_data.columns else 0
                    start = task_data["StartDate"].iloc[0] if "StartDate" in task_data.columns else ""
                    finish = task_data["FinishDate"].iloc[0] if "FinishDate" in task_data.columns else ""
                    breakdown.append({
                        "task": str(task_name),
                        "wbs_code": wbs_code,
                        "start_date": str(start),
                        "finish_date": str(finish),
                        "bom_items": len(task_data),
                        "cost_inr": task_cost,
                    })

            return {
                "period": {"start": start_date, "end": end_date},
                "total_cost_inr": total_cost,
                "tasks_count": len(breakdown),
                "breakdown": breakdown,
            }

        elif tool_name == "get_cost_breakdown_by_wbs":
            if "bom" not in self.query_engine.dfs:
                return {"error": "bom table not loaded"}

            df = self.query_engine.dfs["bom"].copy()

            if tool_input.get("wbs_name"):
                df = df[df["WBSName"].str.contains(tool_input["wbs_name"], case=False, na=False)]

            grouped = df.groupby("WBSName").agg(
                items=("ItemCode", "count"),
                total_amount=("AmountINR", "sum"),
                total_quantity=("Quantity", "sum"),
            ).reset_index()

            return {
                "data": grouped.to_dict("records"),
                "grand_total_inr": float(df["AmountINR"].sum()),
            }

        elif tool_name == "get_material_summary":
            if "erp_costing" not in self.query_engine.dfs:
                return {"error": "erp_costing table not loaded"}

            df = self.query_engine.dfs["erp_costing"].copy()
            sort_by = tool_input.get("sort_by", "TotalAmountINR")
            if sort_by in df.columns:
                df = df.sort_values(sort_by, ascending=False)

            return {
                "data": df.to_dict("records"),
                "total_basic_amount": float(df["BasicAmountINR"].sum()),
                "total_gst": float(df["GSTAmountINR"].sum()),
                "total_amount": float(df["TotalAmountINR"].sum()),
            }

        return {"error": f"Unknown tool: {tool_name}"}
