import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_radio_genres import build_report


class SuggestRadioGenresTests(unittest.TestCase):
    def test_unique_keyword_suggestion_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/radios").mkdir(parents=True)
            path = root / "catalog/radios/radios.json"
            path.write_text(json.dumps({"radios": [
                {"id": "r1", "name": "Rock Cidade", "genre": None},
                {"id": "r2", "name": "Rádio Sem Categoria", "genre": ""},
                {"id": "r3", "name": "Jazz FM", "genre": "Jazz"},
            ]}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            report = build_report(root)
            after = path.read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual(report["counts"]["radios_missing_genre_examined"], 2)
        self.assertEqual(report["counts"]["candidate_suggestions"], 1)
        self.assertEqual(report["suggestions"][0]["suggested_genre"], "Rock")
        self.assertFalse(report["suggestions"][0]["automatic_update"])

    def test_multiple_genre_matches_are_held_for_manual_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/radios").mkdir(parents=True)
            (root / "catalog/radios/radios.json").write_text(json.dumps({
                "radios": [{"id": "r1", "name": "Rock Gospel", "genre": None}]
            }), encoding="utf-8")
            report = build_report(root)

        self.assertEqual(report["counts"]["candidate_suggestions"], 0)
        self.assertEqual(report["counts"]["ambiguous_candidates"], 1)
        self.assertEqual(report["ambiguous"][0]["candidate_genres"], ["Rock", "Gospel"])


if __name__ == "__main__":
    unittest.main()
