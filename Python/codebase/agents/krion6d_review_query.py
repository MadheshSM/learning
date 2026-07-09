"""Shared helpers for Krion6d schedule rows used as review/task workflow items (same loader path)."""
from typing import Any, Dict, List


def project_id_filter_values(project_id: str) -> List[Any]:
    """Match project_id stored as string or int in DataFrames (same as DataAnalystAgent)."""
    vals: List[Any] = [project_id]
    s = str(project_id).strip()
    if s.isdigit():
        vals.append(int(s))
    return vals


def norm_workflow_status(val: Any) -> str:
    """Lowercase, collapse spaces/hyphens so 'In Progress' matches in_progress-style checks."""
    if val is None:
        return ""
    s = str(val).strip().lower().replace("-", "_")
    return "_".join(s.split())


def row_is_pending_review(row: Dict[str, Any]) -> bool:
    """Pending = review_status 0/1 when numeric; else active workflow labels; else in-flight (pct < 100)."""
    rs = row.get("review_status")
    if rs is not None and str(rs).strip() != "":
        try:
            n = int(float(rs))
            if n in (0, 1):
                return True
            if n in (2, 3, 4, 5):
                return False
        except (TypeError, ValueError):
            pass

    st = row.get("status")
    sl = norm_workflow_status(st) if st is not None else ""

    if sl in ("close", "closed", "completed", "done", "approved", "rejected"):
        return False
    if sl in (
        "pending",
        "in_progress",
        "open",
        "create",
        "draft",
        "new",
        "not_started",
    ):
        return True
    if "pending" in sl:
        return True
    if "progress" in sl:
        return True
    if st is not None and st in ("pending", "in_progress", "open"):
        return True

    # Krion6d rows often omit review_status until answered; treat incomplete work as pending.
    try:
        pct = row.get("percent_complete")
        if pct is not None and float(pct) < 100:
            return True
    except (TypeError, ValueError):
        pass

    return False
