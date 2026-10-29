import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import suggest_vod_tmdb_matches as suggest


class SuggestVODTMDBMatchesTests(unittest.TestCase):
    def fixture(self, root, record):
        (root / "catalog/vod/index").mkdir(parents=True)
        (root / "catalog/vod/details/movies").mkdir(parents=True)
        manifest = {"schema_version": 1, "categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}}
        (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "catalog/vod/index/movies.json").write_text(json.dumps([{
            "id": record["id"], "title": record["title"], "type": "movie",
            "detail_path": "catalog/vod/details/movies/part.json"
        }]), encoding="utf-8")
        detail = root / "catalog/vod/details/movies/part.json"
        detail.write_text(json.dumps([record]), encoding="utf-8")
        return detail

    def test_emits_exact_title_suggestion_without_mutating_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detail = self.fixture(root, {"id": "m-1", "title": "Filme Teste (2001)", "year": None, "tmdb_id": None})
            before = detail.read_bytes()
            result = {"id": 123, "title": "Filme Teste", "original_title": "Test Movie",
                      "release_date": "2001-02-03", "poster_path": "/p.jpg", "overview": "x"}
            with patch.object(suggest, "search_catalog_proxy", return_value=([result], "ok")) as proxy:
                report = suggest.build_report(root, root / "reports/out.json",
                    "https://project.supabase.co/functions/v1/cinehub-catalog", "public-key",
                    limit=1, delay=0)
            proxy.assert_called_once()
            self.assertEqual(proxy.call_args.args[2:4], ("movie", "Filme Teste"))
            self.assertEqual(report["summary"]["exact_title_candidates"], 1)
            self.assertEqual(report["candidates"][0]["candidates"][0]["tmdb_id_candidate"], "123")
            self.assertFalse(report["catalog_mutated"])
            self.assertEqual(detail.read_bytes(), before)
            self.assertNotIn("public-key", (root / "reports/out.json").read_text(encoding="utf-8"))

    def test_rejects_year_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, {"id": "m-1", "title": "Filme Teste (2001)", "year": None})
            result = {"id": 123, "title": "Filme Teste", "release_date": "2002-02-03"}
            with patch.object(suggest, "search_catalog_proxy", return_value=([result], "ok")):
                report = suggest.build_report(root, root / "reports/out.json",
                    "https://project.supabase.co/functions/v1/cinehub-catalog", "",
                    limit=1, delay=0)
            self.assertEqual(report["summary"]["year_conflict"], 1)
            self.assertEqual(report["candidates"], [])

    def test_offset_skips_eligible_records_without_searching_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, {"id": "m-1", "title": "Filme Teste", "year": None})
            with patch.object(suggest, "search_catalog_proxy") as proxy:
                report = suggest.build_report(root, root / "out.json",
                    "https://project.supabase.co/functions/v1/cinehub-catalog", "public-key",
                    limit=10, delay=0, offset=1)
            proxy.assert_not_called()
            self.assertEqual(report["records_examined"], 0)
            self.assertEqual(report["eligible_records_skipped"], 1)

    def test_requires_https_url_and_valid_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                suggest.build_report(root, root / "out.json", "http://not-secure", "", limit=1)
            with self.assertRaises(ValueError):
                suggest.build_report(root, root / "out.json", "https://project.supabase.co/functions/v1/cinehub-catalog", "", limit=501)


if __name__ == "__main__":
    unittest.main()
