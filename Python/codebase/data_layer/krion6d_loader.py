"""Convert Krion6d API JSON responses into pandas DataFrames.

Produces the **same standardized column names** as CSVDataLoader so that
QueryEngine / agents work identically regardless of the data source.
"""
import asyncio
import json
import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .krion6d_client import Krion6dClient, _extension_from_text, _normalize_ext_fragment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mappings: Krion6d API field names  ->  standardized names
#
# Must produce the SAME output columns as csv_loader.py COLUMN_MAPPINGS so
# that QueryEngine and all agents work without modification.
#
# API responses may use camelCase, snake_case, or MongoDB-style _id – we
# map every known variant.  Unknown fields are kept as-is.
# ---------------------------------------------------------------------------
KRION6D_COLUMN_MAPPINGS: Dict[str, Dict[str, str]] = {
    "projects": {
        "_id": "project_id",
        "id": "project_id",
        "name": "project_name",
        "status": "status",
        "startDate": "start_date",
        "start_date": "start_date",
        "endDate": "end_date",
        "end_date": "end_date",
        "city": "location",
        "location": "location",
        "type": "project_type",
        "projectType": "project_type",
        "value": "budget",
        "budget": "budget",
        "currency": "currency",
    },
    "issues": {
        "_id": "issue_id",
        "id": "issue_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "issue_code",
        "description": "description",
        "type": "issue_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "conditional": "conditional",
        # Legacy field names (kept for compatibility)
        "title": "title",
        "status": "status",
        "assigneeId": "assignee",
        "assignee_id": "assignee",
        "assignee": "assignee",
        "ownerId": "owner",
        "owner_id": "owner",
        "owner": "owner",
        "dueDate": "due_date",
        "due_date": "due_date",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
    },
    "rfis": {
        "_id": "rfi_id",
        "id": "rfi_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "rfi_code",
        "title": "title",
        "description": "description",
        "question": "question",
        "type": "rfi_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "status": "status",
        "priority": "priority",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "dueDate": "due_date",
        "due_date": "due_date",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "createdAt": "created_date",
        "created_at": "created_date",
        "respondedAt": "response_date",
        "responded_at": "response_date",
        "closedAt": "closed_date",
        "closed_at": "closed_date",
        "createdBy": "submitted_by",
        "created_by": "submitted_by",
        "managerId": "assigned_to",
        "manager_id": "assigned_to",
        "costImpact": "cost_impact",
        "cost_impact": "cost_impact",
        "scheduleImpact": "schedule_impact",
        "schedule_impact": "schedule_impact",
        "officialResponse": "response",
        "official_response": "response",
    },
    "tickets": {
        "_id": "ticket_id",
        "id": "ticket_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "ticket_code",
        "description": "description",
        "type": "ticket_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "conditional": "conditional",
        "title": "title",
        "status": "status",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
    },
    "rfas": {
        "_id": "rfa_id",
        "id": "rfa_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "rfa_code",
        "color": "color",
        "comment": "comment",
        "priorityId": "priority_id",
        "priority": "priority",
        "progress": "progress",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "actualStartDate": "actual_start_date",
        "actual_start_date": "actual_start_date",
        "actualEndDate": "actual_end_date",
        "actual_end_date": "actual_end_date",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "title": "title",
        "status": "status",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
    },
    "submittals": {
        "_id": "submittal_id",
        "id": "submittal_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "submittal_code",
        "identifier": "submittal_number",
        "title": "title",
        "description": "description",
        "type": "submittal_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "statusValue": "status",
        "status_value": "status",
        "status": "status",
        "typeValue": "submittal_type",
        "type_value": "submittal_type",
        "priorityValue": "priority",
        "priority_value": "priority",
        "priority": "priority",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "dueDate": "due_date",
        "due_date": "due_date",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
        "manager": "manager",
        "subcontractor": "subcontractor",
        "responseValue": "response",
        "response_value": "response",
        "revision": "revision",
    },
    "schedule": {
        "_id": "task_id",
        "id": "task_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "task_name",
        "code": "task_code",
        "type": "task_type",
        "taskType": "task_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "status": "status",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "actualStartDate": "actual_start",
        "actual_start_date": "actual_start",
        "actualEndDate": "actual_end",
        "actual_end_date": "actual_end",
        "plannedStart": "planned_start",
        "planned_start": "planned_start",
        "plannedFinish": "planned_end",
        "planned_finish": "planned_end",
        "actualStart": "actual_start",
        "actual_start": "actual_start",
        "actualFinish": "actual_end",
        "actual_finish": "actual_end",
        "progress": "percent_complete",
        "completionPercentage": "percent_complete",
        "completion_percentage": "percent_complete",
        "laggedDays": "lagged_days",
        "worklogHours": "worklog_hours",
        "isCriticalPath": "is_critical",
        "is_critical_path": "is_critical",
        "duration": "duration",
        "remainingDuration": "remaining_duration",
        "remaining_duration": "remaining_duration",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
    },
    "transmittals": {
        "_id": "transmittal_id",
        "id": "transmittal_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "transmittal_code",
        "title": "title",
        "description": "description",
        "type": "transmittal_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "status": "status",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "laggedDays": "lagged_days",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
        "dueDate": "due_date",
        "due_date": "due_date",
    },
    "punch_lists": {
        "_id": "punch_list_id",
        "id": "punch_list_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "punch_list_code",
        "title": "title",
        "description": "description",
        "type": "punch_list_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "status": "status",
        "assignee": "assignee",
        "assigneeId": "assignee",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "laggedDays": "lagged_days",
        "createdAt": "created_date",
        "created_at": "created_date",
        "dueDate": "due_date",
        "due_date": "due_date",
    },
    "check_lists": {
        "_id": "check_list_id",
        "id": "check_list_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "code": "check_list_code",
        "title": "title",
        "description": "description",
        "type": "check_list_type",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "status": "status",
        "startDate": "start_date",
        "start_date": "start_date",
        "targetDate": "due_date",
        "target_date": "due_date",
        "laggedDays": "lagged_days",
        "createdAt": "created_date",
        "created_at": "created_date",
    },
    "boms": {
        "_id": "bom_id",
        "id": "bom_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "title": "title",
        "description": "description",
        "code": "bom_code",
        "status": "status",
        "nameForApproval": "status",
        "reviewStepName": "review_step",
        "reviewStatus": "review_status",
        "reviewCode": "review_code",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
        "estimatedPrice": "estimated_price",
        "estimated_price": "estimated_price",
        "estimatedQuantity": "estimated_quantity",
        "estimated_quantity": "estimated_quantity",
        "actualPrice": "actual_price",
        "actual_price": "actual_price",
        "actualQuantity": "actual_quantity",
        "actual_quantity": "actual_quantity",
        "orderedPrice": "ordered_price",
        "ordered_price": "ordered_price",
        "orderedQuantity": "ordered_quantity",
        "ordered_quantity": "ordered_quantity",
        "quotedPrice": "quoted_price",
        "quoted_price": "quoted_price",
    },
    "meetings": {
        "_id": "meeting_id",
        "id": "meeting_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "title": "title",
        "description": "description",
        "status": "status",
        "meetingDate": "meeting_date",
        "meeting_date": "meeting_date",
        "createdAt": "created_date",
        "created_at": "created_date",
        "updatedAt": "updated_date",
        "updated_at": "updated_date",
    },
    "documents": {
        "_id": "document_id",
        "id": "document_id",
        "projectId": "project_id",
        "project_id": "project_id",
        "name": "title",
        "fileName": "title",
        "filename": "title",
        "title": "title",
        "code": "document_code",
        "version": "version",
        "revision": "revision",
        "lastModified": "updated_date",
        "lastModifiedBy": "updated_by",
        "type": "document_type",
        "folderID": "folder",
        "folderId": "folder",
        "projectName": "project_name",
        "size": "size_mb",
        "workflowName": "review_workflow",
        "currentStepName": "current_step",
        "documentType": "discipline_or_type",
        "discipline": "discipline",
        "checkOutBy": "checked_out_by",
        "url": "file_url",
        "path": "file_path",
        "extension": "file_extension",
        "file_extension": "file_extension",
    },
}


class Krion6dDataLoader:
    """Fetch data from Krion6d API and expose it as pandas DataFrames.

    After calling one of the ``load_*`` methods the resulting DataFrames are
    available in ``self.dataframes`` – the same interface used by CSVDataLoader
    so that QueryEngine can consume them unchanged.
    """

    # Entity type to review API entity param mapping
    ENTITY_WORKFLOW_MAP = {
        "issues": "issue_ticket",
        "rfis": "rfi",
        "rfas": "rfa",
        "submittals": "transmittal_submittal",
        "transmittals": "transmittal_submittal",
        "tickets": "issue_ticket",
        "schedule": "review",
        "meetings": "process",
        "documents": "document",
    }

    def __init__(self, client: Krion6dClient):
        self.client = client
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.source_files: Dict[str, str] = {}
        self.load_errors: List[str] = []
        self.workflow_statuses: Dict[str, List[str]] = {}  # entity -> list of workflow step names

    # ------------------------------------------------------------------
    # Public loaders
    # ------------------------------------------------------------------
    async def load_projects(self) -> pd.DataFrame:
        """Fetch project list and return as DataFrame."""
        raw = await self.client.list_projects()
        df = self._to_dataframe(raw, "projects")
        self.dataframes["projects"] = df
        self.source_files["projects"] = "Krion6d API: projects"
        return df

    async def load_dashboard_summary(
        self,
        project_ids: Optional[List[int]] = None,
        time_filter: str = "all"
    ) -> Dict[str, Any]:
        """Fetch dashboard summary (cross-project status counts).
        Returns structured summary data ready for the LLM."""
        raw = await self.client.get_dashboard(project_ids=project_ids, time_filter=time_filter)
        if not isinstance(raw, dict):
            return {}

        summary: Dict[str, Any] = {}

        # Parse entity status counts
        for entity in ("issue", "rfi", "rfa", "task", "ticket", "transmittal", "submittal"):
            entity_data = raw.get(entity, [])
            if not entity_data or len(entity_data) < 2:
                continue

            pending_info = entity_data[0]  # ["Pending rfi", 14]
            status_breakdown = entity_data[1]  # [["Open", 14], ["Approved", 1], ...]

            pending_count = pending_info[1] if isinstance(pending_info, list) and len(pending_info) > 1 else 0
            statuses = {}
            if isinstance(status_breakdown, list):
                for item in status_breakdown:
                    if isinstance(item, list) and len(item) == 2:
                        statuses[item[0]] = item[1]

            summary[entity] = {
                "pending": pending_count,
                "statuses": statuses
            }

        # Parse project list with counts
        project_list = raw.get("userProjectLst", [])
        if project_list:
            projects = []
            for p in project_list:
                projects.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "status": p.get("workflowStatus"),
                    "issue_count": p.get("issue_count", 0),
                    "rfi_count": p.get("rfi_count", 0),
                    "submittal_count": p.get("submittal_count", 0),
                    "transmittal_count": p.get("transmittal_count", 0),
                    "task_count": p.get("task_count", 0),
                })
            summary["projects"] = projects

        # Also create a DataFrame for the dashboard data
        dashboard_rows = []
        for entity, data in summary.items():
            if entity == "projects":
                continue
            for status_name, count in data.get("statuses", {}).items():
                dashboard_rows.append({
                    "entity": entity,
                    "status": status_name,
                    "count": count,
                    "pending": data.get("pending", 0)
                })
        if dashboard_rows:
            self.dataframes["dashboard_summary"] = pd.DataFrame(dashboard_rows)
            self.source_files["dashboard_summary"] = "Krion6d API: dashboard"

        if project_list:
            self.dataframes["project_summary"] = pd.DataFrame(summary.get("projects", []))
            self.source_files["project_summary"] = "Krion6d API: dashboard projects"

        logger.info(f"Dashboard summary loaded: {list(summary.keys())}")
        return summary

    async def load_workflow_statuses(self, project_id: str) -> Dict[str, Any]:
        """Extract actual status and review_step values from loaded data.
        Returns a dict of entity_name -> {statuses: [...], review_steps: [...], workflows: [...]}."""

        # Fetch workflow configurations from API
        for entity_name, api_entity in self.ENTITY_WORKFLOW_MAP.items():
            try:
                workflows = await self.client.list_workflows(project_id, api_entity)
                if workflows:
                    workflow_names = [wf.get("name", "") for wf in workflows if wf.get("name")]
                    if workflow_names:
                        self.workflow_statuses.setdefault(entity_name, {})
                        self.workflow_statuses[entity_name]["workflows"] = workflow_names
                        logger.info(f"Workflows for {entity_name}: {workflow_names}")
            except Exception as e:
                logger.warning(f"Failed to fetch workflows for {entity_name}: {e}")

        # Extract actual distinct values from loaded data
        for entity_name in self.ENTITY_WORKFLOW_MAP:
            if entity_name in self.dataframes:
                df = self.dataframes[entity_name]
                info = self.workflow_statuses.setdefault(entity_name, {})

                if "status" in df.columns:
                    statuses = [str(s) for s in df["status"].dropna().unique().tolist()]
                    if statuses:
                        info["statuses"] = statuses
                        logger.info(f"Actual statuses for {entity_name}: {statuses}")

                if "review_step" in df.columns:
                    steps = [str(s) for s in df["review_step"].dropna().unique().tolist()]
                    if steps:
                        info["review_steps"] = steps
                        logger.info(f"Actual review steps for {entity_name}: {steps}")

                if "review_status" in df.columns:
                    review_statuses = [str(s) for s in df["review_status"].dropna().unique().tolist()]
                    if review_statuses:
                        info["review_statuses"] = review_statuses

        return self.workflow_statuses

    def _get_fetcher_map(self, project_id: str) -> Dict[str, Any]:
        """Return entity_name → coroutine-factory mapping for a given project."""
        return {
            "issues": lambda: self.client.list_issues(project_id),
            "rfis": lambda: self.client.list_rfis(project_id),
            "rfas": lambda: self.client.list_rfas(project_id),
            "schedule": lambda: self.client.list_tasks(project_id),
            "submittals": lambda: self.client.list_submittals(project_id),
            "transmittals": lambda: self.client.list_transmittals(project_id),
            "tickets": lambda: self.client.list_tickets(project_id),
            "punch_lists": lambda: self.client.list_punch_lists(project_id),
            "check_lists": lambda: self.client.list_check_lists(project_id),
            "meetings": lambda: self.client.list_meetings(project_id),
            "boms": lambda: self.client.list_boms(project_id),
            "documents": lambda: self.client.list_documents(project_id),
        }

    def _filter_fetchers(self, fetcher_map: Dict, entities: Optional[List[str]]) -> Dict:
        """Filter fetcher map to only requested entities."""
        if entities:
            return {k: v for k, v in fetcher_map.items() if k in entities}
        return fetcher_map

    @staticmethod
    def _safe_json_payload(value: Any) -> Any:
        """Parse JSON string payloads used in attachment activity logs."""
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            try:
                return json.loads(s)
            except Exception:
                return None
        return value

    @staticmethod
    def _iter_attachment_items(payload: Any) -> List[Dict[str, Any]]:
        """Normalize payload into list-of-dict attachment items."""
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("attachments"), list):
                return [x for x in payload["attachments"] if isinstance(x, dict)]
            return [payload]
        return []

    @staticmethod
    def _entity_id_values(df: pd.DataFrame, primary_col: str) -> List[Any]:
        """Extract unique IDs from normalized and raw ID column variants."""
        ids: List[Any] = []
        for col in (primary_col, "id"):
            if col in df.columns:
                ids.extend([x for x in df[col].dropna().tolist() if str(x).strip()])
        # Preserve order while removing duplicates
        out: List[Any] = []
        seen = set()
        for v in ids:
            key = str(v)
            if key in seen:
                continue
            seen.add(key)
            out.append(v)
        return out

    async def _build_workflow_attachments(self, project_id: str) -> pd.DataFrame:
        """
        Build normalized attachment rows from transmittal/submittal attachment activity endpoints.
        """
        rows: List[Dict[str, Any]] = []

        async def _collect_for_entity(entity_type: str, entity_id: Any) -> None:
            if entity_type == "transmittal":
                events = await self.client.list_transmittal_attachments(project_id, entity_id)
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    event_type = str(event.get("type", ""))
                    if "document" not in event_type.lower() and "attach" not in event_type.lower():
                        continue

                    event_entity_id = event.get("entityID") or event.get("entityId") or entity_id
                    payloads: List[Dict[str, Any]] = []
                    for field in ("to", "metaData"):
                        parsed = self._safe_json_payload(event.get(field))
                        payloads.extend(self._iter_attachment_items(parsed))
                    if not payloads:
                        continue

                    for p in payloads:
                        if not isinstance(p, dict):
                            continue
                        document_name = p.get("name") or p.get("title")
                        file_url = p.get("url") or p.get("path") or p.get("link")
                        file_extension = (
                            _normalize_ext_fragment(str(p.get("extension")))
                            if p.get("extension")
                            else _extension_from_text(str(document_name or file_url or ""))
                        ) or "unknown"
                        rows.append({
                            "project_id": p.get("projectID") or p.get("projectId") or project_id,
                            "entity_type": entity_type,
                            "entity_id": event_entity_id,
                            "document_id": p.get("documentID") or p.get("documentId") or p.get("documentHistoryID"),
                            "document_name": document_name,
                            "file_extension": file_extension,
                            "file_url": file_url,
                            "version": p.get("version"),
                            "revision": p.get("revision"),
                            "action": p.get("action"),
                            "source_event_type": event_type,
                            "created_at": event.get("createdAt"),
                            "created_by": event.get("createdBy"),
                        })
                return

            # Submittals: attachments come from GET /project/{id}/submittal/{submittalId}
            detail = await self.client.get_submittal(project_id, entity_id)
            if not isinstance(detail, dict):
                return
            for att in self._iter_attachment_items(detail.get("attachments")):
                document_name = att.get("name") or att.get("title")
                file_url = att.get("url") or att.get("path") or att.get("link")
                file_extension = (
                    _normalize_ext_fragment(str(att.get("extension")))
                    if att.get("extension")
                    else _extension_from_text(str(document_name or file_url or ""))
                ) or "unknown"
                rows.append({
                    "project_id": att.get("projectID") or att.get("projectId") or project_id,
                    "entity_type": "submittal",
                    "entity_id": detail.get("id") or detail.get("submittalID") or entity_id,
                    "document_id": att.get("documentID") or att.get("documentId") or att.get("documentHistoryId"),
                    "document_name": document_name,
                    "file_extension": file_extension,
                    "file_url": file_url,
                    "version": att.get("version") or att.get("currentVersion"),
                    "revision": att.get("revision") or att.get("currentRevision"),
                    "action": "added",
                    "source_event_type": "submittal_detail_attachments",
                    "created_at": detail.get("createdAt"),
                    "created_by": detail.get("createdBy"),
                })

        if "transmittals" in self.dataframes and not self.dataframes["transmittals"].empty:
            for tid in self._entity_id_values(self.dataframes["transmittals"], "transmittal_id"):
                await _collect_for_entity("transmittal", tid)

        if "submittals" in self.dataframes and not self.dataframes["submittals"].empty:
            for sid in self._entity_id_values(self.dataframes["submittals"], "submittal_id"):
                await _collect_for_entity("submittal", sid)

        if not rows:
            return pd.DataFrame()
        return self._to_dataframe(rows, "workflow_attachments")

    async def load_project_data(
        self, project_id: str, entities: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """Fetch entity types for a single project (concurrently)."""
        fetchers = self._filter_fetchers(self._get_fetcher_map(project_id), entities)
        logger.info(f"Loading entity data for project {project_id}: {list(fetchers.keys())}")

        results = await asyncio.gather(
            *(fetch() for fetch in fetchers.values()), return_exceptions=True
        )

        loaded = []
        for table_name, result in zip(fetchers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Krion6d API error fetching {table_name} for project {project_id}: {result}")
                self.load_errors.append(f"{table_name}: {result}")
                continue
            if not result:
                logger.info(f"Krion6d API: {table_name} returned empty for project {project_id}")
                self.dataframes[table_name] = self._to_dataframe([], table_name)
                self.source_files[table_name] = f"Krion6d API: {table_name}/{project_id}"
                loaded.append(f"{table_name}(0)")
                continue
            df = self._to_dataframe(result, table_name)
            self.dataframes[table_name] = df
            self.source_files[table_name] = f"Krion6d API: {table_name}/{project_id}"
            loaded.append(f"{table_name}({len(df)})")

        needs_workflow_attachments = (
            entities is None
            or any(e in entities for e in ("submittals", "transmittals", "documents"))
        )
        if needs_workflow_attachments:
            wa_df = await self._build_workflow_attachments(project_id)
            self.dataframes["workflow_attachments"] = wa_df
            self.source_files["workflow_attachments"] = (
                f"Krion6d API: workflow_attachments/{project_id}"
            )
            loaded.append(f"workflow_attachments({len(wa_df)})")

        logger.info(f"Krion6d loaded for project {project_id}: {', '.join(loaded) or 'nothing'}")
        if self.load_errors:
            logger.warning(f"Krion6d load errors: {self.load_errors}")

        return self.dataframes

    async def load_all_projects_data(
        self, project_ids: List[str], max_projects: Optional[int] = None,
        entities: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """Fetch entity data across multiple projects and concatenate."""
        ids = project_ids[:max_projects] if isinstance(max_projects, int) and max_projects > 0 else list(project_ids)
        # Use first project to get entity keys, then filter
        entity_keys = list(self._filter_fetchers(self._get_fetcher_map("_"), entities).keys())
        needs_workflow_attachments = (
            entities is None
            or any(e in entities for e in ("submittals", "transmittals", "documents"))
        )
        if needs_workflow_attachments and "workflow_attachments" not in entity_keys:
            entity_keys.append("workflow_attachments")
        logger.info(f"Loading entity data for {len(ids)} projects: {ids}, entities: {entity_keys}")
        all_frames: Dict[str, List[pd.DataFrame]] = {}

        for pid in ids:
            fetchers = self._filter_fetchers(self._get_fetcher_map(pid), entities)

            results = await asyncio.gather(
                *(fetch() for fetch in fetchers.values()), return_exceptions=True
            )

            for table_name, result in zip(fetchers.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Krion6d API error: {table_name}/{pid}: {result}")
                    self.load_errors.append(f"{table_name}/{pid}: {result}")
                    continue
                if not result:
                    continue
                df = self._to_dataframe(result, table_name)
                if len(df) > 0:
                    all_frames.setdefault(table_name, []).append(df)

            if needs_workflow_attachments:
                wa_df = await self._build_workflow_attachments(pid)
                if len(wa_df) > 0:
                    all_frames.setdefault("workflow_attachments", []).append(wa_df)

        for table_name, frames in all_frames.items():
            merged = pd.concat(frames, ignore_index=True)
            self.dataframes[table_name] = merged
            self.source_files[table_name] = f"Krion6d API: {table_name} (all projects)"

        # Create empty DataFrames for fetched entity types so agents see them
        for entity in entity_keys:
            if entity not in self.dataframes:
                self.dataframes[entity] = self._to_dataframe([], entity)
                self.source_files[entity] = f"Krion6d API: {entity} (empty)"

        loaded_summary = {k: len(v) for k, v in self.dataframes.items()}
        logger.info(f"Krion6d all-projects load summary: {loaded_summary}")
        if self.load_errors:
            logger.warning(f"Krion6d load errors ({len(self.load_errors)}): {self.load_errors[:5]}")

        return self.dataframes

    # ------------------------------------------------------------------
    # Internal helpers (mirror CSVDataLoader patterns)
    # ------------------------------------------------------------------
    def _to_dataframe(self, records: List[Dict], table_name: str) -> pd.DataFrame:
        """Convert list of dicts -> DataFrame with standardized columns."""
        if not records:
            return pd.DataFrame()

        # Flatten nested objects before creating DataFrame
        records = [self._flatten_record(r) for r in records]

        df = pd.DataFrame(records)
        df = self._apply_column_mapping(df, table_name)
        df = self._convert_dates(df)
        df = self._apply_derived_columns(df, table_name)
        if table_name == "documents":
            df = self._finalize_documents_dataframe(df)
        return df

    @staticmethod
    def _apply_derived_columns(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Add derived business columns for specific entities."""
        if table_name == "rfas":
            df = Krion6dDataLoader._add_rfa_work_hours(df)
        return df

    @staticmethod
    def _add_rfa_work_hours(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add RFA work_hours derived from date span excluding weekend days.

        Formula (inclusive calendar days from start_date through due_date):
            work_hours = (working_days_in_span) * 8
        where working_days_in_span = total_days - weekend_days (Sat/Sun in span).
        """
        if "start_date" not in df.columns or "due_date" not in df.columns:
            return df

        def _compute_hours(start_val: Any, due_val: Any) -> Optional[float]:
            if pd.isna(start_val) or pd.isna(due_val):
                return None
            if not isinstance(start_val, (pd.Timestamp, datetime)) or not isinstance(due_val, (pd.Timestamp, datetime)):
                return None

            start_date = pd.Timestamp(start_val).normalize()
            due_date = pd.Timestamp(due_val).normalize()
            if due_date < start_date:
                return None

            total_days = (due_date - start_date).days + 1
            if total_days <= 0:
                return 0.0

            day_range = pd.date_range(start=start_date, periods=total_days, freq="D")
            weekend_days = int((day_range.weekday >= 5).sum())
            working_days = max(total_days - weekend_days, 0)
            return float(working_days * 8)

        df = df.copy()
        df["work_hours"] = [
            _compute_hours(start_val, due_val)
            for start_val, due_val in zip(df["start_date"], df["due_date"])
        ]
        return df

    @staticmethod
    def _finalize_documents_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize file_extension (lowercase + dot; infer from title/url/path). Heuristic size_mb from bytes."""

        def infer_ext(row: pd.Series) -> str:
            if "file_extension" in row.index:
                raw = row["file_extension"]
                if pd.notna(raw) and str(raw).strip():
                    ne = _normalize_ext_fragment(str(raw))
                    if ne:
                        return ne
            for col in ("title", "file_url", "file_path"):
                if col in row.index:
                    val = row[col]
                    if pd.notna(val):
                        e = _extension_from_text(str(val))
                        if e:
                            return e
            return "unknown"

        df = df.copy()
        if "file_extension" not in df.columns:
            df["file_extension"] = None
        df["file_extension"] = df.apply(infer_ext, axis=1)

        if "size_mb" in df.columns:

            def to_mb(v: Any) -> Any:
                if pd.isna(v):
                    return v
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    return v
                if x > 1_000_000:
                    return round(x / (1024 * 1024), 6)
                return x

            df["size_mb"] = df["size_mb"].map(to_mb)

        return df

    @staticmethod
    def _flatten_record(record: Dict) -> Dict:
        """Flatten nested objects like createdBy: {firstName, lastName} into strings."""
        flat = {}
        for key, value in record.items():
            if isinstance(value, dict):
                # e.g. createdBy: {firstName: "John", lastName: "Doe"} → "John Doe"
                if "firstName" in value or "lastName" in value:
                    flat[key] = f"{value.get('firstName', '')} {value.get('lastName', '')}".strip()
                elif "name" in value:
                    flat[key] = value["name"]
                else:
                    flat[key] = str(value)
            else:
                flat[key] = value
        return flat

    @staticmethod
    def _apply_column_mapping(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Rename API fields to standardized column names."""
        mapping = KRION6D_COLUMN_MAPPINGS.get(table_name)
        if mapping is None:
            return df

        rename_dict = {old: new for old, new in mapping.items() if old in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)
            logger.debug(f"Renamed {len(rename_dict)} columns in {table_name}")
            if df.columns.duplicated().any():
                deduped: Dict[str, pd.Series] = {}
                for col in df.columns:
                    col_data = df.loc[:, col]
                    if isinstance(col_data, pd.DataFrame):
                        merged = col_data.bfill(axis=1).iloc[:, 0]
                    else:
                        merged = col_data
                    if col in deduped:
                        deduped[col] = deduped[col].combine_first(merged)
                    else:
                        deduped[col] = merged
                df = pd.DataFrame(deduped)
        return df

    @staticmethod
    def _convert_dates(df: pd.DataFrame) -> pd.DataFrame:
        """Auto-convert date columns (same logic as CSVDataLoader)."""
        date_keywords = [
            "date", "start", "end", "created", "updated",
            "due", "closed", "responded", "opened", "finish", "_at",
        ]

        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
        return df
