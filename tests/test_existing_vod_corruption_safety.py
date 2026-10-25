import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ExistingVODCorruptionSafetyTests(unittest.TestCase):
    def _setup_paths(self, root: Path):
        details = root / "catalog/vod/details"
        (details / "movies").mkdir(parents=True)
        vod = root / "catalog/vod"
        vod.mkdir(exist_ok=True)
        index = vod / "index.json"
        index.write_text(json.dumps({"categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}}), encoding="utf-8")
        (root / "catalog/vod/index").mkdir(exist_ok=True)
        (root / "catalog/vod/index/movies.json").write_text("[]", encoding="utf-8")
        return details, index

    def test_corrupt_detail_shard_aborts_instead_of_skipping_and_deleting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            details, index = self._setup_paths(root)
            shard = details / "movies" / "A-000.json"
            shard.write_text('{"broken":', encoding="utf-8")
            original = shard.read_bytes()
            with patch.object(importer, "ROOT", root), patch.object(importer, "DETAILS", details), patch.object(importer, "VOD_INDEX", index):
                with self.assertRaisesRegex(ValueError, "detail shard is unreadable"):
                    importer.load_existing_details("movies")
            self.assertEqual(shard.read_bytes(), original)

    def test_detail_record_without_id_aborts_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            details, index = self._setup_paths(root)
            shard = details / "movies" / "A-000.json"
            shard.write_text(json.dumps([{"title": "Existing without ID"}]), encoding="utf-8")
            with patch.object(importer, "ROOT", root), patch.object(importer, "DETAILS", details), patch.object(importer, "VOD_INDEX", index):
                with self.assertRaisesRegex(ValueError, "record without ID"):
                    importer.load_existing_details("movies")

    def test_corrupt_manifest_aborts_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            details, index = self._setup_paths(root)
            index.write_text("{broken", encoding="utf-8")
            with patch.object(importer, "ROOT", root), patch.object(importer, "DETAILS", details), patch.object(importer, "VOD_INDEX", index):
                with self.assertRaisesRegex(ValueError, "index.json is unreadable"):
                    importer.load_existing_details("movies")


if __name__ == "__main__":
    unittest.main()
