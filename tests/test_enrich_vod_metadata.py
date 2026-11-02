import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

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
                       "overview": "A synopsis.", "imdb_id": "tt1234567", "genres": [{"id": 1, "name": "Drama"}]}
            with patch.object(enrich, "fetch_tmdb_details", return_value=(payload, "ok")) as fetch:
                report = enrich.build_patch(root, output, root / "cache.sqlite3", 10, "test-key", delay=0)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(report["summary"]["ready"], 1)
            self.assertFalse(report["catalog_mutated"])
            self.assertEqual(detail_path.read_bytes(), before)
            self.assertEqual(report["patches"][0]["proposed_fields"], {
                "poster_url": "/poster.jpg",
                "year": "2001", "genres": ["Drama"], "overview": "A synopsis.", "imdb_id": "tt1234567",
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

    def test_offset_skips_eligible_records_without_querying_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, {"id": "movie-test-film", "title": "A Test Film", "type": "movie",
                                 "year": None, "tmdb_id": "123", "poster_url": None, "genres": []})
            original_load_json = enrich.load_json
            detail_loads = []
            def tracked_load_json(path):
                if str(path).endswith("A-000.json"):
                    detail_loads.append(str(path))
                return original_load_json(path)
            with patch.object(enrich, "load_json", side_effect=tracked_load_json), \
                 patch.object(enrich, "fetch_tmdb_details") as fetch:
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3",
                                            10, "test-key", delay=0, offset=1)
            fetch.assert_not_called()
            self.assertEqual(detail_loads, [])
            self.assertEqual(report["records_examined"], 0)
            self.assertEqual(report["eligible_records_skipped"], 1)

    def test_offset_counts_complete_records_in_stable_tmdb_id_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = {"id": "movie-complete", "title": "Complete Film", "type": "movie",
                        "year": "2001", "tmdb_id": "123", "poster_url": "/poster.jpg",
                        "genres": ["Drama"], "overview": "Already complete."}
            self._fixture(root, complete)
            with patch.object(enrich, "fetch_tmdb_details") as fetch:
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3",
                                            10, "test-key", delay=0, offset=1)
            fetch.assert_not_called()
            self.assertEqual(report["eligible_records_skipped"], 1)
            self.assertEqual(report["records_examined"], 0)

    def test_requires_api_key_before_reading_or_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "SUPABASE_ANON_KEY is required"):
                enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3", 10, "", delay=0)
            self.assertFalse((root / "patch.json").exists())
            self.assertFalse((root / "cache.sqlite3").exists())


    def test_missing_index_tmdb_id_skips_detail_shard_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, {"id": "movie-test-film", "title": "A Test Film", "type": "movie",
                                 "year": None, "tmdb_id": "123", "poster_url": None, "genres": []})
            index_path = root / "catalog/vod/index/movies.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            del index[0]["tmdb_id"]
            index_path.write_text(json.dumps(index), encoding="utf-8")
            original_load_json = enrich.load_json
            detail_loads = []
            def tracked_load_json(path):
                if str(path).endswith("A-000.json"):
                    detail_loads.append(str(path))
                return original_load_json(path)
            with patch.object(enrich, "load_json", side_effect=tracked_load_json), \
                 patch.object(enrich, "fetch_tmdb_details") as fetch:
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3",
                                            10, "test-key", delay=0, offset=0)
            fetch.assert_not_called()
            self.assertEqual(detail_loads, [])
            self.assertEqual(report["records_examined"], 0)
            self.assertEqual(report["summary"]["no_tmdb_id"], 1)

    def test_index_detail_tmdb_id_mismatch_is_held_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, {"id": "movie-test-film", "title": "A Test Film", "type": "movie",
                                 "year": None, "tmdb_id": "456", "poster_url": None, "genres": []})
            index_path = root / "catalog/vod/index/movies.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index[0]["tmdb_id"] = "123"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            with patch.object(enrich, "fetch_tmdb_details") as fetch:
                report = enrich.build_patch(root, root / "patch.json", root / "cache.sqlite3",
                                            10, "test-key", delay=0, offset=0)
            fetch.assert_not_called()
            self.assertEqual(report["summary"]["identity_review"], 1)
            self.assertEqual(report["patches"], [])


    def test_proxy_wrapped_tmdb_not_found_is_terminal_not_retryable_500(self):
        body = json.dumps({
            "success": False,
            "error": "The resource you requested could not be found.",
        }).encode("utf-8")
        error = HTTPError(
            "https://catalog.example/functions/v1/cinehub-catalog",
            500,
            "Internal Server Error",
            None,
            io.BytesIO(body),
        )
        with patch.object(enrich, "urlopen", side_effect=error) as request:
            payload, status = enrich.fetch_tmdb_details(
                "movie", "999999", "test-key", retries=3, delay=0,
                function_url="https://catalog.example/functions/v1/cinehub-catalog",
            )
        self.assertIsNone(payload)
        self.assertEqual(status, "not_found")
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
