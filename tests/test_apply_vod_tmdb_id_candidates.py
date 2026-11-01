import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_vod_tmdb_id_candidates as applier


class ApplyTMDBIDCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "catalog/vod/index").mkdir(parents=True)
        (self.root / "catalog/vod/details/movies").mkdir(parents=True)
        manifest = {"categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}}
        (self.root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = [{
            "id": "movie-a-2020", "title": "A Movie (2020)", "year": "2020",
            "tmdb_id": "", "detail_path": "catalog/vod/details/movies/A-001.json",
        }]
        detail = [{
            "id": "movie-a-2020", "title": "A Movie (2020)", "year": "2020",
            "tmdb_id": "", "sources": [{"url": "https://stream.example/a.m3u8"}],
            "poster_url": "/posters/a.jpg",
        }]
        (self.root / "catalog/vod/index/movies.json").write_text(json.dumps(index), encoding="utf-8")
        (self.root / "catalog/vod/details/movies/A-001.json").write_text(json.dumps(detail), encoding="utf-8")
        self.report_path = self.root / "candidates.json"
        self.write_report([{
            "section": "movies", "catalog_id": "movie-a-2020",
            "catalog_title": "A Movie (2020)", "catalog_year": "2020",
            "media_type": "movie", "status": "exact_title_review",
            "candidates": [{
                "tmdb_id_candidate": "12345", "matched_title": "A Movie",
                "year": "2020", "poster_available": True, "overview_available": True,
            }],
        }])

    def tearDown(self):
        self.tmp.cleanup()

    def write_report(self, candidates):
        self.report_path.write_text(json.dumps({
            "report_type": "review_only_tmdb_id_candidates",
            "read_only": True, "catalog_mutated": False, "candidates": candidates,
        }), encoding="utf-8")

    def read_catalog(self):
        index = json.loads((self.root / "catalog/vod/index/movies.json").read_text(encoding="utf-8"))
        detail = json.loads((self.root / "catalog/vod/details/movies/A-001.json").read_text(encoding="utf-8"))
        return index[0], detail[0]

    def test_applies_unique_exact_title_and_year_and_preserves_sources(self):
        output = self.root / "summary.json"
        summary = applier.apply_reports(self.root, [self.report_path], output)
        index, detail = self.read_catalog()
        self.assertEqual(index["tmdb_id"], "12345")
        self.assertEqual(detail["tmdb_id"], "12345")
        self.assertEqual(detail["sources"], [{"url": "https://stream.example/a.m3u8"}])
        self.assertEqual(detail["poster_url"], "/posters/a.jpg")
        self.assertEqual(summary["counts"]["ids_assigned"], 1)

    def test_skips_multiple_tmdb_candidates(self):
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        report["candidates"][0]["candidates"].append({
            "tmdb_id_candidate": "99999", "matched_title": "A Movie", "year": "2020",
        })
        self.report_path.write_text(json.dumps(report), encoding="utf-8")
        summary = applier.apply_reports(self.root, [self.report_path], self.root / "summary.json")
        index, detail = self.read_catalog()
        self.assertEqual(index["tmdb_id"], "")
        self.assertEqual(detail["tmdb_id"], "")
        self.assertEqual(summary["counts"]["skipped_multiple_candidates"], 1)

    def test_skips_year_mismatch(self):
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        report["candidates"][0]["candidates"][0]["year"] = "2021"
        self.report_path.write_text(json.dumps(report), encoding="utf-8")
        summary = applier.apply_reports(self.root, [self.report_path], self.root / "summary.json")
        index, _ = self.read_catalog()
        self.assertEqual(index["tmdb_id"], "")
        self.assertEqual(summary["counts"]["skipped_missing_or_conflicting_year"], 1)

    def test_skips_tmdb_id_already_used_by_another_record(self):
        index_path = self.root / "catalog/vod/index/movies.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index.append({
            "id": "movie-other", "title": "Other Movie (2020)", "year": "2020",
            "tmdb_id": "12345", "detail_path": "catalog/vod/details/movies/A-001.json",
        })
        index_path.write_text(json.dumps(index), encoding="utf-8")
        summary = applier.apply_reports(self.root, [self.report_path], self.root / "summary.json")
        self.assertEqual(summary["counts"]["skipped_tmdb_id_already_used"], 1)
        self.assertEqual(json.loads(index_path.read_text(encoding="utf-8"))[0]["tmdb_id"], "")


if __name__ == "__main__":
    unittest.main()
