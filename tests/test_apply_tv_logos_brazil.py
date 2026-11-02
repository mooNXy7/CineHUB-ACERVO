import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_tv_logos_brazil import apply


class TvLogosBrazilTests(unittest.TestCase):
    def make_root(self, channels, entries):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(
            json.dumps({"channels": channels}), encoding="utf-8"
        )
        index = root / "logos.json"
        index.write_text(json.dumps(entries), encoding="utf-8")
        self.addCleanup(temp.cleanup)
        return root, index

    def entry(self, name, path=None, host="raw.githubusercontent.com", size=100):
        filename = path or name
        return {
            "name": filename,
            "path": "countries/brazil/" + filename,
            "size": size,
            "download_url": f"https://{host}/tv-logo/tv-logos/main/countries/brazil/{filename}",
        }

    def test_applies_unique_exact_logo_and_preserves_other_fields(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "Canal Brasil HD", "logo_url": None,
              "sources": [{"url": "https://stream.example/live"}]}],
            [self.entry("canal-brasil-br.png")],
        )
        result = apply(root, index)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/brazil/canal-brasil-br.png")
        self.assertEqual(channel["sources"], [{"url": "https://stream.example/live"}])

    def test_accepts_international_logo_index_entries(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "CNN International", "logo_url": None}],
            [{
                "name": "cnn-international-int.png",
                "path": "countries/international/cnn-international-int.png",
                "size": 100,
                "download_url": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/international/cnn-international-int.png",
            }],
        )
        result = apply(root, index)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertIn("/countries/international/", channel["logo_url"])

    def test_explicit_alias_handles_a_and_e(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "A&E", "logo_url": None}],
            [self.entry("a-and-e-br.png")],
        )
        self.assertEqual(apply(root, index)["applied"], 1)

    def test_never_overwrites_existing_logo(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": "https://old.example/logo.png"}],
            [self.entry("band-br.png")],
        )
        self.assertEqual(apply(root, index)["applied"], 0)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(channel["logo_url"], "https://old.example/logo.png")

    def test_ambiguous_source_matches_are_not_applied(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": None}],
            [self.entry("band-br.png"), self.entry("band-br.svg")],
        )
        self.assertEqual(apply(root, index)["ambiguous"], 1)

    def test_rejects_untrusted_hosts_and_paths(self):
        root, index = self.make_root(
            [{"id": "c1", "name": "Band", "logo_url": None}],
            [self.entry("band-br.png", host="evil.example")],
        )
        result = apply(root, index)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["no_verified_source_match"], 1)


if __name__ == "__main__":
    unittest.main()
