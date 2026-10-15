import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CatalogShapeTests(unittest.TestCase):
    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_channels_shape(self):
        data = self.load("catalog/channels/channels.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["channels"], list)

    def test_radios_shape(self):
        data = self.load("catalog/radios/radios.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["radios"], list)

    def test_vod_categories(self):
        data = self.load("catalog/vod/index.json")
        for category in ("movies", "series", "anime", "doramas"):
            self.assertIsInstance(data[category], list)

if __name__ == "__main__":
    unittest.main()
