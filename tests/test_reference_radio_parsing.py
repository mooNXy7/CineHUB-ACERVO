import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ReferenceRadioParsingTests(unittest.TestCase):
    def test_imports_two_and_three_field_rows_without_overwriting_existing_radios(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            vod = reference / "vod"
            vod.mkdir()
            (vod / "radios.txt").write_text(
                "Test FM|https://radio.example/live\n"
                "Logo FM|https://radio.example/logo-live|https://images.example/logo.png\n"
                "Bad FM|javascript:alert(1)|https://images.example/bad.png\n"
                "Existing FM|https://radio.example/new-live|https://images.example/new.png\n"
                "Needs Stream|https://radio.example/needs-stream\n"
                "Malformed row only one field\n"
                "https://cast.example/live|https://images.example/wrong-name.png|https://images.example/wrong-logo.png\n",
                encoding="utf-8",
            )
            existing = {
                "schema_version": 1,
                "radios": [{
                    "id": "radio-existing",
                    "name": "Existing FM",
                    "stream_url": "https://radio.example/original-live",
                    "logo_url": "https://images.example/original.png",
                    "genre": "Rock",
                }, {
                    "id": "radio-needs-stream",
                    "name": "Needs Stream",
                    "stream_url": None,
                    "logo_url": None,
                    "genre": None,
                }],
            }

            result, added, updated = importer.import_reference_radios(reference, existing)

        self.assertEqual(added, 3)
        self.assertEqual(updated, 1)
        by_name = {item["name"]: item for item in result["radios"]}
        self.assertEqual(by_name["Test FM"]["stream_url"], "https://radio.example/live")
        self.assertIsNone(by_name["Test FM"]["logo_url"])
        self.assertEqual(by_name["Logo FM"]["stream_url"], "https://radio.example/logo-live")
        self.assertEqual(by_name["Logo FM"]["logo_url"], "https://images.example/logo.png")
        self.assertIsNone(by_name["Bad FM"]["stream_url"])
        self.assertEqual(by_name["Bad FM"]["stream_status"], "pending_review")
        self.assertEqual(by_name["Existing FM"]["stream_url"], "https://radio.example/original-live")
        self.assertEqual(by_name["Existing FM"]["genre"], "Rock")
        self.assertEqual(by_name["Needs Stream"]["stream_url"], "https://radio.example/needs-stream")
        self.assertNotIn("https://cast.example/live", by_name)


    def test_quarantines_url_as_name_records_without_losing_original_fields(self):
        radios = {
            "schema_version": 1,
            "radios": [
                {"id": "radio-good", "name": "Good FM", "stream_url": "https://good.example/live"},
                {"id": "radio-bad", "name": "https://bad.example/live", "stream_url": "https://images.example/logo.png"},
            ],
        }
        quarantine = {"schema_version": 1, "records": []}

        active, saved, moved = importer.quarantine_malformed_radio_records(radios, quarantine)

        self.assertEqual(moved, 1)
        self.assertEqual([item["name"] for item in active["radios"]], ["Good FM"])
        self.assertEqual(len(saved["records"]), 1)
        self.assertEqual(saved["records"][0]["id"], "radio-bad")
        self.assertEqual(saved["records"][0]["stream_url"], "https://images.example/logo.png")
        self.assertEqual(saved["records"][0]["quarantine_reason"], "url_instead_of_radio_name")

        active, saved, moved_again = importer.quarantine_malformed_radio_records(active, saved)
        self.assertEqual(moved_again, 0)
        self.assertEqual(len(saved["records"]), 1)



if __name__ == "__main__":
    unittest.main()
