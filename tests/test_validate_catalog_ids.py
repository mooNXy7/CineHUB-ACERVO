import unittest

from scripts.validate_catalog import index_detail_tmdb_mismatches


class VODIndexDetailConsistencyTests(unittest.TestCase):
    def test_matching_tmdb_ids_pass(self):
        indexed = {"movie-1": {"id": "movie-1", "tmdb_id": "123"}}
        details = [{"id": "movie-1", "tmdb_id": "123"}]
        self.assertEqual(index_detail_tmdb_mismatches(indexed, details, "movies"), [])

    def test_index_missing_tmdb_id_but_detail_has_one_is_reported(self):
        indexed = {"movie-1": {"id": "movie-1", "title": "Film"}}
        details = [{"id": "movie-1", "tmdb_id": "123"}]
        errors = index_detail_tmdb_mismatches(indexed, details, "movies")
        self.assertEqual(len(errors), 1)
        self.assertIn("index=ausente", errors[0])
        self.assertIn("detail=123", errors[0])

    def test_different_tmdb_ids_are_reported(self):
        indexed = {"movie-1": {"id": "movie-1", "tmdb_id": "123"}}
        details = [{"id": "movie-1", "tmdb_id": "456"}]
        errors = index_detail_tmdb_mismatches(indexed, details, "movies")
        self.assertEqual(len(errors), 1)
        self.assertIn("index=123", errors[0])
        self.assertIn("detail=456", errors[0])

    def test_index_tmdb_id_missing_from_detail_is_reported(self):
        indexed = {"movie-1": {"id": "movie-1", "tmdb_id": "123"}}
        details = [{"id": "movie-1", "tmdb_id": None}]
        errors = index_detail_tmdb_mismatches(indexed, details, "movies")
        self.assertEqual(len(errors), 1)
        self.assertIn("index=123", errors[0])
        self.assertIn("detail=ausente", errors[0])


if __name__ == "__main__":
    unittest.main()
