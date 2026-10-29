import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_vod_metadata_patch as apply_patch


class ApplyVODMetadataPatchTests(unittest.TestCase):
    def _fixture(self, root, detail_record, index_record=None):
        (root / "catalog/vod/index").mkdir(parents=True)
        (root / "catalog/vod/details/movies").mkdir(parents=True)
        if index_record is None:
            index_record = {k: v for k, v in detail_record.items() if k in
                            {"id", "title", "type", "tmdb_id", "year", "poster_url", "genres", "overview"}}
            index_record["detail_path"] = "catalog/vod/details/movies/A-000.json"
        manifest = {"schema_version": 1, "categories": {"movies": {
            "count": 1, "index_path": "catalog/vod/index/movies.json"}}}
        (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "catalog/vod/index/movies.json").write_text(json.dumps([index_record]), encoding="utf-8")
        (root / "catalog/vod/details/movies/A-000.json").write_text(json.dumps([detail_record]), encoding="utf-8")
        return root / "catalog/vod/index/movies.json", root / "catalog/vod/details/movies/A-000.json"

    def test_applies_only_missing_metadata_to_index_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"id": "movie-1", "title": "A Test Film (2001)", "type": "movie",
                      "tmdb_id": "123", "year": None, "poster_url": None, "genres": [], "overview": None,
                      "sources": [{"url": "https://example.test/keep.m3u8"}]}
            index_path, detail_path = self._fixture(root, record)
            patch = {"report_type": "review_only_tmdb_metadata_patch", "catalog_mutated": False,
                     "patches": [{"section": "movies", "id": "movie-1", "title": "A Test Film (2001)",
                                  "matched_title": "A Test Film", "tmdb_id": "123",
                                  "confidence": "exact_provider_id_and_title",
                                  "proposed_fields": {"year": "2001", "poster_url": "/poster.jpg",
                                                      "genres": ["Drama"], "overview": "Synopsis"}}]}
            patch_path = root / "patch.json"
            patch_path.write_text(json.dumps(patch), encoding="utf-8")
            summary = apply_patch.apply_patch(root, patch_path, root / "summary.json")
            index = json.loads(index_path.read_text(encoding="utf-8"))[0]
            detail = json.loads(detail_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(summary["counts"]["fields_updated"], 4)
            self.assertEqual(index["overview"], "Synopsis")
            self.assertEqual(detail["poster_url"], "/poster.jpg")
            self.assertEqual(detail["sources"], record["sources"])
            self.assertTrue(summary["catalog_mutated"])

    def test_refuses_title_mismatch_without_mutating_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"id": "movie-1", "title": "A Test Film (2001)", "type": "movie",
                      "tmdb_id": "123", "year": None, "poster_url": None, "genres": [], "overview": None}
            index_path, detail_path = self._fixture(root, record)
            before = (index_path.read_bytes(), detail_path.read_bytes())
            patch = {"report_type": "review_only_tmdb_metadata_patch", "catalog_mutated": False,
                     "patches": [{"section": "movies", "id": "movie-1", "title": "A Test Film (2001)",
                                  "matched_title": "Different Film", "tmdb_id": "123",
                                  "confidence": "exact_provider_id_and_title",
                                  "proposed_fields": {"year": "2001"}}]}
            patch_path = root / "patch.json"
            patch_path.write_text(json.dumps(patch), encoding="utf-8")
            summary = apply_patch.apply_patch(root, patch_path, root / "summary.json")
            self.assertEqual(summary["counts"]["identity_rejected"], 1)
            self.assertEqual((index_path.read_bytes(), detail_path.read_bytes()), before)
            self.assertFalse(summary["catalog_mutated"])


if __name__ == "__main__":
    unittest.main()
