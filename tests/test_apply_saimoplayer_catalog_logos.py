import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_saimoplayer_catalog_logos import apply


class SaimoPlayerLogoApplicationTests(unittest.TestCase):
    def make_root(self, channels, source):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )
        source_file = root / "catalogo.txt"
        source_file.write_text(source, encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root, source_file

    def test_applies_live_verified_logo_and_preserves_streams(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Warner Channel HD", "logo_url": None,
              "sources": [{"url": "https://stream.example/live"}]}],
            "canal: Warner\nlogo: https://logos.example/warner.png\nfonte: https://ignored.example/live\n",
        )
        result = apply(root, source, verify_image=lambda _: True)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://logos.example/warner.png")
        self.assertEqual(channel["sources"], [{"url": "https://stream.example/live"}])

    def test_ignores_credentials_and_non_https_logo_urls(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Example", "logo_url": None}],
            "canal: Example\nlogo: http://logos.example/a.png\n",
        )
        result = apply(root, source, verify_image=lambda _: True)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["invalid_or_unreachable_images"], 1)

    def test_never_overwrites_existing_logo(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Example", "logo_url": "https://old.example/a.png"}],
            "canal: Example\nlogo: https://logos.example/a.png\n",
        )
        result = apply(root, source, verify_image=lambda _: True)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_existing"], 1)

    def test_ambiguous_source_aliases_are_not_guessed(self):
        root, source = self.make_root(
            [{"id": "c1", "name": "Example", "logo_url": None}],
            "canal: Example\nlogo: https://logos.example/a.png\n\n"
            "canal: Example\nlogo: https://logos.example/b.png\n",
        )
        result = apply(root, source, verify_image=lambda _: True)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["ambiguous_source_matches"], 1)


if __name__ == "__main__":
    unittest.main()
