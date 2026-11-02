import sys
import unittest

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ReferenceDedupeTests(unittest.TestCase):
    def test_title_year_variants_with_different_ids_remain_separate(self):
        first = {
            "id": "movie-example-movie-2019",
            "title": "Example Movie (2019)",
            "type": "movie",
            "year": None,
            "tmdb_id": None,
            "sources": [{"url": "https://one.example/movie.mp4", "audio": "dub"}],
            "provider_refs": [],
        }
        second = {
            "id": "movie-example-movie",
            "title": "Example Movie",
            "type": "movie",
            "year": "2019",
            "tmdb_id": None,
            "sources": [{"url": "https://two.example/movie.mp4", "audio": "dub"}],
            "provider_refs": [],
        }

        result = importer.dedupe_records([first, second])

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {source["url"] for item in result for source in item["sources"]},
            {"https://one.example/movie.mp4", "https://two.example/movie.mp4"},
        )


if __name__ == "__main__":
    unittest.main()
