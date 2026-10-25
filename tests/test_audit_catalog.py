import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_catalog import audit


class ReadOnlyAuditTests(unittest.TestCase):
    def test_audit_counts_categories_and_detects_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": [{"id": "ch-a", "name": "A"}]},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": [{"id": "r-a", "name": "A"}]},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    "movies": {"count": 2, "index_path": "catalog/vod/index/movies.json"},
                    "series": {"count": 0, "index_path": "catalog/vod/index/series.json"},
                    "anime": {"count": 0, "index_path": "catalog/vod/index/anime.json"},
                    "doramas": {"count": 0, "index_path": "catalog/vod/index/doramas.json"}}},
                "catalog/vod/index/movies.json": [{"id": "m-1"}, {"id": "m-2"}],
                "catalog/vod/index/series.json": [],
                "catalog/vod/index/anime.json": [],
                "catalog/vod/index/doramas.json": [],
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {"A": "A"}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {"one": {"status": "healthy"}}},
                "catalog/epg/xmltv-channels.json": {"sources": {"one": {"channels": [{"id": "x"}]}}},
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["counts"]["vod_total"], 2)
            self.assertEqual(result["counts"]["channels"], 1)
            self.assertEqual(result["counts"]["radios"], 1)
            self.assertEqual(result["counts"]["epg_sources_healthy"], 1)
            self.assertFalse(any(x["code"] == "manifest_count_mismatch" for x in result["findings"]))

    def test_audit_is_read_only_and_reports_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": [{"id": "same"}, {"id": "same"}]},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": []},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    name: {"count": 0, "index_path": f"catalog/vod/index/{name}.json"}
                    for name in ("movies", "series", "anime", "doramas")}},
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {}},
                "catalog/epg/xmltv-channels.json": {"sources": {}},
            }
            for name in ("movies", "series", "anime", "doramas"):
                files[f"catalog/vod/index/{name}.json"] = []
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = audit(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertTrue(any(x["code"] == "duplicate_ids" for x in result["findings"]))


if __name__ == "__main__":
    unittest.main()
