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



    def test_audit_reports_catalog_quality_without_mutating_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": [
                    {"id": "ch-a", "name": "A", "logo_url": "http://example.com/logo.png",
                     "sources": [{"url": "https://example.com/live"}]}
                ]},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": [
                    {"id": "r-a", "name": "Rock", "stream_url": "https://radio.example/stream%22%3E%3C/audio%3E"}
                ]},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    name: {"count": 2 if name == "movies" else 0,
                           "index_path": f"catalog/vod/index/{name}.json"}
                    for name in ("movies", "series", "anime", "doramas")}},
                "catalog/vod/index/movies.json": [
                    {"id": "m-1", "title": "Example Movie"},
                    {"id": "m-2", "title": "Example Movie"}
                ],
                "catalog/vod/index/series.json": [],
                "catalog/vod/index/anime.json": [],
                "catalog/vod/index/doramas.json": [],
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {}},
                "catalog/epg/xmltv-channels.json": {"sources": {}},
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = audit(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(result["quality"]["http_url_references"], 1)
            self.assertEqual(result["quality"]["suspicious_url_references"], 1)
            self.assertEqual(result["quality"]["vod_duplicate_normalized_titles"], 1)
            self.assertEqual(result["quality"]["vod_missing_poster"], 2)

    def test_audit_rejects_detail_paths_that_escape_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": []},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": []},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    name: {"count": 1 if name == "movies" else 0,
                           "index_path": f"catalog/vod/index/{name}.json"}
                    for name in ("movies", "series", "anime", "doramas")}},
                "catalog/vod/index/movies.json": [{"id": "m-1", "detail_path": "../../outside.json"}],
                "catalog/vod/index/series.json": [],
                "catalog/vod/index/anime.json": [],
                "catalog/vod/index/doramas.json": [],
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {}},
                "catalog/epg/xmltv-channels.json": {"sources": {}},
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            result = audit(root)
            self.assertTrue(any(x["code"] == "detail_path_outside_root" for x in result["findings"]))


    def test_audit_exposes_duplicate_title_groups_for_safe_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": []},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": []},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    name: {"count": 2 if name == "movies" else 0,
                           "index_path": f"catalog/vod/index/{name}.json"}
                    for name in ("movies", "series", "anime", "doramas")}},
                "catalog/vod/index/movies.json": [
                    {"id": "m-1", "title": "Example Film (2020)", "year": "2020", "tmdb_id": "101"},
                    {"id": "m-2", "title": "Example Film", "year": "2020", "tmdb_id": "202"}
                ],
                "catalog/vod/index/series.json": [],
                "catalog/vod/index/anime.json": [],
                "catalog/vod/index/doramas.json": [],
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {}},
                "catalog/epg/xmltv-channels.json": {"sources": {}},
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            result = audit(root)
            groups = result["duplicate_title_groups"]
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["normalized_title"], "example film")
            self.assertFalse(groups[0]["same_tmdb_id"])
            self.assertEqual({x["tmdb_id"] for x in groups[0]["records"]}, {"101", "202"})


    def test_audit_separates_html_epg_page_health_from_source_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {"schema_version": 1, "channels": []},
                "catalog/radios/radios.json": {"schema_version": 1, "radios": []},
                "catalog/vod/index.json": {"schema_version": 1, "categories": {
                    name: {"count": 0, "index_path": f"catalog/vod/index/{name}.json"}
                    for name in ("movies", "series", "anime", "doramas")}},
                "catalog/vod/index/movies.json": [],
                "catalog/vod/index/series.json": [],
                "catalog/vod/index/anime.json": [],
                "catalog/vod/index/doramas.json": [],
                "sources/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/sources.json": {"schema_version": 1, "sources": []},
                "catalog/epg/channel-map.json": {"meuguia_codes": {}, "guiadetv_slugs": {}, "xmltv_aliases": {}},
                "catalog/epg/health.json": {"sources": {"guiadetv-br": {"status": "healthy"}}},
                "catalog/epg/xmltv-channels.json": {"sources": {}},
                "catalog/epg/html-programmes.json": {
                    "schema_version": 1,
                    "timezone": "America/Sao_Paulo",
                    "health": {
                        "Canal A": {"source_id": "meuguia-br", "status": "healthy", "programme_count": 3},
                        "Canal B": {"source_id": "guia-de-tv-br", "status": "unavailable",
                                    "error": "no_programmes", "programme_count": 0},
                    },
                    "programmes": {
                        "Canal A": {"source_id": "meuguia-br", "programmes": [{"title": "Jornal"}]}
                    },
                },
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["counts"]["epg_sources_healthy"], 1)
            self.assertEqual(result["counts"]["html_epg_channels_healthy"], 1)
            self.assertEqual(result["counts"]["html_epg_channels_unavailable"], 1)
            self.assertEqual(result["counts"]["html_epg_channels_with_programmes"], 1)
            self.assertEqual(result["counts"]["html_epg_channels_without_programmes"], 1)
            self.assertEqual(result["html_epg_unavailable_examples"][0]["channel"], "Canal B")


if __name__ == "__main__":
    unittest.main()
