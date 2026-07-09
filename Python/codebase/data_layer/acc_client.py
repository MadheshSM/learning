"""ACC (Autodesk Construction Cloud) OAuth 2.0 client and REST API wrapper.

Uses the Autodesk Platform Services (APS) 3-legged OAuth flow.
Mirrors the pattern from ti-backend/src/modules/acc-auth/.
"""
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APS OAuth URLs
# ---------------------------------------------------------------------------
AUTHORIZE_URL = "https://developer.api.autodesk.com/authentication/v2/authorize"
TOKEN_URL     = "https://developer.api.autodesk.com/authentication/v2/token"
PROFILE_URL   = "https://developer.api.autodesk.com/userprofile/v1/users/@me"

SCOPES = "data:read data:write data:create data:search viewables:read account:read"


# ---------------------------------------------------------------------------
# ACCAuthManager
# ---------------------------------------------------------------------------
class ACCAuthManager:
    """Manages ACC OAuth 2.0 3-legged flow and token storage (in-memory)."""

    _tokens: Dict[str, Dict] = {}
    _pending_states: Dict[str, Dict] = {}

    def __init__(self):
        self.client_id     = os.getenv("APS_CLIENT_ID", "")
        self.client_secret = os.getenv("APS_CLIENT_SECRET", "")
        self.callback_url  = os.getenv("APS_CALLBACK_URL", "")

    def get_authorization_url(self, app_user_id: str = "") -> tuple[str, str]:
        state = str(uuid.uuid4())
        self._pending_states[state] = {"created_at": time.time(), "app_user_id": app_user_id}
        params = {
            "response_type": "code",
            "client_id":     self.client_id,
            "redirect_uri":  self.callback_url,
            "scope":         SCOPES,
            "state":         state,
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}", state

    async def exchange_code(self, code: str, state: str) -> Dict:
        app_user_id = ""
        if state and state in self._pending_states:
            app_user_id = self._pending_states[state].get("app_user_id", "")
            del self._pending_states[state]

        data = {
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  self.callback_url,
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise PermissionError(f"Token exchange failed: {resp.status_code}")

        token_data  = resp.json()
        profile     = await self.get_user_profile(token_data["access_token"])
        acc_user_id = str(profile.get("userId", profile.get("sub", "unknown")))
        store_key   = app_user_id or acc_user_id

        self._tokens[store_key] = {
            "access_token":  token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at":    time.time() + token_data.get("expires_in", 3600),
            "user_profile":  profile,
            "acc_user_id":   acc_user_id,
        }
        return {
            "acc_user_id": acc_user_id,
            "app_user_id": store_key,
            "user_name":   profile.get("userName", ""),
            "email":       profile.get("emailId", ""),
        }

    async def refresh_access_token(self, user_key: str) -> str:
        token_entry = self._tokens.get(user_key)
        if not token_entry or not token_entry.get("refresh_token"):
            raise PermissionError(f"No refresh token for user {user_key}")
        data = {
            "grant_type":    "refresh_token",
            "refresh_token": token_entry["refresh_token"],
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
            "scope":         SCOPES,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TOKEN_URL, data=data)
        if resp.status_code != 200:
            self._tokens.pop(user_key, None)
            raise PermissionError("Token refresh failed. User needs to re-authenticate.")
        new_data = resp.json()
        token_entry["access_token"] = new_data["access_token"]
        if new_data.get("refresh_token"):
            token_entry["refresh_token"] = new_data["refresh_token"]
        token_entry["expires_at"] = time.time() + new_data.get("expires_in", 3600)
        return new_data["access_token"]

    async def get_valid_token(self, user_key: str) -> str:
        token_entry = self._tokens.get(user_key)
        if not token_entry:
            raise PermissionError(f"No ACC tokens for user {user_key}. Please login.")
        if token_entry["expires_at"] < time.time() + 300:
            return await self.refresh_access_token(user_key)
        return token_entry["access_token"]

    def get_status(self, user_key: str) -> Dict:
        token_entry = self._tokens.get(user_key)
        if not token_entry:
            return {"connected": False}
        profile = token_entry.get("user_profile", {})
        return {
            "connected":   True,
            "acc_user_id": token_entry.get("acc_user_id", user_key),
            "app_user_id": user_key,
            "user_name":   profile.get("userName", ""),
            "email":       profile.get("emailId", ""),
        }

    def get_any_connected_user(self) -> Optional[str]:
        for user_key in self._tokens:
            return user_key
        return None

    def disconnect(self, user_key: str) -> bool:
        if user_key in self._tokens:
            del self._tokens[user_key]
            return True
        return False

    @staticmethod
    async def get_user_profile(access_token: str) -> Dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise PermissionError("Failed to fetch ACC user profile")
        return resp.json()


# ---------------------------------------------------------------------------
# ACCApiClient
# ---------------------------------------------------------------------------
class ACCApiClient:
    """Calls Autodesk Construction Cloud REST APIs with a valid access token."""

    BASE = "https://developer.api.autodesk.com"

    def __init__(self, access_token: str, account_id: str = ""):
        self.access_token = access_token
        self.account_id   = account_id          # hub ID e.g. "b.xxxxxxxx-..."
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        }
        self._timeout = 30.0

    # ------------------------------------------------------------------
    # Project ID helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_project_id(project_id: str) -> str:
        """Strip 'b.' prefix → plain UUID for Construction APIs."""
        raw = str(project_id or "").strip()
        return raw[2:] if raw.startswith("b.") else raw

    @staticmethod
    def _dm_project_id(project_id: str) -> str:
        """Ensure 'b.' prefix for Data Management API calls."""
        raw = str(project_id or "").strip()
        return raw if raw.startswith("b.") else f"b.{raw}"

    # ------------------------------------------------------------------
    # Core HTTP helpers
    # ------------------------------------------------------------------
    async def _get(self, url: str, params: Optional[Dict] = None) -> Any:
        logger.debug("ACC API GET %s params=%s", url, params)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, headers=self._headers, params=params)

        logger.debug("ACC API %d <- GET %s", resp.status_code, url)

        if resp.status_code == 401:
            raise PermissionError("ACC API: authentication failed (401). Token may be expired.")
        if resp.status_code == 403:
            raise PermissionError(
                f"ACC API: access denied (403) for {url}. "
                "Check user permissions / OAuth scopes (need account:read)."
            )
        if resp.status_code == 404:
            raise LookupError(f"ACC API: not found (404) — {url}")
        if resp.status_code >= 400:
            logger.error("ACC API %d GET %s -> %s", resp.status_code, url, resp.text[:300])
            resp.raise_for_status()

        return resp.json()

    async def _get_all_pages(self, url: str, params: Optional[Dict] = None) -> List[Dict]:
        all_results: List[Dict] = []
        params = dict(params or {})
        params.setdefault("limit", 100)
        offset = 0

        while True:
            params["offset"] = offset
            data    = await self._get(url, params)
            results: List[Dict] = []

            if isinstance(data, list):
                results = data
            elif isinstance(data, dict):
                results = data.get("results", data.get("data", data.get("items", [])))

            all_results.extend(results)

            pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
            total      = pagination.get("totalResults", len(all_results))
            if len(all_results) >= total or not results:
                break
            offset += len(results)

        return all_results

    # ------------------------------------------------------------------
    # Hubs / Projects  (Data Management API)
    # ------------------------------------------------------------------
    async def list_hubs(self) -> List[Dict]:
        data = await self._get(f"{self.BASE}/project/v1/hubs")
        return data.get("data", [])

    async def list_projects(self) -> List[Dict]:
        hubs = await self.list_hubs()
        if not hubs:
            logger.warning("ACC: No hubs found for this user")
            return []

        all_projects: List[Dict] = []
        for hub in hubs:
            hub_id   = hub.get("id", "")
            hub_name = hub.get("attributes", {}).get("name", "")
            if not hub_id:
                continue
            try:
                data         = await self._get(f"{self.BASE}/project/v1/hubs/{hub_id}/projects")
                projects_raw = data.get("data", [])
            except Exception as e:
                logger.warning("ACC: Failed to fetch projects for hub %s: %s", hub_id, e)
                continue

            for proj in projects_raw:
                attrs    = proj.get("attributes", {})
                raw_id   = proj.get("id", "")
                clean_id = self._clean_project_id(raw_id)

                all_projects.append({
                    "id":          clean_id,
                    "raw_id":      raw_id,
                    "name":        attrs.get("name", ""),
                    "status":      attrs.get("status", ""),
                    "startDate":   attrs.get("startDate"),
                    "endDate":     attrs.get("endDate"),
                    "projectType": attrs.get("type", ""),
                    "city":        attrs.get("city", ""),
                    "country":     attrs.get("country", ""),
                    "hub_id":      hub_id,
                    "hub_name":    hub_name,
                })

        logger.info("ACC: Found %d projects across %d hubs", len(all_projects), len(hubs))
        return all_projects

    # ------------------------------------------------------------------
    # Issues / RFIs / Submittals
    # ------------------------------------------------------------------
    async def list_issues(self, project_id: str) -> List[Dict]:
        pid = self._clean_project_id(project_id)
        return await self._get_all_pages(
            f"{self.BASE}/construction/issues/v1/projects/{pid}/issues"
        )

    async def list_rfis(self, project_id: str) -> List[Dict]:
        pid = self._clean_project_id(project_id)
        try:
            return await self._get_all_pages(
                f"{self.BASE}/construction/rfis/v2/projects/{pid}/rfis"
            )
        except Exception as e:
            logger.warning("ACC RFI v2 failed for %s: %s", pid, e)
            return []

    async def list_submittals(self, project_id: str) -> List[Dict]:
        pid = self._clean_project_id(project_id)
        try:
            return await self._get_all_pages(
                f"{self.BASE}/construction/submittals/v2/projects/{pid}/items"
            )
        except Exception as e:
            logger.warning("ACC Submittals failed for %s: %s", pid, e)
            return []

    # ------------------------------------------------------------------
    # Transmittals  (Data Management → Transmittals)
    # ------------------------------------------------------------------
    async def list_transmittals(self, project_id: str) -> List[Dict]:
        """GET /construction/transmittals/v1/projects/{projectId}/transmittals

        ACC UI columns → API response fields:
          Status           → status  (SENDING / COMPLETED / FAILED)
          ID               → sequenceId
          Title            → title
          Sent by          → sentBy (user ID), sentByName (display name)
          Sender company   → sentByCompanyName
          Documents count  → documentsCount
          Created          → createdAt
          Updated          → updatedAt
        """
        pid = self._clean_project_id(project_id)
        try:
            return await self._get_all_pages(
                f"{self.BASE}/construction/transmittals/v1/projects/{pid}/transmittals"
            )
        except Exception as e:
            logger.warning("ACC Transmittals failed for %s: %s", pid, e)
            return []

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    _schedule_cache: Dict[str, Dict[str, Any]] = {}
    _SCHEDULE_CACHE_TTL = 600  # 10 minutes

    async def _list_schedules(self, clean_pid: str) -> List[Dict]:
        url  = f"{self.BASE}/construction/schedule/v1/projects/{clean_pid}/schedules"
        data = await self._get(url)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("results", data.get("data", data.get("items", [])))
        return []

    async def _list_schedule_activities(self, clean_pid: str, schedule_id: str) -> List[Dict]:
        url = (
            f"{self.BASE}/construction/schedule/v1/projects/{clean_pid}"
            f"/schedules/{schedule_id}/activities"
        )
        try:
            return await self._get_all_pages(url, params={"limit": 500})
        except Exception as e:
            logger.error(
                "ACC Schedule: error fetching activities | project=%s schedule=%s — %s",
                clean_pid, schedule_id, e,
            )
            return []

    async def list_project_schedule_activities(self, project_id: str) -> List[Dict]:
        clean_pid = self._clean_project_id(project_id)
        cache_key = f"schedule:{clean_pid}"

        cached = self._schedule_cache.get(cache_key)
        if cached and (time.time() - cached["fetched_at"]) < self._SCHEDULE_CACHE_TTL:
            return cached["data"]

        schedules = await self._list_schedules(clean_pid)
        if not schedules:
            logger.warning("ACC Schedule: no schedules found for project %s", clean_pid)
            return []

        all_activities: List[Dict] = []
        for sched in schedules:
            schedule_id   = sched.get("id") or sched.get("scheduleId", "")
            schedule_name = sched.get("name") or sched.get("scheduleName", "")
            if not schedule_id:
                continue
            activities = await self._list_schedule_activities(clean_pid, schedule_id)
            for act in activities:
                act.setdefault("scheduleId",   schedule_id)
                act.setdefault("scheduleName", schedule_name)
                act.setdefault("projectId",    clean_pid)
            all_activities.extend(activities)

        self._schedule_cache[cache_key] = {
            "data":       all_activities,
            "fetched_at": time.time(),
        }
        return all_activities

    # ------------------------------------------------------------------
    # Project members  (used for user ID → display name resolution)
    #
    # Two endpoints tried in order:
    #   1. Construction Admin API v1  — most complete, needs account:read scope
    #   2. Data Management API        — fallback, needs hub/account_id set
    #
    # If both fail, returns [] and user IDs will remain unresolved.
    # Make sure account_id is passed when constructing ACCApiClient and
    # that the OAuth token includes the account:read scope.
    # ------------------------------------------------------------------
    async def list_project_members(self, project_id: str) -> List[Dict]:
        pid = self._clean_project_id(project_id)

        # ── Primary: Construction Admin API v1 ───────────────────────────
        primary_url = f"{self.BASE}/construction/admin/v1/projects/{pid}/users"
        try:
            members = await self._get_all_pages(primary_url)
            if members:
                logger.info(
                    "ACC members [primary] project=%s → %d members", pid, len(members)
                )
                return members
            # Empty list returned — log and try fallback
            logger.warning(
                "ACC members [primary] project=%s → 0 members (empty response). "
                "Trying fallback.", pid,
            )
        except PermissionError as e:
            logger.warning(
                "ACC members [primary] 403 for project=%s: %s. "
                "Ensure token has account:read scope.", pid, e,
            )
        except LookupError as e:
            logger.warning(
                "ACC members [primary] 404 for project=%s: %s.", pid, e,
            )
        except Exception as e:
            logger.warning(
                "ACC members [primary] failed for project=%s: %s. "
                "Trying fallback.", pid, e,
            )

        # ── Fallback: Data Management API ────────────────────────────────
        # Requires self.account_id (hub ID) to be set.
        if not self.account_id:
            logger.error(
                "ACC members [fallback] skipped for project=%s — "
                "account_id not set on ACCApiClient. "
                "Pass account_id=hub_id when constructing ACCApiClient. "
                "User IDs will NOT be resolved to names.", pid,
            )
            return []

        dm_pid       = self._dm_project_id(pid)
        fallback_url = (
            f"{self.BASE}/project/v1/hubs/{self.account_id}"
            f"/projects/{dm_pid}/users"
        )
        try:
            data = await self._get(fallback_url)
            members: List[Dict] = []
            if isinstance(data, list):
                members = data
            elif isinstance(data, dict):
                for key in ("results", "data", "items", "users"):
                    items = data.get(key)
                    if isinstance(items, list):
                        members = items
                        break
            if members:
                logger.info(
                    "ACC members [fallback] project=%s → %d members", pid, len(members)
                )
                return members
            logger.warning(
                "ACC members [fallback] project=%s → 0 members. "
                "User IDs will NOT be resolved to names.", pid,
            )
        except Exception as e:
            logger.error(
                "ACC members [fallback] also failed for project=%s: %s. "
                "User IDs will NOT be resolved to names.", pid, e,
            )

        return []

    # ------------------------------------------------------------------
    # Debug helper — call from a test script to diagnose member resolution
    # ------------------------------------------------------------------
    async def debug_user_resolution(self, project_id: str) -> Dict[str, Any]:
        """Standalone debug — tests both member endpoints and prints what
        user fields are available in the response.

        Usage:
            result = await client.debug_user_resolution("99e32525-...")
            print(result)
        """
        pid    = self._clean_project_id(project_id)
        report: Dict[str, Any] = {
            "project_id_raw":   project_id,
            "project_id_clean": pid,
            "account_id":       self.account_id,
            "primary_url":      f"{self.BASE}/construction/admin/v1/projects/{pid}/users",
            "fallback_url":     (
                f"{self.BASE}/project/v1/hubs/{self.account_id}"
                f"/projects/{self._dm_project_id(pid)}/users"
                if self.account_id else "skipped (account_id not set)"
            ),
            "primary_result":   None,
            "fallback_result":  None,
            "sample_member":    None,
            "errors":           [],
        }

        # Test primary
        try:
            members = await self._get_all_pages(report["primary_url"])
            report["primary_result"] = {
                "count":       len(members),
                "sample_keys": list(members[0].keys()) if members else [],
            }
            if members:
                report["sample_member"] = members[0]
        except Exception as e:
            report["errors"].append(f"primary: {type(e).__name__}: {e}")
            report["primary_result"] = {"error": str(e)}

        # Test fallback
        if self.account_id:
            try:
                data    = await self._get(report["fallback_url"])
                members = []
                if isinstance(data, list):
                    members = data
                elif isinstance(data, dict):
                    for key in ("results", "data", "items", "users"):
                        items = data.get(key)
                        if isinstance(items, list):
                            members = items
                            break
                report["fallback_result"] = {
                    "count":       len(members),
                    "sample_keys": list(members[0].keys()) if members else [],
                }
                if members and not report["sample_member"]:
                    report["sample_member"] = members[0]
            except Exception as e:
                report["errors"].append(f"fallback: {type(e).__name__}: {e}")
                report["fallback_result"] = {"error": str(e)}

        return report

    # ------------------------------------------------------------------
    # Debug helper for schedule
    # ------------------------------------------------------------------
    async def debug_schedule_fetch(self, project_id: str) -> Dict[str, Any]:
        clean_pid = self._clean_project_id(project_id)
        report: Dict[str, Any] = {
            "project_id_raw":          project_id,
            "project_id_clean":        clean_pid,
            "schedules":               [],
            "activities_per_schedule": {},
            "errors":                  [],
        }
        try:
            schedules = await self._list_schedules(clean_pid)
            report["schedules"] = [
                {
                    "id":   s.get("id") or s.get("scheduleId"),
                    "name": s.get("name") or s.get("scheduleName"),
                }
                for s in schedules
            ]
        except Exception as e:
            report["errors"].append(f"listing schedules: {type(e).__name__}: {e}")
            return report

        for sched in schedules:
            sid  = sched.get("id") or sched.get("scheduleId", "")
            name = sched.get("name") or sched.get("scheduleName", "unknown")
            if not sid:
                continue
            try:
                activities = await self._list_schedule_activities(clean_pid, sid)
                report["activities_per_schedule"][sid] = {
                    "name":            name,
                    "count":           len(activities),
                    "sample_keys":     list(activities[0].keys())[:20] if activities else [],
                    "sample_activity": activities[0] if activities else None,
                }
            except Exception as e:
                report["activities_per_schedule"][sid] = {
                    "name":  name,
                    "error": f"{type(e).__name__}: {e}",
                }
                report["errors"].append(f"schedule {sid}: {e}")

        return report



