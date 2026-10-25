import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def record(ident, title, year="2001", tmdb_id=None, source=None):
    return {
        "id": ident,
        "title": title,
        "type": "movie",
        "year": year,
        "tmdb_id": tmdb_id,
        "poster_url": None,
        "genres": [],
        "sources": [source] if source else [],
        "provider_refs": [],
        "source_candidates_skipped": 0,
    }


class ReferenceDedupePreservationTests(unittest.TestCase):
    def test_same_title_year_with_different_ids_is_preserved(self):
        older = record("movie-old-id", "The Same Film", "2001", "100")
        alternate = record("movie-alternate-id", "The Same Film", "2001", "200")

        result = importer.dedupe_records([older, alternate])

        self.assertEqual(len(result), 2)
        self.assertEqual({item["id"] for item in result}, {"movie-old-id", "movie-alternate-id"})

    def test_same_tmdb_id_with_conflicting_titles_is_preserved_for_review(self):
        first = record("movie-one", "First Title", "2001", "100")
        second = record("movie-two", "Different Title", "2001", "100")

        result = importer.dedupe_records([first, second])

        self.assertEqual(len(result), 2)
        self.assertEqual({item["title"] for item in result}, {"First Title", "Different Title"})

    def test_identical_stable_id_merges_sources_and_keeps_metadata(self):
        source = {
            "url": "https://media.example/new.m3u8",
            "audio": "dub",
            "priority": 20,
            "source_id": "reference",
            "source_type": "direct",
        }
        existing = record("movie-same", "Same Film", "2001", "100")
        incoming = record("movie-same", "Same Film", "2001", "100", source)

        result = importer.dedupe_records([existing, incoming])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "movie-same")
        self.assertEqual(len(result[0]["sources"]), 1)
        self.assertEqual(result[0]["sources"][0]["source_id"], "reference")

    def test_record_without_id_is_not_silently_dropped(self):
        item = record("", "Record Missing ID", "2001", None)

        result = importer.dedupe_records([item])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Record Missing ID")


if __name__ == "__main__":
    unittest.main()
