"""JSON export builder."""

import json

from export.models import DashboardExportSnapshot


def build_json(snapshot: DashboardExportSnapshot) -> bytes:
    payload = snapshot.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

