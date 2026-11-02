import json
import tempfile
import unittest
from pathlib import Path
from scripts.update_radio_catalog import apply_reviewed_genre_decisions, canonical_genre, genre_from_tags, update


class RadioGenreNormalizationTests(unittest.TestCase):
    def test_known_aliases_are_normalized_without_changing_other_labels(self):
        self.assertEqual(canonical_genre("Jornalismo"), "Notícias")
        self.assertEqual(canonical_genre("Brasileira"), "Música Brasileira")
        self.assertEqual(canonical_genre("Rap/Hip-hop"), "Hip-Hop")
        self.assertEqual(canonical_genre("Jazz"), "Jazz")

    def test_specific_tags_fill_only_supported_genres(self):
        self.assertEqual(genre_from_tags("gospel music"), "Gospel")
        self.assertEqual(genre_from_tags("musica popular brasileira"), "MPB")
        self.assertEqual(genre_from_tags("eclectic programming"), "Eclética")
        self.assertEqual(genre_from_tags("light classics"), "Clássica")
        self.assertEqual(genre_from_tags("nativista"), "Regional")
        self.assertIsNone(genre_from_tags("popular music, online"))

    def test_update_normalizes_existing_genres_and_preserves_other_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sources").mkdir()
            (root / "catalog/radios").mkdir(parents=True)
            (root / "sources/sources.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
            original = {
                "schema_version": 1,
                "radios": [{
                    "id": "radio.test",
                    "name": "Rádio Teste",
                    "stream_url": "https://radio.example/live",
                    "logo_url": "https://radio.example/logo.png",
                    "genre": "Jornalismo",
                    "source_id": "existing",
                    "custom_metadata": {"keep": True},
                }],
            }
            path = root / "catalog/radios/radios.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            report = update(root)
            saved = json.loads(path.read_text(encoding="utf-8"))["radios"][0]
        self.assertEqual(saved["genre"], "Notícias")
        self.assertEqual(saved["stream_url"], original["radios"][0]["stream_url"])
        self.assertEqual(saved["logo_url"], original["radios"][0]["logo_url"])
        self.assertEqual(saved["custom_metadata"], {"keep": True})
        self.assertEqual(report["genre_normalization"]["updated"], 1)

    def test_reviewed_genre_decisions_require_exact_identity_and_preserve_existing_genres(self):
        radios = [
            {"id": "r1", "name": "Nova FM", "genre": None},
            {"id": "r2", "name": "News FM", "genre": "Notícias"},
            {"id": "r3", "name": "Different Name", "genre": None},
        ]
        evidence = [{"source": "Official station page", "url": "https://example.org/about", "reported_genre": "MPB"}]
        decisions = [
            {"radio_id": "r1", "radio_name": "Nova FM", "assigned_genre": "MPB", "decision": "manual_verified", "evidence": evidence},
            {"radio_id": "r2", "radio_name": "News FM", "assigned_genre": "Rock", "decision": "manual_verified", "evidence": evidence},
            {"radio_id": "r3", "radio_name": "Wrong Name", "assigned_genre": "Jazz", "decision": "manual_verified", "evidence": evidence},
            {"radio_id": "missing", "radio_name": "Missing FM", "assigned_genre": "Jazz", "decision": "manual_verified", "evidence": evidence},
            {"radio_id": "r1", "radio_name": "Nova FM", "assigned_genre": "Rock", "decision": "guess", "evidence": evidence},
        ]
        counts = apply_reviewed_genre_decisions(radios, decisions)
        self.assertEqual(radios[0]["genre"], "MPB")
        self.assertEqual(radios[1]["genre"], "Notícias")
        self.assertIsNone(radios[2]["genre"])
        self.assertEqual(counts["applied"], 1)
        self.assertEqual(counts["already_classified"], 1)
        self.assertEqual(counts["identity_mismatch"], 1)
        self.assertEqual(counts["missing_radio"], 1)
        self.assertEqual(counts["invalid_decision"], 1)


if __name__ == "__main__":
    unittest.main()
