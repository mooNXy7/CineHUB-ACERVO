import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ReferenceImporterAtomicWriteTests(unittest.TestCase):
    def test_json_writer_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text('{"old":true}\n', encoding="utf-8")
            importer.write_json(path, {"channels": [{"id": "new"}]})
            self.assertEqual(path.read_text(encoding="utf-8"), '{\n  "channels": [\n    {\n      "id": "new"\n    }\n  ]\n}\n')
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])
            self.assertEqual(list(Path(tmp).glob(".*.tmp")), [])

    def test_failed_replace_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text('{"old":true}\n', encoding="utf-8")
            with patch.object(importer.os, "replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    importer.write_json(path, {"new": True})
            self.assertEqual(path.read_text(encoding="utf-8"), '{"old":true}\n')
            self.assertEqual(list(Path(tmp).glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
