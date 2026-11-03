import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_reference_catalog import is_probable_image_url, parse_radio_line


class RadioReferenceContractTests(unittest.TestCase):
    def test_real_reference_fixture_uses_name_and_stream_columns(self):
        fixture = ROOT / "tests/fixtures/radios_reference.txt"
        rows = [parse_radio_line(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
        rows = [row for row in rows if row]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "012 Rock News")
        self.assertEqual(rows[0]["stream_url"], "https://9881.brasilstream.com.br/stream")
        self.assertIsNone(rows[0]["logo_url"])
        self.assertEqual(rows[0]["stream_status"], "imported")

    def test_legacy_four_column_format_remains_supported(self):
        row = parse_radio_line("legacy-id|Rádio Legado|https://audio.example.org/live|https://img.example.org/logo.png")
        self.assertEqual(row["name"], "Rádio Legado")
        self.assertEqual(row["stream_url"], "https://audio.example.org/live")
        self.assertEqual(row["logo_url"], "https://img.example.org/logo.png")

    def test_image_url_is_not_accepted_as_audio_stream(self):
        row = parse_radio_line("Estação com erro|https://img.example.org/logo.png")
        self.assertIsNone(row["stream_url"])
        self.assertEqual(row["stream_status"], "pending_review")
        self.assertTrue(is_probable_image_url("https://img.example.org/logo.webp"))
        self.assertFalse(is_probable_image_url("https://audio.example.org/live.mp3"))

    def test_malformed_or_empty_rows_are_ignored(self):
        self.assertIsNone(parse_radio_line(""))
        self.assertIsNone(parse_radio_line("nome-sem-stream"))
        self.assertIsNone(parse_radio_line("|https://audio.example.org/live"))

    def test_existing_radio_catalog_is_not_silently_truncated(self):
        data = json.loads((ROOT / "catalog/radios/radios.json").read_text(encoding="utf-8"))
        radios = data.get("radios", [])
        ids = [row.get("id") for row in radios]
        self.assertGreaterEqual(len(radios), 1000)
        self.assertTrue(all(ids))
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
