"""Tests for Krion6d document search, loader normalization, and query_documents filters."""
import pandas as pd
import pytest

from agents.data_analyst_agent import DataAnalystAgent
from data_layer.krion6d_client import (
    Krion6dClient,
    _extension_from_text,
    _is_document_like_row,
    _normalize_ext_fragment,
)
from data_layer.krion6d_loader import Krion6dDataLoader
from data_layer.query_engine import QueryEngine


class TestParseSearchResponse:
    def test_dict_data_key(self):
        raw = {"data": [{"id": 1, "name": "x.pdf"}]}
        out = Krion6dClient._parse_search_response(raw)
        assert len(out) == 1
        assert out[0]["name"] == "x.pdf"

    def test_raw_list(self):
        raw = [{"a": 1}, {"b": 2}]
        out = Krion6dClient._parse_search_response(raw)
        assert len(out) == 2

    def test_malformed_non_dict_items_skipped(self):
        raw = {"data": [{"ok": True}, "skip", 3]}
        out = Krion6dClient._parse_search_response(raw)
        assert len(out) == 1


class TestDocumentLikeRows:
    def test_excludes_folder(self):
        assert not _is_document_like_row({"isFolder": True, "name": "a.pdf"})
        assert not _is_document_like_row({"is_folder": True, "name": "a.pdf"})

    def test_type_document(self):
        assert _is_document_like_row({"type": "document", "isFolder": False})

    def test_supported_extension(self):
        assert _is_document_like_row({"name": "plan.rvt", "isFolder": False})
        assert _is_document_like_row({"url": "https://x.com/a.dwg", "isFolder": False})

    def test_unknown_extension_excluded_unless_type_document(self):
        assert not _is_document_like_row({"name": "weird.zzz", "isFolder": False})


class TestExtensionHelpers:
    def test_normalize(self):
        assert _normalize_ext_fragment("PDF") == ".pdf"
        assert _normalize_ext_fragment(".RVT") == ".rvt"

    def test_from_path_or_url(self):
        assert _extension_from_text("C:/p/x.rvt") == ".rvt"
        assert _extension_from_text("https://h/a.pdf?x=1") == ".pdf"


class TestDataAnalystDocumentFilters:
    def test_project_id_filter_values(self):
        v = DataAnalystAgent._project_id_filter_values("96")
        assert "96" in v and 96 in v

    def test_project_id_non_numeric(self):
        v = DataAnalystAgent._project_id_filter_values("abc-1")
        assert v == ["abc-1"]

    def test_normalize_file_extension_filter(self):
        assert DataAnalystAgent._normalize_file_extension_filter("pdf") == ".pdf"
        assert DataAnalystAgent._normalize_file_extension_filter("RVT") == ".rvt"
        assert DataAnalystAgent._normalize_file_extension_filter(".pdf") == ".pdf"
        assert DataAnalystAgent._normalize_file_extension_filter(None) is None


class TestFinalizeDocumentsDataframe:
    def test_infer_extension_from_title(self):
        df = pd.DataFrame([{"title": "Sheet.pdf"}])
        out = Krion6dDataLoader._finalize_documents_dataframe(df)
        assert out["file_extension"].iloc[0] == ".pdf"

    def test_infer_from_url(self):
        df = pd.DataFrame([{"title": "n", "file_url": "http://x/f.rvt"}])
        out = Krion6dDataLoader._finalize_documents_dataframe(df)
        assert out["file_extension"].iloc[0] == ".rvt"

    def test_size_bytes_to_mb(self):
        df = pd.DataFrame([{"title": "a.pdf", "size_mb": 2_097_152}])  # 2 MiB in bytes
        out = Krion6dDataLoader._finalize_documents_dataframe(df)
        assert abs(out["size_mb"].iloc[0] - 2.0) < 0.01


class TestQueryEngineDocumentsProjectId:
    def test_string_or_int_project_id(self):
        df = pd.DataFrame(
            [
                {"document_id": "1", "project_id": 96, "title": "a", "file_extension": ".pdf"},
                {"document_id": "2", "project_id": "96", "title": "b", "file_extension": ".rvt"},
                {"document_id": "3", "project_id": 97, "title": "c", "file_extension": ".pdf"},
            ]
        )
        qe = QueryEngine({"documents": df})
        r1 = qe.query("documents", {"project_id": ["96", 96]}, limit=50)
        assert len(r1) == 2
        r2 = qe.query("documents", {"file_extension": ".pdf", "project_id": [96, "96"]}, limit=50)
        assert len(r2) == 1
        assert r2.iloc[0]["title"] == "a"


@pytest.mark.asyncio
async def test_list_documents_mock_request():
    client = Krion6dClient("test-token")

    async def fake_request(method, path, json_body=None, params=None):
        assert json_body.get("limit") == -1
        assert "projectId" in json_body
        return {
            "data": [
                {"name": "a.pdf", "type": "document", "isFolder": False},
                {"name": "dir", "isFolder": True},
                {"name": "b.rvt", "isFolder": False},
            ]
        }

    client._request = fake_request  # type: ignore[method-assign]
    rows = await client.list_documents("96")
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"a.pdf", "b.rvt"}


@pytest.mark.asyncio
async def test_list_documents_request_raises_returns_empty():
    client = Krion6dClient("test-token")

    async def boom(method, path, json_body=None, params=None):
        raise ConnectionError("network")

    client._request = boom  # type: ignore[method-assign]
    rows = await client.list_documents("1")
    assert rows == []
