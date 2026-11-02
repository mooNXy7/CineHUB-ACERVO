import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_saimoplayer_m3u_logos import apply


class SaimoPlayerM3ULogoTests(unittest.TestCase):
    def make_root(self, channels, m3u):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )
        source = root / "reference.m3u"
        source.write_text(m3u, encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root, source

    def test_applies_verified_tvg_logo_only(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Warner Channel HD", "logo_url": None,
              "sources": [{"url": "https://existing.example/live"}]}],
            '#EXTM3U\n#EXTINF:-1 tvg-name="Warner" tvg-id="Warner" tvg-logo="https://logos.example/warner.png",Warner Channel\nhttps://ignored.example/live\n',
        )
        result = apply(root, source, verify_image=lambda _: True)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://logos.example/warner.png")
        self.assertEqual(channel["sources"], [{"url": "https://existing.example/live"}])

    def test_does_not_overwrite_existing_logo(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": "https://old.example/a.png"}],
            '#EXTINF:-1 tvg-name="Band" tvg-logo="https://logos.example/band.png",Band\n',
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)

    def test_rejects_http_and_sensitive_query_urls(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": None}],
            '#EXTINF:-1 tvg-name="Band" tvg-logo="http://logos.example/band.png",Band\n',
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)

    def test_ambiguous_brand_urls_are_not_applied(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": None}],
            '#EXTINF:-1 tvg-name="Band" tvg-logo="https://logos.example/one.png",Band\n'
            '#EXTINF:-1 tvg-name="Band" tvg-logo="https://logos.example/two.png",Band\n',
        )
        self.assertEqual(apply(root, source, verify_image=lambda _: True)["applied"], 0)


if __name__ == "__main__":
    unittest.main()
