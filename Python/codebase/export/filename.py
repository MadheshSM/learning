"""Filename helpers for dashboard export files."""

from datetime import datetime
import re


def _sanitize(segment: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", segment or "")
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned or "Unknown"


def build_export_filename(project_code: str, module: str, date_range: str, fmt: str) -> str:
    project_part = _sanitize(project_code or "AllProjects")
    module_part = _sanitize(module or "AllModules")
    date_part = _sanitize(date_range or "AllTime")
    fmt_lower = (fmt or "csv").lower()
    return f"{project_part}_{module_part}_{date_part}_{fmt_lower}.{fmt_lower}"


def build_xlsx_filename(project_code: str, business_module: str, timestamp: str) -> str:
    """Legacy helper kept for backwards-compatibility (xlsx only)."""
    project_part = _sanitize(project_code or "AllProjects")
    module_part = _sanitize(business_module or "general")
    stamp = _sanitize(timestamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    return f"{project_part}_{module_part}_{stamp}.xlsx"


def build_timestamped_export_filename(project_code: str, timestamp: str, fmt: str) -> str:
    """Build timestamped export filename: ProjectCode_YYYYMMDD_HHMMSS.ext"""
    project_part = _sanitize(project_code or "AllProjects")
    stamp = _sanitize(timestamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    ext = (fmt or "csv").lower()
    return f"{project_part}_{stamp}.{ext}"

