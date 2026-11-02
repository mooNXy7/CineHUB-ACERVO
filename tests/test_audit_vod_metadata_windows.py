import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_vod_metadata_windows import build_report


class VODMetadataWindowAuditTests(unittest.TestCase):
    def test_uses_stable_numeric_tmdb_offset_and_checks_detail_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog/vod/index").mkdir(parents=True)
            (root / "catalog/vod/details/movies").mkdir(parents=True)
            (root / "catalog/vod/details/series").mkdir(parents=True)
            manifest = {
                "categories": {
                    "movies": {"index_path": "catalog/vod/index/movies.json"},
                    "series": {"index_path": "catalog/vod/index/series.json"},
                }
            }
            (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
            movies = [
                {"id": "m1", "tmdb_id": "101", "detail_path": "catalog/vod/details/movies/a.json"},
                {"id": "m2", "tmdb_id": "102", "detail_path": "catalog/vod/details/movies/a.json"},
                {"id": "m3", "tmdb_id": "103", "detail_path": "catalog/vod/details/movies/b.json"},
            ]
            series = [
                {"id": "s1", "tmdb_id": "201", "detail_path": "catalog/vod/details/series/s.json"},
            ]
            (root / "catalog/vod/index/movies.json").write_text(json.dumps(movies), encoding="utf-8")
            (root / "catalog/vod/index/series.json").write_text(json.dumps(series), encoding="utf-8")
            (root / "catalog/vod/details/movies/a.json").write_text(json.dumps([
                {"id": "m1", "tmdb_id": "101", "poster_url": None, "year": "2020", "genres": ["Drama"], "overview": "ok"},
                {"id": "m2", "tmdb_id": "102", "poster_url": "/p.jpg", "year": "2021", "genres": ["Drama"], "overview": "ok"},
            ]), encoding="utf-8")
            (root / "catalog/vod/details/movies/b.json").write_text(json.dumps([
                {"id": "m3", "tmdb_id": "999", "poster_url": "/p.jpg", "year": "2022", "genres": ["Drama"], "overview": "ok"},
            ]), encoding="utf-8")
            (root / "catalog/vod/details/series/s.json").write_text(json.dumps([
                {"id": "s1", "tmdb_id": "201", "poster_url": "/s.jpg", "year": "2022", "genres": [], "overview": "ok"},
            ]), encoding="utf-8")
            report = build_report(root, window_size=2)
        self.assertFalse(report["catalog_mutated"])
        self.assertFalse(report["network_accessed"])
        self.assertEqual(report["summary"]["eligible_records"], 4)
        self.assertEqual(report["summary"]["records_with_missing_metadata"], 2)
        self.assertEqual(report["summary"]["complete_records"], 1)
        self.assertEqual(report["summary"]["identity_mismatches"], 1)
        self.assertEqual([w["offset"] for w in report["windows"]], [0, 2])
        self.assertEqual(report["windows"][0]["missing_field_counts"]["poster_url"], 1)
        self.assertEqual(report["windows"][1]["missing_field_counts"]["genres"], 1)


if __name__ == "__main__":
    unittest.main()
