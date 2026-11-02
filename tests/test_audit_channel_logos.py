import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_channel_logos import build_report


class ChannelLogoAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "catalog/channels").mkdir(parents=True)
        (self.root / "catalog/reference").mkdir(parents=True)
        catalog = {
            "channels": [
                {"id": "one", "name": "Alpha TV", "logo_url": "https://cdn.example/alpha.png"},
                {"id": "two", "name": "Beta", "logo_url": "http://cdn.example/shared.png"},
                {"id": "three", "name": "Gamma", "logo_url": ""},
                {"id": "four", "name": "Delta", "logo_url": "http://cdn.example/shared.png"},
            ]
        }
        refs = {
            "entries": [
                {"name": "Alpha TV", "logo_url": "https://cdn.example/alpha.png"},
                {"name": "Beta", "logo_url": "https://cdn.example/beta.png"},
                {"name": "Gamma", "logo_url": "https://cdn.example/gamma.png"},
            ]
        }
        variants = {"reviewed_variants": [
            {"channel_id": "one", "reference_name": "Alpha TV"},
            {"channel_id": "two", "reference_name": "Beta"},
        ]}
        (self.root / "catalog/channels/channels.json").write_text(json.dumps(catalog), encoding="utf-8")
        (self.root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps(refs), encoding="utf-8")
        (self.root / "catalog/reference/reviewed-channel-logo-variants.json").write_text(json.dumps(variants), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_counts_applied_missing_http_and_reference_disagreement(self):
        report = build_report(self.root)
        counts = report["counts"]
        self.assertEqual(counts["channels_total"], 4)
        self.assertEqual(counts["channels_with_logo"], 3)
        self.assertEqual(counts["channels_missing_logo"], 1)
        self.assertEqual(counts["logo_urls_https"], 1)
        self.assertEqual(counts["logo_urls_http"], 2)
        self.assertEqual(counts["catalog_exact_name_reference_matches"], 3)
        self.assertEqual(counts["exact_name_matches_with_same_url"], 1)
        self.assertEqual(counts["exact_name_matches_with_different_url"], 1)
        self.assertEqual(counts["missing_channels_with_exact_reference"], 1)
        self.assertEqual(counts["reviewed_variants_with_catalog_logo_applied"], 2)
        self.assertEqual(counts["reviewed_variants_with_exact_reference_logo_applied"], 1)
        self.assertEqual(counts["reviewed_variants_with_nonmatching_catalog_logo"], 1)
        self.assertEqual(counts["reviewed_variants_with_missing_reference"], 0)

    def test_shared_logo_urls_are_informational_not_invalid(self):
        report = build_report(self.root)
        counts = report["counts"]
        self.assertEqual(counts["shared_logo_url_groups"], 1)
        self.assertEqual(counts["channels_using_shared_logo_urls"], 2)
        self.assertEqual(counts["malformed_logo_urls"], 0)

    def test_audit_is_read_only(self):
        path = self.root / "catalog/channels/channels.json"
        before = path.read_text(encoding="utf-8")
        build_report(self.root)
        self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
