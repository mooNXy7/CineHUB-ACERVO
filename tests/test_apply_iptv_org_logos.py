import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_iptv_org_logos import apply


class IptvOrgLogoTests(unittest.TestCase):
    def make_root(self, channels, records):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )
        source = root / "logos.json"
        source.write_text(json.dumps(records), encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root, source

    def test_applies_unique_in_use_channel_logo(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "CNN Brasil HD", "logo_url": None}],
            [{"channel": "CNNBrasil.br", "feed": None, "in_use": True,
              "url": "https://logos.example/cnn-brasil.svg", "format": "SVG"}],
        )
        result = apply(root, source, verify_image=lambda _: True)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://logos.example/cnn-brasil.svg")

    def test_ignores_unused_and_feed_specific_logos(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "CNN Brasil", "logo_url": None}],
            [{"channel": "CNNBrasil.br", "feed": None, "in_use": False,
              "url": "https://logos.example/old.svg"},
             {"channel": "CNNBrasil.br", "feed": "Regional", "in_use": True,
              "url": "https://logos.example/feed.svg"}],
        )
        result = apply(root, source, verify_image=lambda _: True)
        self.assertEqual(result["applied"], 0)

    def test_ambiguous_active_logos_are_not_guessed(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "CNN Brasil", "logo_url": None}],
            [{"channel": "CNNBrasil.br", "feed": None, "in_use": True,
              "url": "https://logos.example/one.svg"},
             {"channel": "CNNBrasil.br", "feed": None, "in_use": True,
              "url": "https://logos.example/two.svg"}],
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)

    def test_never_overwrites_existing_logo(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "CNN Brasil", "logo_url": "https://old.example/logo.png"}],
            [{"channel": "CNNBrasil.br", "feed": None, "in_use": True,
              "url": "https://logos.example/cnn.svg"}],
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)


if __name__ == "__main__":
    unittest.main()
