import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_catalog
import update_epg


class AtomicPublicationTests(unittest.TestCase):
    def test_channel_json_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "catalog.json"
            target.write_text('{"old": true}\n', encoding="utf-8")
            update_catalog.atomic_write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), '{\n  "new": true\n}\n')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["catalog.json"])

    def test_channel_write_failure_preserves_previous_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "catalog.json"
            target.write_text('{"last_valid": true}\n', encoding="utf-8")
            with patch("update_catalog.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    update_catalog.atomic_write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), '{"last_valid": true}\n')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["catalog.json"])

    def test_epg_json_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "health.json"
            target.write_text('{"old": true}\n', encoding="utf-8")
            update_epg.write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), '{\n  "new": true\n}\n')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["health.json"])

    def test_epg_write_failure_preserves_previous_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "index.json"
            target.write_text('{"last_valid": true}\n', encoding="utf-8")
            with patch("update_epg.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    update_epg.write_json(target, {"new": True})
            self.assertEqual(target.read_text(encoding="utf-8"), '{"last_valid": true}\n')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["index.json"])


if __name__ == "__main__":
    unittest.main()
