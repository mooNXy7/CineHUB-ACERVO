import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import summarize_reference_import_preview as preview


def make_catalog(root: Path, movie_records):
    (root / "catalog/vod/index").mkdir(parents=True)
    categories = {}
    for section in preview.SECTIONS:
        records = movie_records if section == "movies" else []
        path = root / f"catalog/vod/index/{section}.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        categories[section] = {"index_path": f"catalog/vod/index/{section}.json"}
    (root / "catalog/vod/index.json").write_text(json.dumps({"categories": categories}), encoding="utf-8")
    (root / "catalog/channels").mkdir(parents=True)
    (root / "catalog/channels/channels.json").write_text(
        json.dumps({"channels": [{"id": "ch1", "name": "Example", "sources": [{"url": "https://secret.example/stream"}]}]}),
        encoding="utf-8",
    )
    (root / "catalog/radios").mkdir(parents=True)
    (root / "catalog/radios/radios.json").write_text(
        json.dumps({"radios": [{"id": "radio1", "name": "Example radio", "stream_url": "https://secret.example/radio"}]}),
        encoding="utf-8",
    )


class ReferenceImportPreviewSummaryTests(unittest.TestCase):
    def test_summary_reports_count_deltas_and_bounded_identity_examples_without_stream_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = root / "before"
            after = root / "after"
            make_catalog(before, [{
                "id": "movie-1", "title": "Example Movie", "year": None,
                "poster_url": None, "genres": [], "source_count": 1,
            }])
            make_catalog(after, [
                {
                    "id": "movie-1", "title": "Example Movie", "year": "2001",
                    "poster_url": "https://images.example/poster.jpg", "genres": ["Drama"],
                    "source_count": 2,
                },
                {
                    "id": "movie-2", "title": "Example Movie", "year": None,
                    "poster_url": None, "genres": [], "source_count": 0,
                },
            ])
            import_report = root / "reference-import.json"
            import_report.write_text(json.dumps({
                "counts": {"source_urls_merged_into_reference_candidates": 3},
                "counter_semantics": {
                    "source_urls_merged_into_reference_candidates": "Parser-level merges; not net catalog additions."
                },
            }), encoding="utf-8")
            result = preview.build_summary(before, after, import_report)
            rendered = json.dumps(result)

        self.assertFalse(result["catalog_published"])
        self.assertFalse(result["review_gate"]["automatic_approval_allowed"])
        self.assertEqual(result["review_gate"]["status"], "blocked_pending_review")
        self.assertTrue(any("duplicate-title groups increased" in reason for reason in result["review_gate"]["blocking_reasons"]))
        self.assertEqual(result["delta"]["vod_total"], 1)
        self.assertEqual(result["delta"]["vod_counts"]["movies"], 1)
        self.assertEqual(result["delta"]["vod_missing_metadata"]["year"], 0)
        self.assertEqual(result["delta"]["vod_source_references_in_index"]["source_count"], 1)
        self.assertEqual(result["delta"]["vod_duplicate_titles_by_category"]["movies"]["groups"], 1)
        self.assertNotIn("https://secret.example", rendered)
        self.assertIn("duplicate_title_examples", result)
        self.assertIn("Example Movie", rendered)
        self.assertIn("new_records_missing_metadata", result)
        self.assertEqual(result["import_counters"]["source_urls_merged_into_reference_candidates"], 3)
        self.assertIn("not net catalog additions", result["import_counter_semantics"]["source_urls_merged_into_reference_candidates"])
        self.assertEqual(result["new_records_missing_metadata"]["movies"]["new_record_count"], 1)
        self.assertEqual(result["new_records_missing_metadata"]["movies"]["records_with_missing_metadata"], 1)
        self.assertNotIn("vod_record_ids_by_category", rendered)


if __name__ == "__main__":
    unittest.main()
