import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_catalog


class RadioQuarantineValidationTests(unittest.TestCase):
    def test_valid_active_and_quarantined_records_are_accepted(self):
        radios = {"radios": [
            {"id": "radio-live", "name": "Live FM", "stream_url": "https://live.example/stream"},
        ]}
        quarantine = {"schema_version": 1, "records": [
            {"id": "radio-bad", "name": "https://bad.example/live"},
        ]}
        self.assertEqual(validate_catalog.validate_radio_catalog(radios, quarantine), [])

    def test_url_name_in_active_catalog_is_rejected(self):
        radios = {"radios": [
            {"id": "radio-bad", "name": "https://bad.example/live"},
        ]}
        quarantine = {"records": []}
        errors = validate_catalog.validate_radio_catalog(radios, quarantine)
        self.assertTrue(any("URL no campo name" in error for error in errors))

    def test_active_and_quarantine_ids_must_not_overlap(self):
        radios = {"radios": [{"id": "radio-1", "name": "Station FM"}]}
        quarantine = {"records": [{"id": "radio-1", "name": "https://bad.example/live"}]}
        errors = validate_catalog.validate_radio_catalog(radios, quarantine)
        self.assertTrue(any("IDs presentes" in error for error in errors))


    def test_http_or_credentialed_radio_stream_is_rejected(self):
        radios = {"radios": [
            {"id": "radio-http", "name": "HTTP FM", "stream_url": "http://radio.example/live"},
            {"id": "radio-auth", "name": "Auth FM", "stream_url": "https://user:pass@radio.example/live"},
        ]}
        errors = validate_catalog.validate_radio_catalog(radios, {"records": []})
        self.assertEqual(sum("stream_url inseguro/inválido" in error for error in errors), 2)



if __name__ == "__main__":
    unittest.main()
