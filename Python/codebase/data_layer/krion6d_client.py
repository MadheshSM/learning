"""HTTP client for Krion6d REST API"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://jkr-api.krion6d.com/api/v1"

# File extensions treated as project documents (lowercase, leading dot).
SUPPORTED_DOCUMENT_EXTENSIONS = frozenset({
    ".pdf", ".dwg", ".dxf", ".rvt", ".rfa", ".rte", ".ifc", ".nwd", ".nwc", ".dwf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".zip",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bim", ".3dm", ".skp",
})


def _normalize_ext_fragment(ext: Optional[str]) -> str:
    if not ext or not isinstance(ext, str):
        return ""
    e = ext.strip().lower()
    if not e:
        return ""
    return e if e.startswith(".") else f".{e}"


def _extension_from_text(path: Optional[str]) -> str:
    if not path or not isinstance(path, str):
        return ""
    path = path.rstrip("/").split("?", 1)[0]
    if "." not in path:
        return ""
    return _normalize_ext_fragment(path.rsplit(".", 1)[-1])


def _row_candidate_extension(row: Dict[str, Any]) -> str:
    for key in ("extension", "file_extension", "fileExtension"):
        v = row.get(key)
        if v:
            return _normalize_ext_fragment(str(v))
    for key in ("name", "fileName", "filename", "title", "url", "path"):
        v = row.get(key)
        if v:
            ext = _extension_from_text(str(v))
            if ext:
                return ext
    return ""


def _is_document_like_row(row: Dict[str, Any]) -> bool:
    if row.get("isFolder") is True or row.get("is_folder") is True:
        return False
    t = row.get("type")
    if isinstance(t, str) and t.lower() == "document":
        return True
    ext = _row_candidate_extension(row)
    return bool(ext and ext in SUPPORTED_DOCUMENT_EXTENSIONS)


class Krion6dClient:
    """Async HTTP client wrapping the Krion6d REST API."""

    def __init__(self, auth_token: str, module: str = "design", user_id: Optional[int] = None):
        self.module = module
        self.user_id = user_id
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Origin": "https://jkr.krion6d.com",
        }
        self._timeout = 30.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_curl(method: str, url: str, headers: Dict[str, str], json_body: Any = None) -> str:
        """Build a curl command string for logging/debugging."""
        parts = [f"curl -X {method}"]
        for k, v in headers.items():
            # Mask bearer token for safety
            val = v if "Bearer" not in v else "Bearer <token>"
            parts.append(f"  -H '{k}: {val}'")
        if json_body is not None:
            parts.append(f"  -d '{json.dumps(json_body)}'")
        parts.append(f"  '{url}'")
        return " \\\n".join(parts)

    async def _request(
        self, method: str, path: str, json_body: Any = None, params: Optional[Dict] = None
    ) -> Any:
        """Execute an HTTP request and return the parsed JSON body."""
        url = f"{BASE_URL}{path}"

        # Build full URL with query params for curl log
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            curl_url = f"{url}?{qs}"
        else:
            curl_url = url

        curl_cmd = self._to_curl(method, curl_url, self._headers, json_body)
        logger.info(f"Krion6d API request:\n{curl_cmd}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method, url, headers=self._headers, json=json_body, params=params
            )

        # Log response with body preview for debugging
        body_preview = response.text[:500] if response.text else "(empty)"
        logger.info(f"Krion6d API response: {response.status_code} ({len(response.text)} bytes)\n{body_preview}")

        if response.status_code == 401:
            raise PermissionError("Krion6d API: authentication failed (401). Token may be expired.")

        if response.status_code >= 400:
            body_preview = response.text[:200] if response.text else "(empty)"
            logger.error(f"Krion6d API {response.status_code} {method} {url} → {body_preview}")
            response.raise_for_status()

        return response.json()

    def _default_list_body(
        self, filters: Optional[Dict] = None, include_user_filter: bool = True
    ) -> Dict:
        """Build the default request body for list endpoints, including user context."""
        body = {
            "module": self.module,
            "search": "",
            "filters": [],
            "status": "",
            "user": [{"id": self.user_id, "type": "user"}] if (include_user_filter and self.user_id) else [],
            "workflow": [],
            "sortBy": [{"field": "id", "sort": "ASC"}],
        }
        if filters:
            body.update(filters)
        return body

    async def _post_list(
        self,
        path: str,
        filters: Optional[Dict] = None,
        limit: int = 1000,
        include_user_filter: bool = True,
    ) -> List[Dict]:
        """POST to a list endpoint to fetch all records."""
        body = self._default_list_body(filters, include_user_filter=include_user_filter)
        data = await self._request("POST", path, json_body=body, params={"limit": limit})

        # The API may return [] , {"data": []} , or {"items": []}
        if isinstance(data, list):
            logger.debug(f"_post_list {path}: got raw list with {len(data)} items")
            return data
        if isinstance(data, dict):
            logger.debug(f"_post_list {path}: got dict with keys={list(data.keys())}")
            for key in ("data", "items", "results", "records"):
                if key in data and isinstance(data[key], list):
                    logger.debug(f"_post_list {path}: extracted '{key}' with {len(data[key])} items")
                    return data[key]
            # Single-object response wrapped in dict – return as one-element list
            return [data]
        return []

    # ------------------------------------------------------------------
    # Project endpoints
    # ------------------------------------------------------------------
    async def list_projects(self, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /{module}/project/list?limit=1000"""
        return await self._post_list(f"/{self.module}/project/list", filters, limit=1000)

    async def get_project_options(self) -> Any:
        """GET /{module}/project/options"""
        return await self._request("GET", f"/{self.module}/project/options")

    # ------------------------------------------------------------------
    # Workflow/Review endpoints
    # ------------------------------------------------------------------
    async def list_workflows(self, project_id: str, entity: str) -> List[Dict]:
        """POST /{module}/project/{id}/review/list?limit=100&entity={entity}
        Returns workflow configurations with step details for an entity type."""
        data = await self._request(
            "POST",
            f"/{self.module}/project/{project_id}/review/list",
            json_body={},
            params={"limit": 100, "entity": entity}
        )
        # Response is {success, data: {data: [...], meta: {...}}}
        if isinstance(data, dict):
            inner = data.get("data", data)
            if isinstance(inner, dict):
                return inner.get("data", [])
            if isinstance(inner, list):
                return inner
        return []

    async def get_workflow_steps(self, review_id: int) -> Dict:
        """GET /{module}/project/{projectId}/review/{reviewId}
        Returns workflow with its step details."""
        # This needs project context but review ID is globally unique
        # The findOne endpoint returns step names and configurations
        return await self._request("GET", f"/{self.module}/project/0/review/{review_id}")

    # ------------------------------------------------------------------
    # Entity endpoints (require project_id)
    # ------------------------------------------------------------------
    async def list_issues(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/issue/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/{self.module}/issue/list", filters, limit=-1
        )

    async def list_rfis(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/rfi/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/{self.module}/rfi/list", filters, limit=-1
        )

    async def list_tasks(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/task/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/{self.module}/task/list", filters, limit=-1
        )

    async def list_tickets(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/ticket/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/{self.module}/ticket/list", filters, limit=-1
        )

    async def list_rfas(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/rfa/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/{self.module}/rfa/list", filters, limit=-1
        )

    async def list_submittals(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/submittal/list?limit=-1 (with safe fallback)."""

        def _extract(data: Any) -> List[Dict]:
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, dict):
                    items = inner.get("data", [])
                    if isinstance(items, list):
                        return items
                if isinstance(inner, list):
                    return inner
            return []

        # Rejected hypotheses cleanup:
        # - module path /project/{id}/design/submittal/list -> 404/502
        # - limit=1000 on module path -> still non-functional
        # Keep only valid path and test body-shape hypotheses.
        _attempts = [
            # H5: default list body with user filter
            {
                "url": f"/project/{project_id}/submittal/list",
                "limit": -1,
                "body": self._default_list_body(filters, include_user_filter=True),
                "hypothesis_id": "H5",
                "body_variant": "default_user",
            },
            # H6: default list body without user filter
            {
                "url": f"/project/{project_id}/submittal/list",
                "limit": -1,
                "body": self._default_list_body(filters, include_user_filter=False),
                "hypothesis_id": "H6",
                "body_variant": "default_no_user",
            },
            # H7: minimal body in case status/workflow/sortBy causes server-side filtering
            {
                "url": f"/project/{project_id}/submittal/list",
                "limit": -1,
                "body": {"search": "", "filters": []},
                "hypothesis_id": "H7",
                "body_variant": "minimal",
            },
        ]

        for _a in _attempts:
            _url = _a["url"]
            _limit = _a["limit"]
            body = _a["body"]
            _hid = _a["hypothesis_id"]
            _variant = _a["body_variant"]
            try:
                data = await self._request("POST", _url, json_body=body, params={"limit": _limit})
                items = _extract(data)
                if items:
                    return items
            except Exception as _e:
                pass
        return []

    @staticmethod
    def _extract_list_payload(data: Any) -> List[Dict]:
        """Normalize common API list response shapes."""
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            inner = data.get("data", data)
            if isinstance(inner, dict):
                items = inner.get("data", [])
                if isinstance(items, list):
                    return [x for x in items if isinstance(x, dict)]
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        return []

    async def list_transmittals(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/transmittal/list?limit=1000 (with safe fallback)."""
        # First attempt: user-scoped list
        body = self._default_list_body(filters)
        try:
            data = await self._request(
                "POST",
                f"/project/{project_id}/transmittal/list",
                json_body=body,
                params={"limit": 1000},
            )
            if isinstance(data, list):
                if data:
                    return data
            elif isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, dict):
                    items = inner.get("data", [])
                    if isinstance(items, list) and items:
                        return items
                if isinstance(inner, list) and inner:
                    return inner
        except Exception:
            pass

        # Second attempt: remove user filter
        body = self._default_list_body(filters)
        body["user"] = []
        try:
            data = await self._request(
                "POST",
                f"/project/{project_id}/transmittal/list",
                json_body=body,
                params={"limit": 1000},
            )
            if isinstance(data, list):
                if data:
                    return data
            elif isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, dict):
                    items = inner.get("data", [])
                    if isinstance(items, list) and items:
                        return items
                if isinstance(inner, list) and inner:
                    return inner
        except Exception:
            pass

        # Final fallback: deployments that require module segment
        try:
            fallback = await self._post_list(
                f"/project/{project_id}/{self.module}/transmittal/list",
                filters,
                limit=1000,
            )
            if fallback:
                return fallback
        except Exception:
            pass

        return []

    async def list_transmittal_attachments(self, project_id: str, transmittal_id: Any) -> List[Dict]:
        """POST /project/{projectId}/transmittal/{transmittalId}/attachments"""
        try:
            data = await self._request(
                "POST",
                f"/project/{project_id}/transmittal/{transmittal_id}/attachments",
                json_body={},
                params={"limit": 100},
            )
            return self._extract_list_payload(data)
        except Exception as e:
            logger.warning(
                f"list_transmittal_attachments failed for project={project_id}, transmittal={transmittal_id}: {e}"
            )
            return []

    async def get_submittal(self, project_id: str, submittal_id: Any) -> Dict[str, Any]:
        """GET /project/{projectId}/submittal/{submittalId}"""
        try:
            data = await self._request(
                "GET",
                f"/project/{project_id}/submittal/{submittal_id}",
            )
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(
                f"get_submittal failed for project={project_id}, submittal={submittal_id}: {e}"
            )
            return {}

    async def list_boms(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/{module}/bom/list (fallback: /project/{id}/bom/list)."""
        items = await self._post_list(
            f"/project/{project_id}/{self.module}/bom/list", filters, limit=-1
        )
        if items:
            return items
        try:
            fallback = await self._post_list(
                f"/project/{project_id}/bom/list", filters, limit=-1
            )
            if fallback:
                return fallback
        except Exception:
            pass
        return []

    async def _list_with_paths(
        self,
        paths: List[str],
        filters: Optional[Dict] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """Try list endpoints in order with user + no-user body fallbacks."""
        for path in paths:
            for include_user in (True, False):
                try:
                    data = await self._post_list(
                        path,
                        filters=filters,
                        limit=limit,
                        include_user_filter=include_user,
                    )
                    if data:
                        return data
                except Exception:
                    continue
        return []

    async def list_meetings(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """List meetings for a project."""
        return await self._list_with_paths(
            paths=[
                f"/{self.module}/project/{project_id}/meeting/list",
                f"/{self.module}/project/{project_id}/meetingminutes/list",
                f"/project/{project_id}/{self.module}/meeting/list",
                f"/project/{project_id}/meeting/list",
                f"/project/{project_id}/{self.module}/meetingminutes/list",
                f"/project/{project_id}/meetingminutes/list",
                f"/project/{project_id}/{self.module}/meeting-minutes/list",
                f"/project/{project_id}/meeting-minutes/list",
            ],
            filters=filters,
            limit=1000,
        )

    async def list_punch_lists(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/punch-list/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/punch-list/list", filters, limit=-1
        )

    async def list_check_lists(self, project_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """POST /project/{id}/check-list/list?limit=-1"""
        return await self._post_list(
            f"/project/{project_id}/check-list/list", filters, limit=-1
        )

    @staticmethod
    def _parse_search_response(data: Any) -> List[Dict]:
        """Normalize POST /search body: raw list or dict with data/items/results/records."""
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("data", "items", "results", "records"):
                inner = data.get(key)
                if isinstance(inner, list):
                    return [x for x in inner if isinstance(x, dict)]
            return [data]
        return []

    @staticmethod
    def _project_id_for_search_body(project_id: str) -> Any:
        s = str(project_id).strip()
        if s.isdigit():
            return int(s)
        return project_id

    async def list_documents(
        self, project_id: str, filters: Optional[Dict] = None
    ) -> List[Dict]:
        """POST /search (and fallbacks) — project files; excludes folders, keeps document-like rows."""
        try:
            body: Dict[str, Any] = {
                "search": "",
                "projectId": self._project_id_for_search_body(project_id),
                "limit": -1,
            }
            if filters:
                body.update(filters)

            paths = [
                "/search",
                f"/{self.module}/search",
                f"/project/{project_id}/search",
                f"/project/{project_id}/{self.module}/search",
            ]

            for path in paths:
                try:
                    data = await self._request("POST", path, json_body=body)
                    rows = self._parse_search_response(data)
                    out = [r for r in rows if _is_document_like_row(r)]
                    logger.info(
                        f"list_documents {path}: {len(out)} document-like rows (from {len(rows)} raw)"
                    )
                    return out
                except Exception as e:
                    logger.warning(f"list_documents attempt {path} failed: {e}")
                    continue

            return []
        except Exception as e:
            logger.warning(f"list_documents failed for project {project_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Dashboard endpoints
    # ------------------------------------------------------------------
    async def get_dashboard(
        self,
        project_ids: Optional[List[int]] = None,
        user_ids: Optional[List[int]] = None,
        time_filter: str = "all"
    ) -> Any:
        """POST /dashboard - Get cross-project summary counts.
        time_filter: 'this_week', 'this_month', 'this_year', 'all'"""
        body = {
            "projectIds": project_ids or [],
            "userIds": user_ids or [],
            "filter": time_filter
        }
        return await self._request("POST", "/dashboard", json_body=body)

    async def get_project_dashboard(
        self, project_id: str, entity: str, filters: Optional[Dict] = None
    ) -> Any:
        """POST /dashboard/{module}/project/{id}/{entity}/details"""
        return await self._request(
            "POST",
            f"/dashboard/{self.module}/project/{project_id}/{entity}/details",
            json_body=filters or {},
        )
