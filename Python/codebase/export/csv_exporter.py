"""CSV export builder."""

from typing import List

from export.metadata_rows import build_export_metadata_rows
from export.models import DashboardExportSnapshot, MAX_WIDGET_ROWS


def _csv_escape(value: object) -> str:
    text = "" if value is None else str(value)
    if "," in text or '"' in text or "\n" in text:
        return '"' + text.replace('"', '""') + '"'
    return text


def _table_to_csv(headers: List[object], rows: List[List[object]]) -> str:
    capped_rows = rows[:MAX_WIDGET_ROWS]
    lines = [",".join(_csv_escape(h) for h in headers)]
    lines.extend(",".join(_csv_escape(cell) for cell in row) for row in capped_rows)
    if len(rows) > len(capped_rows):
        lines.append(f'"TRUNCATED","Showing first {len(capped_rows)} rows"')
    return "\n".join(lines)


def build_csv(snapshot: DashboardExportSnapshot) -> bytes:
    meta_rows = build_export_metadata_rows(snapshot, include_widget_count=True)
    meta_header = "Key,Value"
    meta_body = "\n".join(
        f"{_csv_escape(k)},{_csv_escape(v)}" for k, v in meta_rows
    )
    prelude = meta_header + "\n" + meta_body + "\n\n"

    sections: List[str] = []
    for widget in snapshot.widgets:
        data = widget.data or {}
        section = None

        if widget.type == "table":
            section = _table_to_csv(data.get("headers", []), data.get("rows", []))
        elif data.get("labels") and data.get("datasets"):
            labels = data.get("labels", [])
            datasets = data.get("datasets", [])
            header = ["Label", *[ds.get("label", "Value") for ds in datasets]]
            rows = []
            for i, label in enumerate(labels[:MAX_WIDGET_ROWS]):
                row = [label]
                for ds in datasets:
                    values = ds.get("data", [])
                    row.append(values[i] if i < len(values) else "")
                rows.append(row)
            section = _table_to_csv(header, rows)
        elif widget.type == "kpi":
            rows = [["Metric", "Value"]]
            rows.append([widget.title, data.get("value", "")])
            if data.get("unit"):
                rows.append(["Unit", data.get("unit")])
            if data.get("change"):
                rows.append(["Change", data.get("change")])
            section = _table_to_csv(rows[0], rows[1:])

        if section:
            sections.append(f"# {widget.title}\n{section}")

    if not sections:
        sections.append("# No tabular widget data available")

    return ("\ufeff" + prelude + "\n\n".join(sections)).encode("utf-8")

