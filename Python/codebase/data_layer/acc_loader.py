"""Convert ACC (Autodesk Construction Cloud) API JSON responses into pandas DataFrames.

Produces the same standardized column names as CSVDataLoader so that
QueryEngine / agents work identically regardless of the data source.
"""
import asyncio
import json
import logging
import warnings
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from .acc_client import ACCApiClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mappings
# ---------------------------------------------------------------------------
ACC_COLUMN_MAPPINGS: Dict[str, Dict[str, str]] = {
    "projects": {
        "id":          "project_id",
        "name":        "project_name",
        "status":      "status",
        "startDate":   "start_date",
        "endDate":     "end_date",
        "city":        "location",
        "type":        "project_type",
        "projectType": "project_type",
        "value":       "budget",
        "currency":    "currency",
        "addressLine1":"address",
        "country":     "country",
        "jobNumber":   "job_number",
    },
    "issues": {
        "id":             "issue_id",
        "containerId":    "container_id",
        "displayId":      "display_id",
        "title":          "title",
        "description":    "description",
        "status":         "status",
        "issueTypeId":    "issue_type_id",
        "issueSubtypeId": "issue_subtype_id",
        "assignedTo":     "assignee",
        "assignedToType": "assignee_type",
        "ownerId":        "owner",
        "dueDate":        "due_date",
        "createdAt":      "created_date",
        "updatedAt":      "updated_date",
        "closedAt":       "closed_date",
        "closedBy":       "closed_by",
        "startDate":      "start_date",
        "locationId":     "location",
        "rootCauseId":    "root_cause",
        "linkedDocuments":"linked_documents",
        "published":      "published",
        "priority":       "priority",
    },
    "rfis": {
        "id":               "rfi_id",
        "title":            "title",
        "status":           "status",
        "priority":         "priority",
        "dueDate":          "due_date",
        "createdAt":        "created_date",
        "updatedAt":        "updated_date",
        "closedAt":         "closed_date",
        "createdBy":        "submitted_by",
        "created_by":       "submitted_by",
        "assignedTo":       "assigned_to",
        "assigned_to":      "assigned_to",
        "managerId":        "manager",
        "manager_id":       "manager",
        "costImpact":       "cost_impact",
        "scheduleImpact":   "schedule_impact",
        "question":         "question",
        "answer":           "response",
        "customIdentifier": "rfi_number",
    },
    "submittals": {
        "id":           "submittal_id",
        "title":        "title",
        "description":  "description",
        "status":       "status",
        "type":         "submittal_type",
        "priority":     "priority",
        "dueDate":      "due_date",
        "createdAt":    "created_date",
        "updatedAt":    "updated_date",
        "manager":      "manager",
        "subcontractor":"subcontractor",
        "sentDate":     "sent_date",
        "receivedDate": "received_date",
        "revision":     "revision",
        "specSection":  "spec_section",
        "identifier":   "submittal_number",
    },
    "transmittals": {
        # ACC API returns sentBy as a nested object: {autodeskId, name, email, companyName}
        # We flatten it in _flatten_transmittal_records() before column mapping.
        "id":                 "transmittal_id",
        "sequenceId":         "sequence_id",
        "title":              "title",
        "message":            "message",
        "status":             "status",
        "sentBy_autodeskId":  "created_by_id",
        "sentBy_name":        "created_by",
        "sentBy_email":       "created_by_email",
        "sentBy_companyName": "company_name",
        "documentsCount":     "docs_count",
        "displayRecipients":  "recipients_display",
        "createdAt":          "created_date",
        "updatedAt":          "updated_date",
        "packedStatus":       "packed_status",
    },
    "schedule": {
        "id":                   "task_id",
        "planId":               "plan_id",
        "uniqueId":             "unique_id",
        "activityUniqueId":     "activity_unique_id",
        "parentTaskId":         "parent_task_id",
        "scheduleId":           "schedule_id",
        "scheduleName":         "schedule_name",
        "projectId":            "project_id",
        "type":                 "task_type",
        "subType":              "task_sub_type",
        "status":               "status",
        "priority":             "priority",
        "name":                 "task_name",
        "description":          "description",
        "plannedStart":         "planned_start",
        "actualStart":          "actual_start",
        "start":                "start_date",
        "finish":               "end_date",
        "archivedAt":           "archived_date",
        "lastReferenceAddedAt": "last_reference_date",
        "plannedDuration":      "planned_duration",
        "actualDuration":       "actual_duration",
        "duration":             "duration",
        "completionPercentage": "percent_complete",
        "wbsId":                "wbs_id",
        "wbsFallbackName":      "phase",
        "assignedTo":           "assigned_to",
        "company":              "company",
        "role":                 "role",
        "crewSize":             "crew_size",
        "createdAt":            "created_date",
        "createdBy":            "created_by",
        "updatedAt":            "updated_date",
        "updatedBy":            "updated_by",
        "commitmentsCount":     "commitments_count",
        "commentsCount":        "comments_count",
    },
}

ACC_ENTITY_TABLES = ("issues", "rfis", "submittals", "transmittals", "schedule")

# ---------------------------------------------------------------------------
# Which RAW API fields (before column mapping) contain user IDs per table.
# We resolve these BEFORE _apply_column_mapping runs so the field names
# always match what the ACC API actually sends.
# ---------------------------------------------------------------------------
USER_ID_FIELDS_BY_TABLE: Dict[str, List[str]] = {
    "issues":    ["assignedTo", "ownerId", "closedBy"],
    "rfis":      ["assignedTo", "assigned_to", "managerId", "manager_id",
                  "createdBy", "created_by"],
    "submittals":["manager", "subcontractor"],
    "schedule":  ["assignedTo", "createdBy", "updatedBy"],
}

# ---------------------------------------------------------------------------
# Schedule status normalisation
# ---------------------------------------------------------------------------
ACC_SCHEDULE_STATUS_MAP: Dict[str, str] = {
    "OPEN":        "not_started",
    "NOT_STARTED": "not_started",
    "IN_PROGRESS": "in_progress",
    "IN PROGRESS": "in_progress",
    "INPROGRESS":  "in_progress",
    "COMPLETE":    "completed",
    "COMPLETED":   "completed",
    "DONE":        "completed",
    "CLOSED":      "completed",
    "ON_HOLD":     "on_hold",
    "ON HOLD":     "on_hold",
    "ONHOLD":      "on_hold",
    "CANCELLED":   "cancelled",
    "CANCELED":    "cancelled",
}

# ---------------------------------------------------------------------------
# Schedule load status codes
# ---------------------------------------------------------------------------
SCHEDULE_OK          = "ok"
SCHEDULE_EMPTY       = "empty"
SCHEDULE_NO_SCHEDULE = "no_schedule"
SCHEDULE_PERMISSION  = "permission"
SCHEDULE_NOT_FOUND   = "not_found"
SCHEDULE_ERROR       = "error"


# ===========================================================================
# ACCDataLoader
# ===========================================================================
class ACCDataLoader:
    """Fetch data from ACC API and expose it as pandas DataFrames."""

    def __init__(self, client: ACCApiClient):
        self.client                = client
        self.dataframes:           Dict[str, pd.DataFrame] = {}
        self.source_files:         Dict[str, str]          = {}
        self.load_errors:          List[str]               = []
        self.schedule_load_status: str                     = SCHEDULE_OK
        self.schedule_load_detail: str                     = ""

    # ------------------------------------------------------------------
    # Public loaders
    # ------------------------------------------------------------------
    async def load_projects(self) -> pd.DataFrame:
        raw = await self.client.list_projects()
        df  = self._to_dataframe(raw, "projects")
        self.dataframes["projects"]   = df
        self.source_files["projects"] = "ACC API: projects"
        return df

    async def load_project_data(self, project_id: str) -> Dict[str, pd.DataFrame]:
        """Fetch all entity types for one project concurrently.

        User ID → display name resolution flow
        ───────────────────────────────────────
        1. list_project_members() is called alongside all other fetchers.
        2. _build_user_id_to_name_map() turns the member list into a
           { raw_id: "First Last" } dict, registering every known ID alias
           (autodeskId, userId, oauthUserId, guid …).
        3. _resolve_user_ids_in_records() walks every record for a table and
           replaces raw ID strings / dicts in the USER_ID_FIELDS_BY_TABLE
           fields with the resolved display name BEFORE _to_dataframe() runs.
        4. If resolution fails (403, no account_id, empty members) the raw
           IDs are kept — the load still succeeds, just without names.
        """
        logger.info("ACC: Loading entity data for project %s", project_id)

        fetchers = {
            "project_members": self.client.list_project_members(project_id),
            "issues":          self.client.list_issues(project_id),
            "rfis":            self.client.list_rfis(project_id),
            "submittals":      self.client.list_submittals(project_id),
            "transmittals":    self.client.list_transmittals(project_id),
            "schedule":        self.client.list_project_schedule_activities(project_id),
        }

        results         = await asyncio.gather(*fetchers.values(), return_exceptions=True)
        results_by_name = dict(zip(fetchers.keys(), results))

        # ── Step 1: build user ID → name map ─────────────────────────────
        id_to_name = self._extract_id_to_name(
            results_by_name.get("project_members", []), project_id
        )

        # ── Step 2: process each entity table ────────────────────────────
        loaded = []
        for table_name in ACC_ENTITY_TABLES:
            result = results_by_name.get(table_name)

            # Schedule-specific error tagging + Data Connector fallback
            if table_name == "schedule":
                status, detail, tag = self._classify_schedule_result(result, project_id)
                if status != SCHEDULE_OK:
                    self.schedule_load_status = status
                    self.schedule_load_detail = detail
                    self.load_errors.append(f"schedule: {detail}")
                    self.dataframes["schedule"]   = pd.DataFrame()
                    self.source_files["schedule"] = f"ACC API: schedule/{project_id}"
                    loaded.append(tag)
                    continue

            # Generic error handling
            if isinstance(result, Exception):
                err = f"{table_name}: {result}"
                logger.error("ACC API error fetching %s for project %s: %s",
                             table_name, project_id, result)
                self.load_errors.append(err)
                continue

            records = result if isinstance(result, list) else []

            # ── Step 3: resolve user IDs → names (before column mapping) ──
            if id_to_name and records:
                records = self._resolve_user_ids_in_records(
                    records,
                    id_to_name=id_to_name,
                    fields=USER_ID_FIELDS_BY_TABLE.get(table_name, []),
                )

            # ── Step 4: build DataFrame ────────────────────────────────────
            if table_name == "transmittals" and records:
                records = self._flatten_transmittal_records(records)

            df = self._to_dataframe(records, table_name)
            if table_name == "schedule":
                df = self._post_process_schedule(df)
                self.schedule_load_status = SCHEDULE_OK

            self.dataframes[table_name]   = df
            self.source_files[table_name] = f"ACC API: {table_name}/{project_id}"
            loaded.append(f"{table_name}({len(df)})")

        logger.info("ACC loaded for project %s: %s", project_id, ", ".join(loaded) or "nothing")
        if self.load_errors:
            logger.warning("ACC load errors: %s", self.load_errors)

        return self.dataframes

    async def load_all_projects_data(
        self, project_ids: List[str], max_projects: int = 10
    ) -> Dict[str, pd.DataFrame]:
        ids = project_ids[:max_projects]
        logger.info("ACC: Loading entity data for %d projects: %s", len(ids), ids)
        all_frames: Dict[str, List[pd.DataFrame]] = {}

        for pid in ids:
            fetchers = {
                "project_members": self.client.list_project_members(pid),
                "issues":          self.client.list_issues(pid),
                "rfis":            self.client.list_rfis(pid),
                "submittals":      self.client.list_submittals(pid),
                "transmittals":    self.client.list_transmittals(pid),
                "schedule":        self.client.list_project_schedule_activities(pid),
            }

            results         = await asyncio.gather(*fetchers.values(), return_exceptions=True)
            results_by_name = dict(zip(fetchers.keys(), results))

            id_to_name = self._extract_id_to_name(
                results_by_name.get("project_members", []), pid
            )

            for table_name in ACC_ENTITY_TABLES:
                result = results_by_name.get(table_name)

                if isinstance(result, Exception):
                    err = f"{table_name}/{pid}: {result}"
                    logger.error("ACC API error: %s", err)
                    self.load_errors.append(err)
                    if table_name == "schedule":
                        status, detail, _ = self._classify_schedule_result(result, pid)
                        self.schedule_load_status = status
                        self.schedule_load_detail = detail
                    continue

                records = result if isinstance(result, list) else []
                if not records:
                    continue

                if id_to_name:
                    records = self._resolve_user_ids_in_records(
                        records,
                        id_to_name=id_to_name,
                        fields=USER_ID_FIELDS_BY_TABLE.get(table_name, []),
                    )

                if table_name == "transmittals":
                    records = self._flatten_transmittal_records(records)

                df = self._to_dataframe(records, table_name)
                if table_name == "schedule":
                    df = self._post_process_schedule(df)

                if len(df) > 0:
                    all_frames.setdefault(table_name, []).append(df)

        for table_name, frames in all_frames.items():
            merged = pd.concat(frames, ignore_index=True)
            self.dataframes[table_name]   = merged
            self.source_files[table_name] = f"ACC API: {table_name} (all projects)"

        for entity in ACC_ENTITY_TABLES:
            if entity not in self.dataframes:
                self.dataframes[entity]   = self._to_dataframe([], entity)
                self.source_files[entity] = f"ACC API: {entity} (empty)"

        logger.info("ACC all-projects load summary: %s",
                    {k: len(v) for k, v in self.dataframes.items()})
        if self.load_errors:
            logger.warning("ACC load errors (%d): %s",
                           len(self.load_errors), self.load_errors[:5])

        return self.dataframes

    # ------------------------------------------------------------------
    # User ID → display name  (the core of K6AG-I87)
    # ------------------------------------------------------------------
    def _extract_id_to_name(
        self, members_result: Any, project_id: str
    ) -> Dict[str, str]:
        """Unwrap the project_members fetch result and build the id→name map.

        Logs clearly when resolution will be skipped so the root cause
        (missing account_id, 403, empty response) is visible in logs.
        """
        if isinstance(members_result, Exception):
            logger.error(
                "ACC user resolution SKIPPED for project %s — "
                "list_project_members raised: %s. "
                "User IDs will show as raw IDs.",
                project_id, members_result,
            )
            self.load_errors.append(f"project_members/{project_id}: {members_result}")
            return {}

        members = members_result if isinstance(members_result, list) else []
        if not members:
            logger.warning(
                "ACC user resolution SKIPPED for project %s — "
                "0 members returned. "
                "Ensure ACCApiClient is initialised with account_id=hub_id "
                "and the token includes the account:read scope.",
                project_id,
            )
            return {}

        id_to_name = self._build_user_id_to_name_map(members)
        logger.info(
            "ACC user resolution: built map with %d entries from %d members "
            "for project %s",
            len(id_to_name), len(members), project_id,
        )
        return id_to_name

    # Possible ID field names the ACC API uses across different endpoints
    _MEMBER_ID_KEYS: tuple = (
        "id", "userId", "user_id",
        "autodeskId", "autodesk_id",
        "autodeskUserId", "autodeskUserID",
        "oauthUserId", "oauthUserID",
        "uid", "guid",
    )

    @staticmethod
    def _flatten_resource_attrs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Merge JSON:API-style { attributes: {...} } into a flat dict."""
        if not isinstance(obj, dict):
            return {}
        out  = {k: v for k, v in obj.items() if k != "attributes"}
        attrs = obj.get("attributes")
        if isinstance(attrs, dict):
            for k, v in attrs.items():
                out.setdefault(k, v)
        return out

    @staticmethod
    def _id_alias_strings(raw: Optional[str]) -> List[str]:
        """Return all lookup aliases for a raw ID string.

        Handles:
          - plain UUID
          - uppercase variant
          - "urn:..." → tail after last ":"
          - "b.<uuid>" → strip "b." prefix
        """
        if raw is None:
            return []
        s = str(raw).strip()
        if not s:
            return []

        out: List[str] = []
        seen: Set[str] = set()

        def add(t: str) -> None:
            t = t.strip()
            if not t:
                return
            if t not in seen:
                seen.add(t)
                out.append(t)
            u = t.upper()
            if u not in seen:
                seen.add(u)
                out.append(u)

        add(s)
        if ":" in s:                        # "urn:adsk.wipprod:dm.user:abc123"
            add(s.split(":")[-1].strip())
        if "/" in s:                        # path-style IDs
            add(s.split("/")[-1].strip())
        if len(s) > 2 and s[:2].lower() == "b.":   # Data Management prefix
            add(s[2:])

        return out

    @staticmethod
    def _extract_user_name(user: Dict[str, Any]) -> Optional[str]:
        """Extract the best display name from a member record."""
        if not isinstance(user, dict):
            return None
        flat = ACCDataLoader._flatten_resource_attrs(user)

        # Prefer dedicated display/full-name fields
        for key in ("name", "displayName", "fullName"):
            val = flat.get(key)
            if val:
                return str(val).strip()

        # Fall back to userName or email
        for key in ("userName", "emailId", "email"):
            val = flat.get(key)
            if val:
                return str(val).strip()

        # Construct from first + last name
        first = flat.get("firstName") or flat.get("first_name") or ""
        last  = flat.get("lastName")  or flat.get("last_name")  or ""
        full  = f"{first} {last}".strip()
        return full if full else None

    @classmethod
    def _build_user_id_to_name_map(cls, members: List[Dict[str, Any]]) -> Dict[str, str]:
        """Build { id_alias: "display name" } from a list of member records.

        Registers every known ID alias so that regardless of which field the
        ACC API uses in issues/rfis/submittals/schedule, we get a match.
        """
        mapping: Dict[str, str] = {}
        for m in members or []:
            if not isinstance(m, dict):
                continue
            flat = cls._flatten_resource_attrs(m)
            name = cls._extract_user_name(flat)
            if not name:
                continue
            # Register every ID variant found in this record
            for key in cls._MEMBER_ID_KEYS:
                val = flat.get(key)
                if val is None or val == "":
                    continue
                for alias in cls._id_alias_strings(str(val)):
                    mapping[alias] = name

        return mapping

    @staticmethod
    def _lookup_display_name(
        id_to_name: Dict[str, str], raw: str
    ) -> Optional[str]:
        """Look up a raw ID value against all its aliases."""
        for alias in ACCDataLoader._id_alias_strings(raw):
            if alias in id_to_name:
                return id_to_name[alias]
        return None

    @staticmethod
    def _resolve_user_value(value: Any, id_to_name: Dict[str, str]) -> Any:
        """Resolve a single field value (string, dict, or JSON-string) to a name."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return value

        # Dict — e.g. { "id": "abc123", "type": "user" }
        if isinstance(value, dict):
            for key in ("id", "userId", "user_id", "autodeskId",
                        "autodesk_id", "autodeskUserId", "guid", "uid"):
                if key in value and value[key]:
                    resolved = ACCDataLoader._lookup_display_name(
                        id_to_name, str(value[key]).strip()
                    )
                    if resolved:
                        return resolved
            return value     # dict but no known ID key — leave as-is

        # String — may be a plain UUID, URN, or JSON-encoded dict/list
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return value
            # Try to parse as JSON first
            if (s.startswith("{") and s.endswith("}")) or \
               (s.startswith("[") and s.endswith("]")):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, dict):
                        return ACCDataLoader._resolve_user_value(parsed, id_to_name)
                except Exception:
                    pass
            resolved = ACCDataLoader._lookup_display_name(id_to_name, s)
            return resolved if resolved is not None else value

        # Anything else — stringify and try
        resolved = ACCDataLoader._lookup_display_name(id_to_name, str(value).strip())
        return resolved if resolved is not None else value

    @classmethod
    def _resolve_user_ids_in_records(
        cls,
        records:    List[Dict[str, Any]],
        id_to_name: Dict[str, str],
        fields:     List[str],
    ) -> List[Dict[str, Any]]:
        """Walk every record and resolve the specified fields in-place (copy).

        Called BEFORE _apply_column_mapping so field names always match
        the raw ACC API response keys defined in USER_ID_FIELDS_BY_TABLE.
        """
        if not records or not id_to_name or not fields:
            return records

        resolved = []
        for r in records:
            if not isinstance(r, dict):
                continue
            out = dict(r)
            for f in fields:
                if f in out:
                    out[f] = cls._resolve_user_value(out[f], id_to_name)
            resolved.append(out)
        return resolved

    # ------------------------------------------------------------------
    # Schedule helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_schedule_result(
        result: Any, project_id: str
    ) -> tuple:  # (status_code, detail_message, log_tag)
        """Classify an exception or empty result from the schedule fetch."""
        if isinstance(result, PermissionError):
            return (
                SCHEDULE_PERMISSION,
                str(result),
                "schedule(PERMISSION_ERROR)",
            )
        if isinstance(result, LookupError):
            return (
                SCHEDULE_NOT_FOUND,
                str(result),
                "schedule(NOT_FOUND)",
            )
        if isinstance(result, Exception):
            return (
                SCHEDULE_ERROR,
                str(result),
                "schedule(ERROR)",
            )
        if not result:
            return (
                SCHEDULE_EMPTY,
                (
                    f"Schedule API returned 0 activities for project {project_id}. "
                    "Check server logs for root cause."
                ),
                "schedule(0)",
            )
        return (SCHEDULE_OK, "", "")

    @staticmethod
    def _post_process_schedule(df: pd.DataFrame) -> pd.DataFrame:
        """Derive columns ScheduleAgent needs that ACC API doesn't return directly."""
        if df.empty:
            return df

        # Normalise status values
        if "status" in df.columns:
            df["status"] = (
                df["status"]
                .astype(str).str.strip().str.upper()
                .map(lambda s: ACC_SCHEDULE_STATUS_MAP.get(s, s.lower()))
            )

        # Derive is_wbs
        if "is_wbs" not in df.columns:
            wbs_mask = pd.Series(False, index=df.index)
            if "task_type" in df.columns:
                wbs_mask |= df["task_type"].astype(str).str.upper().isin(["WBS", "SUMMARY"])
            if "task_sub_type" in df.columns:
                wbs_mask |= df["task_sub_type"].astype(str).str.upper().isin(["WBS", "SUMMARY"])
            df["is_wbs"] = wbs_mask

        # Derive is_critical (approximation)
        if "is_critical" not in df.columns:
            if "parent_task_id" in df.columns:
                df["is_critical"] = df["parent_task_id"].isna() & ~df["is_wbs"]
            else:
                df["is_critical"] = False

        # Derive planned_end from end_date when absent
        if "planned_end" not in df.columns and "end_date" in df.columns:
            df["planned_end"] = df["end_date"]

        # Derive actual_end from actual_start + actual_duration
        if "actual_end" not in df.columns:
            if "actual_start" in df.columns and "actual_duration" in df.columns:
                try:
                    dur = pd.to_numeric(df["actual_duration"], errors="coerce")
                    df["actual_end"] = df["actual_start"] + pd.to_timedelta(dur, unit="D")
                except Exception:
                    df["actual_end"] = pd.NaT
            else:
                df["actual_end"] = pd.NaT

        return df



    # ------------------------------------------------------------------
    # Transmittal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _flatten_transmittal_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten nested sentBy object into top-level fields.

        ACC API returns:
            sentBy: {autodeskId, name, email, companyAutodeskId, companyName}
            recipients: {users: [...], companies: [...], roles: [...]}

        We flatten sentBy into sentBy_name, sentBy_email, etc. so that
        _apply_column_mapping can rename them to standardized names.
        """
        flattened = []
        for r in records:
            if not isinstance(r, dict):
                continue
            out = dict(r)

            # Flatten sentBy
            sent_by = out.pop("sentBy", None)
            if isinstance(sent_by, dict):
                out["sentBy_autodeskId"] = sent_by.get("autodeskId", "")
                out["sentBy_name"] = sent_by.get("name", "")
                out["sentBy_email"] = sent_by.get("email", "")
                out["sentBy_companyName"] = sent_by.get("companyName", "")
                out["sentBy_companyAutodeskId"] = sent_by.get("companyAutodeskId", "")
            elif isinstance(sent_by, str):
                # Fallback if sentBy is just a string ID
                out["sentBy_autodeskId"] = sent_by
                out["sentBy_name"] = sent_by

            # Flatten recipients into a simple count/list
            recipients = out.pop("recipients", None)
            if isinstance(recipients, dict):
                users = recipients.get("users", [])
                out["recipient_names"] = ", ".join(
                    u.get("name", u.get("autodeskId", ""))
                    for u in users if isinstance(u, dict)
                ) if users else ""
                out["recipient_count"] = len(users)

            # Remove complex nested fields that don't serialize to DataFrame well
            out.pop("externalMembers", None)

            flattened.append(out)
        return flattened

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _to_dataframe(self, records: List[Dict], table_name: str) -> pd.DataFrame:
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df = self._apply_column_mapping(df, table_name)
        df = self._convert_dates(df)
        return df

    @staticmethod
    def _apply_column_mapping(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        mapping = ACC_COLUMN_MAPPINGS.get(table_name)
        if mapping is None:
            return df
        rename_dict = {old: new for old, new in mapping.items() if old in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)
            logger.debug("Renamed %d columns in %s", len(rename_dict), table_name)
        return df

    @staticmethod
    def _convert_dates(df: pd.DataFrame) -> pd.DataFrame:
        date_keywords = [
            "date", "start", "end", "created", "updated",
            "due", "closed", "responded", "opened", "finish", "_at",
        ]
        for col in df.columns:
            if any(kw in col.lower() for kw in date_keywords):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
        return df
