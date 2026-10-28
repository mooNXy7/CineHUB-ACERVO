import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADIOS_PATH = ROOT / "catalog/radios/radios.json"


class RadioCatalogRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(RADIOS_PATH.read_text(encoding="utf-8"))
        cls.radios = {item["id"]: item for item in cls.document["radios"]}

    def test_explicit_genre_names_are_enriched_without_guessing_generic_fm(self):
        expected = {
            "radio.012-rock-news": "Rock",
            "radio.a-sertaneja-106-7-fm": "Sertanejo",
            "radio.adoro-flashback": "Flashback",
            "radio.alpha-mpb": "MPB",
            "radio.essencia-gospel-fm": "Gospel",
            "radio.radio-forro": "Forró",
        }
        for radio_id, genre in expected.items():
            with self.subTest(radio_id=radio_id):
                self.assertEqual(self.radios[radio_id]["genre"], genre)
        self.assertIsNone(self.radios["radio.87-fm"]["genre"])

    def test_known_malformed_imported_urls_are_quarantined(self):
        self.assertEqual(self.radios["radio.a-tarde-fm"]["stream_url"], "https://stm35.srvstm.com:7920/stream")
        self.assertEqual(self.radios["radio.casa-dos-caipiras"]["genre"], "Sertanejo")
        self.assertEqual(self.radios["radio.casa-dos-caipiras"]["logo_url"], "https://img.radios.com.br/radio/lg/radio36246_1585720041.jpg")
        self.assertIsNone(self.radios["radio-https-8758-brasilstream-com-br-stream"]["stream_url"])
        self.assertEqual(self.radios["radio.clube-fm-100-5"]["stream_url"], "https://sc4s.cdn.upx.com:8069/stream")
        self.assertEqual(self.radios["radio.radio-nikey"]["stream_url"], "https://stm8.voxhd.com.br:7996/stream")
        self.assertIsNone(self.radios["radio-https-8185-brasilstream-com-br-stream"]["stream_url"])

    def test_no_radio_url_contains_known_imported_html_fragments(self):
        bad = re.compile(
            r"%22%3e%3c/audio%3e|%22%20data-turbolinks-permanent|%22$|"
            r"facebook[.]com/photo/.*__tn__=%3c",
            re.IGNORECASE,
        )
        findings = []
        for radio in self.document["radios"]:
            for field in ("stream_url", "logo_url"):
                value = radio.get(field)
                if isinstance(value, str) and bad.search(value):
                    findings.append((radio.get("id"), field))
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
