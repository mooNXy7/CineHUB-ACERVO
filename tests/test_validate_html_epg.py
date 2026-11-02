import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_catalog import validate_html_epg_doc


class ValidateHtmlEpgTests(unittest.TestCase):
    def test_valid_sidecar_passes(self):
        doc = {
            "schema_version": 1,
            "timezone": "America/Sao_Paulo",
            "programmes": {
                "HBO": {
                    "source_id": "meuguia-br",
                    "programmes": [
                        {"start": "2026-10-25T18:00:00-03:00", "end": "2026-10-25T19:00:00-03:00", "title": "Filme A"},
                        {"start": "2026-10-25T19:00:00-03:00", "end": "2026-10-25T20:00:00-03:00", "title": "Filme B"},
                    ],
                },
            },
            "health": {},
        }
        self.assertEqual(validate_html_epg_doc(doc), [])

    def test_rejects_missing_timezone_and_invalid_interval(self):
        doc = {
            "schema_version": 1,
            "timezone": "UTC",
            "programmes": {
                "HBO": {
                    "source_id": "unknown",
                    "programmes": [
                        {"start": "2026-10-25T19:00:00", "end": "2026-10-25T18:00:00", "title": "Inválido"},
                    ],
                },
            },
            "health": {},
        }
        errors = validate_html_epg_doc(doc)
        self.assertTrue(any("timezone" in error for error in errors))
        self.assertTrue(any("source_id" in error for error in errors))
        self.assertTrue(any("intervalo inválido" in error for error in errors))

    def test_rejects_unsorted_programmes(self):
        doc = {
            "schema_version": 1,
            "timezone": "America/Sao_Paulo",
            "programmes": {
                "HBO": {
                    "source_id": "meuguia-br",
                    "programmes": [
                        {"start": "2026-10-25T20:00:00-03:00", "end": "2026-10-25T21:00:00-03:00", "title": "B"},
                        {"start": "2026-10-25T19:00:00-03:00", "end": "2026-10-25T20:00:00-03:00", "title": "A"},
                    ],
                },
            },
            "health": {},
        }
        self.assertTrue(any("fora de ordem" in error for error in validate_html_epg_doc(doc)))


if __name__ == "__main__":
    unittest.main()
