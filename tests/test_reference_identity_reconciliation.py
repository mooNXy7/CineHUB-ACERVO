import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def record(ident, title, year, tmdb_id, source_url):
    return {
        "id": ident,
        "title": title,
        "type": "movie",
        "year": year,
        "tmdb_id": tmdb_id,
        "poster_url": None,
        "genres": [],
        "sources": [{
            "url": source_url,
            "audio": "dub",
            "priority": 20,
            "source_id": "reference",
            "source_type": "direct",
        }],
        "provider_refs": [],
        "source_candidates_skipped": 0,
    }


class ReferenceIdentityReconciliationTests(unittest.TestCase):
    def test_exact_title_and_year_collision_merges_sources_into_existing_record(self):
        old = record("movie-existing", "Example Film (2020)", "2020", "123", "https://old.example/movie.m3u8")
        incoming = record("movie-new-id", "Example Film", "2020", "123", "https://new.example/movie.m3u8")
        existing = {old["id"]: old}
        counters = defaultdict(int)

        accepted = importer.reconcile_reference_identity("movies", existing, [incoming], counters)

        self.assertEqual(accepted, [])
        self.assertEqual(old["id"], "movie-existing")
        self.assertEqual({source["url"] for source in old["sources"]}, {
            "https://old.example/movie.m3u8", "https://new.example/movie.m3u8"
        })
        self.assertEqual(counters["movies_tmdb_id_sources_merged_into_existing"], 1)

    def test_conflicting_title_with_existing_tmdb_id_is_skipped_not_merged(self):
        old = record("movie-existing", "First Film (2020)", "2020", "123", "https://old.example/movie.m3u8")
        incoming = record("movie-conflict", "Completely Different Film (2020)", "2020", "123", "https://new.example/movie.m3u8")
        existing = {old["id"]: old}
        counters = defaultdict(int)

        accepted = importer.reconcile_reference_identity("movies", existing, [incoming], counters)

        self.assertEqual(accepted, [])
        self.assertEqual(old["title"], "First Film (2020)")
        self.assertEqual(len(old["sources"]), 1)
        self.assertEqual(counters["movies_ambiguous_tmdb_id_records_skipped"], 1)

    def test_duplicate_tmdb_ids_in_incoming_group_are_all_quarantined(self):
        first = record("movie-one", "First Film (2020)", "2020", "123", "https://one.example/movie.m3u8")
        second = record("movie-two", "Second Film (2020)", "2020", "123", "https://two.example/movie.m3u8")
        counters = defaultdict(int)

        accepted = importer.reconcile_reference_identity("movies", {}, [first, second], counters)

        self.assertEqual(accepted, [])
        self.assertEqual(counters["movies_ambiguous_tmdb_id_records_skipped"], 2)

    def test_unique_tmdb_id_incoming_record_is_accepted(self):
        incoming = record("movie-unique", "Unique Film (2020)", "2020", "456", "https://unique.example/movie.m3u8")
        counters = defaultdict(int)

        accepted = importer.reconcile_reference_identity("movies", {}, [incoming], counters)

        self.assertEqual(accepted, [incoming])
        self.assertEqual(counters["movies_ambiguous_tmdb_id_records_skipped"], 0)


if __name__ == "__main__":
    unittest.main()
