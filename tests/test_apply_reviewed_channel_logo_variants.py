import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_reviewed_channel_logo_variants


class ReviewedChannelLogoVariantTests(unittest.TestCase):
    def make_root(self, channels, references, reviewed):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for relative, value in {
            "catalog/channels/channels.json": {"channels": channels},
            "catalog/reference/saimo-channel-logos.json": {"entries": references},
            "catalog/reference/reviewed-channel-logo-variants.json": {
                "reviewed_variants": reviewed,
            },
        }.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return root

    def test_applies_only_allowlisted_quality_variant_and_preserves_other_fields(self):
        root = self.make_root(
            [{"id": "ch-example-hd", "name": "Example Channel HD", "logo_url": None,
              "sources": [{"url": "https://stream.example/live"}], "epg_id": "Example"}],
            [{"name": "Example Channel", "logo_url": "https://logos.example/example.png"}],
            [{"channel_id": "ch-example-hd", "reference_name": "Example Channel"}],
        )
        result = apply_reviewed_channel_logo_variants.apply(root)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 1)
        self.assertEqual(channel["logo_url"], "https://logos.example/example.png")
        self.assertEqual(channel["sources"], [{"url": "https://stream.example/live"}])
        self.assertEqual(channel["epg_id"], "Example")

    def test_does_not_apply_unlisted_quality_variant(self):
        root = self.make_root(
            [{"id": "ch-example-hd", "name": "Example Channel HD", "logo_url": None}],
            [{"name": "Example Channel", "logo_url": "https://logos.example/example.png"}],
            [],
        )
        result = apply_reviewed_channel_logo_variants.apply(root)
        self.assertEqual(result["applied"], 0)

    def test_never_overwrites_existing_logo(self):
        root = self.make_root(
            [{"id": "ch-example-hd", "name": "Example Channel HD",
              "logo_url": "https://existing.example/logo.png"}],
            [{"name": "Example Channel", "logo_url": "https://logos.example/example.png"}],
            [{"channel_id": "ch-example-hd", "reference_name": "Example Channel"}],
        )
        result = apply_reviewed_channel_logo_variants.apply(root)
        channel = json.loads((root / "catalog/channels/channels.json").read_text())["channels"][0]
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_existing"], 1)
        self.assertEqual(channel["logo_url"], "https://existing.example/logo.png")

    def test_rejects_mismatched_reviewed_reference_name(self):
        root = self.make_root(
            [{"id": "ch-example-hd", "name": "Example Channel HD", "logo_url": None}],
            [{"name": "Example Channel", "logo_url": "https://logos.example/example.png"}],
            [{"channel_id": "ch-example-hd", "reference_name": "Different Channel"}],
        )
        result = apply_reviewed_channel_logo_variants.apply(root)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_mismatch"], 1)

    def test_rejects_ambiguous_reference_logos(self):
        root = self.make_root(
            [{"id": "ch-example-hd", "name": "Example Channel HD", "logo_url": None}],
            [
                {"name": "Example Channel", "logo_url": "https://logos.example/one.png"},
                {"name": "Example Channel", "logo_url": "https://logos.example/two.png"},
            ],
            [{"channel_id": "ch-example-hd", "reference_name": "Example Channel"}],
        )
        result = apply_reviewed_channel_logo_variants.apply(root)
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_invalid"], 1)


if __name__ == "__main__":
    unittest.main()
