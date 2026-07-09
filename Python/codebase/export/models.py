"""Export request models and validation helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


ExportFormat = Literal["csv", "xlsx", "json", "pdf"]

MAX_WIDGETS = 100
MAX_WIDGET_ROWS = 5000
MAX_SUMMARY_LEN = 12000


class ExportMetadata(BaseModel):
    project_code: Optional[str] = None
    module: Optional[str] = None
    date_range: Optional[str] = None
    data_source: Optional[str] = None
    query_text: Optional[str] = None
    summary_text: Optional[str] = None
    timestamp: Optional[str] = None

    @field_validator("summary_text")
    @classmethod
    def validate_summary_length(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > MAX_SUMMARY_LEN:
            return value[:MAX_SUMMARY_LEN]
        return value


class ExportWidget(BaseModel):
    widget_id: str
    title: str = "Untitled Widget"
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    chart_config: Optional[Dict[str, Any]] = None
    chart_image_base64: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_fallback(cls, value: str) -> str:
        value = (value or "").strip()
        return value or "Untitled Widget"


class DashboardExportSnapshot(BaseModel):
    metadata: ExportMetadata
    widgets: List[ExportWidget] = Field(default_factory=list)

    @field_validator("widgets")
    @classmethod
    def validate_widget_count(cls, widgets: List[ExportWidget]) -> List[ExportWidget]:
        if len(widgets) > MAX_WIDGETS:
            raise ValueError(f"Maximum {MAX_WIDGETS} widgets allowed per export")
        return widgets


class ExportRequest(BaseModel):
    format: ExportFormat
    snapshot: DashboardExportSnapshot

