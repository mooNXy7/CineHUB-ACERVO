import json
import tempfile
import unittest
from pathlib import Path
from scripts.update_radio_catalog import canonical_genre, genre_from_tags, update


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


if __name__ == "__main__":
    unittest.main()
