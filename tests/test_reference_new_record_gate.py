import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def item(ident, title, year="2020", poster="https://images.example/poster.jpg", genres=None):
    return {
        "id": ident,
        "title": title,
        "type": "movie",
        "year": year,
        "poster_url": poster,
        "genres": genres if genres is not None else ["Drama"],
        "sources": [],
        "provider_refs": [],
    }


class NewReferenceRecordGateTests(unittest.TestCase):
    def test_existing_id_remains_eligible_even_when_metadata_is_incomplete(self):
        old = {"movie-existing": item("movie-existing", "Existing")}
        incoming = item("movie-existing", "Existing", year=None, poster=None, genres=[])
        counters = {}

        result = importer.hold_unready_new_records("movies", old, [incoming], counters)

        self.assertEqual([x["id"] for x in result], ["movie-existing"])
        self.assertEqual(counters, {})

    def test_new_complete_unique_record_is_eligible(self):
        counters = {}
        incoming = item("movie-new", "New Complete Film")

        result = importer.hold_unready_new_records("movies", {}, [incoming], counters)

        self.assertEqual([x["id"] for x in result], ["movie-new"])
        self.assertEqual(counters, {})

    def test_new_record_missing_any_required_metadata_is_held(self):
        counters = {}
        incoming = item("movie-new", "New Incomplete Film", poster=None, genres=[])

        result = importer.hold_unready_new_records("movies", {}, [incoming], counters)

        self.assertEqual(result, [])
        self.assertEqual(counters.get("movies_held_incomplete_metadata"), 1)

    def test_new_title_matching_existing_record_is_held_without_merging(self):
        old = {"movie-old": item("movie-old", "Same Title")}
        incoming = item("movie-new", "Same Title", year="2021")
        counters = {}

        result = importer.hold_unready_new_records("movies", old, [incoming], counters)

        self.assertEqual(result, [])
        self.assertEqual(counters.get("movies_held_title_collision"), 1)
        self.assertEqual(old["movie-old"]["year"], "2020")

    def test_ambiguous_new_title_group_is_held_instead_of_picking_a_winner(self):
        first = item("movie-a", "Shared Title", year="2020")
        second = item("movie-b", "Shared Title", year="2021")
        counters = {}

        result = importer.hold_unready_new_records("movies", {}, [first, second], counters)

        self.assertEqual(result, [])
        self.assertEqual(counters.get("movies_held_title_collision"), 2)


if __name__ == "__main__":
    unittest.main()
