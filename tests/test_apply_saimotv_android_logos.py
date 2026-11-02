import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_saimotv_android_logos import apply


class SaimoTvAndroidLogoTests(unittest.TestCase):
    def make_root(self, channels, records):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )
        source = root / "offline.json"
        source.write_text(json.dumps({"data": records}), encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root, source

    def test_applies_unique_live_logo_by_normalized_brand(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Adult Swim HD", "logo_url": None,
              "sources": [{"url": "https://stream.example/live"}]}],
            [{"name": "Adult Swim", "logo": "https://logos.example/adult-swim.png",
              "streams": [{"url": "https://must-not-import.example/live"}],
              "drm_system": {"clearKey": "secret"}}],
        )
        result = apply(root, source, verify_image=lambda _: True)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://logos.example/adult-swim.png")
        self.assertEqual(channel["sources"], [{"url": "https://stream.example/live"}])
        self.assertNotIn("drm_system", channel)

    def test_never_overwrites_existing_logo(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "AMC", "logo_url": "https://old.example/logo.png"}],
            [{"name": "AMC", "logo": "https://logos.example/amc.png"}],
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)

    def test_rejects_ambiguous_reference_urls(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "AMC", "logo_url": None}],
            [{"name": "AMC", "logo": "https://logos.example/a.png"},
             {"name": "AMC", "logo": "https://logos.example/b.png"}],
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)

    def test_rejects_http_and_sensitive_urls(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "AMC", "logo_url": None}],
            [{"name": "AMC", "logo": "http://logos.example/a.png"}],
        )
        result = apply(root, source, verify_image=lambda _: True)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["unmatched_catalog_keys"], 1)


if __name__ == "__main__":
    unittest.main()
