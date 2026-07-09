"""Shared metadata rows for PDF, XLSX, and CSV exports (no Date Range — use Timestamp)."""

from typing import List, Tuple

from export.models import DashboardExportSnapshot


def build_export_metadata_rows(
    snapshot: DashboardExportSnapshot,
    *,
    include_widget_count: bool = False,
) -> List[Tuple[str, str]]:
    """Same fields and order for all export formats."""
    m = snapshot.metadata
    rows: List[Tuple[str, str]] = [
        ("Project", m.project_code or "AllProjects"),
        ("Module", m.module or "AllModules"),
    ]
    if m.data_source:
        rows.append(("Data Source", m.data_source))
    if m.timestamp:
        rows.append(("Timestamp", m.timestamp))
    if m.query_text:
        rows.append(("Query", m.query_text))
    if m.summary_text:
        rows.append(("Summary", m.summary_text))
    if include_widget_count:
        rows.append(("Widget Count", str(len(snapshot.widgets))))
    return rows
