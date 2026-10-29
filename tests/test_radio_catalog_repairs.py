import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADIOS_PATH = ROOT / "catalog/radios/radios.json"
QUARANTINE_PATH = ROOT / "reports/radio-quarantine.json"


class RadioCatalogRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(RADIOS_PATH.read_text(encoding="utf-8"))
        cls.radios = {item["id"]: item for item in cls.document["radios"]}
        cls.quarantine = json.loads(QUARANTINE_PATH.read_text(encoding="utf-8"))
        cls.quarantined = {item["record"]["id"]: item for item in cls.quarantine["records"]}

    def test_explicit_genre_names_are_enriched_without_guessing_generic_fm(self):
        expected = {
            "radio.012-rock-news": "Rock",
            "radio.a-sertaneja-106-7-fm": "Sertanejo",
            "radio.adoro-flashback": "Flashback",
            "radio.alpha-mpb": "MPB",
            "radio.essencia-gospel-fm": "Gospel",
            "radio.radio-forro": "Forró",
            "radio.casa-dos-caipiras": "Sertanejo",
        }
        for radio_id, genre in expected.items():
            with self.subTest(radio_id=radio_id):
                self.assertEqual(self.radios[radio_id]["genre"], genre)
        self.assertIsNone(self.radios["radio.87-fm"]["genre"])

    def test_stream_urls_with_trailing_html_are_repaired(self):
        expected = {
            "radio.a-tarde-fm": "https://stm35.srvstm.com:7920/stream",
            "radio.clube-fm-100-5": "https://sc4s.cdn.upx.com:8069/stream",
            "radio.radio-nikey": "https://stm8.voxhd.com.br:7996/stream",
        }
        for radio_id, stream_url in expected.items():
            with self.subTest(radio_id=radio_id):
                self.assertEqual(self.radios[radio_id]["stream_url"], stream_url)

    def test_malformed_duplicate_rows_are_quarantined_not_deleted(self):
        expected = {
            "radio-https-8185-brasilstream-com-br-stream": "radio.98-rock",
            "radio-https-8758-brasilstream-com-br-stream": "radio.casa-dos-caipiras",
            "radio-https-sv10-hdradios-net-6864-stream": "radio.radio-chaveco",
            "radio-https-streaming-radioempresabrasil-com-br-proxy-novainstrumental-stream": "radio.radio-nova-instrumental",
        }
        self.assertEqual(len(self.document["radios"]), 1022)
        self.assertTrue(self.quarantine["records_preserved"])
        for radio_id, duplicate_of in expected.items():
            with self.subTest(radio_id=radio_id):
                self.assertNotIn(radio_id, self.radios)
                self.assertEqual(self.quarantined[radio_id]["duplicate_of"], duplicate_of)
                self.assertEqual(self.quarantined[radio_id]["action"], "quarantined_not_deleted")
                self.assertIn(self.quarantined[radio_id]["duplicate_stream_url"],
                              {item.get("stream_url") for item in self.document["radios"]})

    def test_no_live_radio_url_contains_known_imported_html_fragments(self):
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
