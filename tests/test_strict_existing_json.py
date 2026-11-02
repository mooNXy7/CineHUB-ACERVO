import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class StrictExistingJSONTests(unittest.TestCase):
    def test_missing_file_uses_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            fallback = {"schema_version": 1, "channels": []}
            self.assertEqual(importer.load_json(path, fallback), fallback)

    def test_corrupt_existing_json_aborts_instead_of_returning_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.json"
            path.write_text("{broken", encoding="utf-8")
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "existing JSON is unreadable"):
                importer.load_json(path, {"schema_version": 1, "channels": []})
            self.assertEqual(path.read_bytes(), original)

    def test_wrong_top_level_type_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "radios.json"
            path.write_text(json.dumps([]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "wrong top-level type"):
                importer.load_json(path, {"schema_version": 1, "radios": []})


if __name__ == "__main__":
    unittest.main()
