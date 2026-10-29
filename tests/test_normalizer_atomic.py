import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import normalize_catalog


class NormalizeCatalogAtomicWriteTests(unittest.TestCase):
    def test_successful_publish_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.json"
            path.write_text('{"old": true}\n', encoding="utf-8")

            normalize_catalog.atomic_write_text(path, '{"nome": "São Paulo"}\n')

            self.assertEqual(path.read_text(encoding="utf-8"), '{"nome": "São Paulo"}\n')
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_replace_failure_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.json"
            original = b'{"previous": "intacto"}\n'
            path.write_bytes(original)

            with patch("normalize_catalog.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    normalize_catalog.atomic_write_text(path, '{"new": true}\n')

            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(tmp).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
