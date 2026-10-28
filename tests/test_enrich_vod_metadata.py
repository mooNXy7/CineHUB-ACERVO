import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import enrich_vod_metadata as enrich


class ReviewOnlyTMDBPatchTests(unittest.TestCase):
    def _fixture(self, root: Path, record: dict):
        (root / "catalog/vod/index").mkdir(parents=True)
        (root / "catalog/vod/details/movies").mkdir(parents=True)
        manifest = {"schema_version": 1, "categories": {"movies": {"count": 1, "index_path": "catalog/vod/index/movies.json"}}}
        (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "catalog/vod/index/movies.json").write_text(json.dumps([{
            "id": record["id"], "title": record["title"], "type": "movie",
            "detail_path": "catalog/vod/details/movies/A-000.json", "tmdb_id": record.get("tmdb_id"),
        }]), encoding="utf-8")
        detail_path = root / "catalog/vod/details/movies/A-000.json"
        detail_path.write_text(json.dumps([record]), encoding="utf-8")
        return detail_path

    def test_builds_patch_from_exact_id_and_title_without_mutating_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"id": "movie-test-film", "title": "A Test Film (2001)", "type": "movie",
                      "year": None, "tmdb_id": "123", "poster_url": None, "genres": [],
                      "sources": [{"url": "https://media.example/keep.m3u8"}]}
            detail_path = self._fixture(root, record)
            before = detail_path.read_bytes()
            output = root / "reports/patch.json"
            payload = {"id": 123, "title": "A Test Film", "original_title": "A Test Film",
                       "release_date": "2001-05-01", "poster_path": "/poster.jpg",
                       "genres": [{"id": 1, "name": "Drama"}]}
            with patch.object(enrich, "fetch_tmdb_details", return_value=(payload, "ok")) as fetch:
                report = enrich.build_patch(root, output, root / "cache.sqlite3", 10, "test-key", delay=0)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(report["summary"]["ready"], 1)
            self.assertFalse(report["catalog_mutated"])
            self.assertEqual(detail_path.read_bytes(), before)
            self.assertEqual(report["patches"][0]["proposed_fields"], {
                "poster_url": "https://image.tmdb.org/t/p/w500/poster.jpg",
                "year": "2001", "genres": ["Drama"],
            })
            self.assertNotIn("test-key", output.read_text(encoding="utf-8"))

    def test_title_mismatch_is_held_for_manual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"id": "movie-test-film", "title": "A Test Film", "type": "movie",
                      "year": None, "tmdb_id": "123", "poster_url": None, "genres": []}
            self._fixture(root, record)
            payload = {"id": 123, "title": "Entirely Different Film", "original_title": "Entirely Different Film",
                       "release_date": "2001-01-01", "poster_path": "/poster.jpg", "genres": [{"name": "Drama"}]}
            with patch.object(enrich, "fetch_tmdb_details", return_value=(payload, "ok")):
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3", 10, "test-key", delay=0)
            self.assertEqual(report["summary"]["identity_review"], 1)
            self.assertEqual(report["patches"], [])

    def test_conflicting_year_hint_is_held_for_manual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"id": "movie-test-film", "title": "A Test Film (2001)", "type": "movie",
                      "year": None, "tmdb_id": "123", "poster_url": None, "genres": []}
            self._fixture(root, record)
            payload = {"id": 123, "title": "A Test Film", "original_title": "A Test Film",
                       "release_date": "2002-01-01", "poster_path": "/poster.jpg", "genres": [{"name": "Drama"}]}
            with patch.object(enrich, "fetch_tmdb_details", return_value=(payload, "ok")):
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3", 10, "test-key", delay=0)
            self.assertEqual(report["summary"]["identity_review"], 1)
            self.assertEqual(report["patches"], [])

    def test_requires_api_key_before_reading_or_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "TMDB_API_KEY is required"):
                enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3", 10, "", delay=0)
            self.assertFalse((root / "patch.json").exists())
            self.assertFalse((root / "cache.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
