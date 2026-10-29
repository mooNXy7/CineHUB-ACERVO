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
                "Malformed row only one field\n",
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


if __name__ == "__main__":
    unittest.main()
