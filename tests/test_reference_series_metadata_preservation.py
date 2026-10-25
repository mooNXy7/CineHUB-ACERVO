import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ReferenceSeriesMetadataPreservationTests(unittest.TestCase):
    def test_series_enrichment_preserves_existing_metadata_and_unions_genres(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            vod = reference / "vod"
            vod.mkdir()
            (vod / "series-main-1.txt").write_text(
                "@A Test Series (2010)\t2010\n"
                "1\t1\tdub\thttps://media.example/episode.m3u8\n",
                encoding="utf-8",
            )
            item = {
                "id": "series-existing-id",
                "title": "A Test Series (2010)",
                "type": "series",
                "year": None,
                "tmdb_id": "111",
                "poster_url": "https://images.example/existing-poster.jpg",
                "genres": ["Drama"],
                "subtype": "series",
                "seasons": {},
                "sources": [],
                "provider_refs": [],
                "source_candidates_skipped": 0,
            }
            series = {(importer.norm(item["title"]), "2010"): item}
            counters = {"skipped_urls": 0, "sources_added": 0, "provider_refs_added": 0}
            fichas = {
                ("s", importer.norm(item["title"])): {
                    "tmdb_id": "222",
                    "poster_path": "https://images.example/reference-poster.jpg",
                    "genres": ["Drama", "Comedy"],
                }
            }

            importer.parse_series(reference, fichas, {}, set(), set(), counters, series)

        self.assertEqual(item["id"], "series-existing-id")
        self.assertEqual(item["tmdb_id"], "111")
        self.assertEqual(item["poster_url"], "https://images.example/existing-poster.jpg")
        self.assertEqual(item["year"], "2010")
        self.assertEqual(item["genres"], ["Drama", "Comedy"])
        self.assertEqual(len(item["seasons"]), 1)
        self.assertEqual(item["seasons"][0]["episodes"][0]["episode"], 1)


if __name__ == "__main__":
    unittest.main()
