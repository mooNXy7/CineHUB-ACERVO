import json
import sys
import tempfile
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
            "seasons": [{"season": 1, "episodes": [{"title": "  Episódio &#039; Um &#039;  "}]}],
        }]
        updated = normalize_catalog.normalize_title_records(records)
        self.assertEqual(updated, 2)
        self.assertEqual(records[0]["title"], "Scooby-Doo! Mistério na Lutamania")
        self.assertEqual(records[0]["id"], "movie-1")
        self.assertEqual(records[0]["tmdb_id"], "123")
        self.assertEqual(records[0]["sources"], [{"url": "https://example.com/live"}])
        self.assertEqual(records[0]["seasons"][0]["episodes"][0]["title"], "Episódio ' Um '")


    def test_normalizes_vod_index_and_detail_titles_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_path = root / "catalog/vod/index/movies.json"
            detail_path = root / "catalog/vod/details/movies/A-001.json"
            manifest_path = root / "catalog/vod/index.json"
            for path in (index_path, detail_path, manifest_path):
                path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(json.dumps([{
                "id": "movie-1",
                "title": "A&#039;  Test",
                "detail_path": "catalog/vod/details/movies/A-001.json",
                "tmdb_id": "123",
            }]), encoding="utf-8")
            detail_path.write_text(json.dumps([{
                "id": "movie-1",
                "title": "A&#039;  Test",
                "tmdb_id": "123",
                "sources": [{"url": "https://example.com/movie"}],
            }]), encoding="utf-8")
            manifest_path.write_text(json.dumps({
                "schema_version": 1,
                "categories": {
                    "movies": {"index_path": "catalog/vod/index/movies.json"},
                },
            }), encoding="utf-8")

            index_count, detail_count, index_titles, detail_titles, changed_files = normalize_catalog.normalize_vod_titles(root)

            index = json.loads(index_path.read_text(encoding="utf-8"))
            detail = json.loads(detail_path.read_text(encoding="utf-8"))
            self.assertEqual((index_count, detail_count, index_titles, detail_titles, changed_files), (1, 1, 1, 1, 2))
            self.assertEqual(index[0]["title"], "A' Test")
            self.assertEqual(detail[0]["title"], "A' Test")
            self.assertEqual(detail[0]["sources"], [{"url": "https://example.com/movie"}])
            self.assertEqual(detail[0]["tmdb_id"], "123")



if __name__ == "__main__":
    unittest.main()
