import json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from plan_vod_enrichment import build_report, safe_catalog_path


class PlanVodEnrichmentTests(unittest.TestCase):
    def _fixture(self, root):
        (root / "catalog/vod/index").mkdir(parents=True)
        sections = ("movies", "series", "anime", "doramas")
        manifest = {"categories": {s: {"index_path": f"catalog/vod/index/{s}.json"} for s in sections}}
        (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
        docs = {
            "movies": [
                {"id": "m-1", "title": "Filme com ID", "type": "movie", "tmdb_id": "123", "poster_url": ""},
                {"id": "m-2", "title": "Filme candidato", "type": "movie", "year": "2020", "poster_url": ""},
                {"id": "m-3", "title": "Sem ano", "type": "movie", "poster_url": "", "sources": [{"url": "https://secret.example/play"}]},
            ],
            "series": [], "anime": [], "doramas": [],
        }
        for section, records in docs.items():
            (root / f"catalog/vod/index/{section}.json").write_text(json.dumps(records), encoding="utf-8")
        return docs

    def test_report_is_read_only_and_redacts_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            report = build_report(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertEqual(before, after)
            self.assertTrue(report["read_only"])
            self.assertFalse(report["network_accessed"])
            self.assertFalse(report["catalog_mutated"])
            self.assertEqual(report["categories"]["movies"]["records_with_missing_metadata"], 3)
            self.assertEqual(report["categories"]["movies"]["match_status_counts"]["provider_id_present"], 1)
            self.assertEqual(report["categories"]["movies"]["match_status_counts"]["title_year_type_candidate"], 1)
            self.assertEqual(report["categories"]["movies"]["match_status_counts"]["manual_identity_review"], 1)
            self.assertNotIn("secret.example", serialized)
            self.assertNotIn("https://", serialized)

    def test_limits_examples_but_keeps_true_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            report = build_report(root, limit=1)
            section = report["categories"]["movies"]
            self.assertEqual(section["records_with_missing_metadata"], 3)
            self.assertEqual(section["examples_included"], 1)
            self.assertTrue(section["examples_truncated"])

    def test_rejects_index_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                safe_catalog_path(root, "../outside.json")

    def test_rejects_invalid_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            with self.assertRaises(ValueError):
                build_report(root, limit=0)


if __name__ == "__main__":
    unittest.main()
