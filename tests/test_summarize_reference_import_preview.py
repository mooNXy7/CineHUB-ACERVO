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
    def test_summary_reports_count_deltas_without_catalog_urls_or_titles(self):
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
                    "id": "movie-2", "title": "Another Movie", "year": None,
                    "poster_url": None, "genres": [], "source_count": 0,
                },
            ])
            result = preview.build_summary(before, after)
            rendered = json.dumps(result)

        self.assertFalse(result["catalog_published"])
        self.assertEqual(result["delta"]["vod_total"], 1)
        self.assertEqual(result["delta"]["vod_counts"]["movies"], 1)
        self.assertEqual(result["delta"]["vod_missing_metadata"]["year"], 0)
        self.assertEqual(result["delta"]["vod_source_references_in_index"]["source_count"], 1)
        self.assertNotIn("https://secret.example", rendered)
        self.assertNotIn("Example Movie", rendered)
        self.assertNotIn("Another Movie", rendered)


if __name__ == "__main__":
    unittest.main()
