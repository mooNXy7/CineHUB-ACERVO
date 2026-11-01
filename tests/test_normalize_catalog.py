import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import normalize_catalog


class CatalogDisplayNormalizationTests(unittest.TestCase):
    def test_decodes_html_entities_and_collapses_whitespace(self):
        value = "  Rock N&#039; Roll:  Vivendo no Limite (2020)  "
        self.assertEqual(
            normalize_catalog.normalize_display_text(value),
            "Rock N' Roll: Vivendo no Limite (2020)",
        )

    def test_removes_leading_bom_but_preserves_zero_width_joiner(self):
        self.assertEqual(
            normalize_catalog.normalize_display_text("\ufeffHappy End: Por Trás da Webcam"),
            "Happy End: Por Trás da Webcam",
        )
        multilingual = "ರ‍್ಯಾಂಬೋ 2"
        self.assertEqual(normalize_catalog.normalize_display_text(multilingual), multilingual)

    def test_title_normalization_preserves_ids_and_source_arrays(self):
        records = [{
            "id": "movie-1",
            "title": "Scooby-Doo!  Mistério na Lutamania",
            "sources": [{"url": "https://example.com/live"}],
            "tmdb_id": "123",
        }]
        updated = normalize_catalog.normalize_title_records(records)
        self.assertEqual(updated, 1)
        self.assertEqual(records[0]["title"], "Scooby-Doo! Mistério na Lutamania")
        self.assertEqual(records[0]["id"], "movie-1")
        self.assertEqual(records[0]["tmdb_id"], "123")
        self.assertEqual(records[0]["sources"], [{"url": "https://example.com/live"}])


if __name__ == "__main__":
    unittest.main()
