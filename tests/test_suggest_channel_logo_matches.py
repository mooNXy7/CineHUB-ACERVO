import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_channel_logo_matches import build_report


class SuggestChannelLogoMatchesTests(unittest.TestCase):
    def test_exact_name_suggestions_are_read_only_and_only_fill_blanks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/channels").mkdir(parents=True)
            (root / "catalog/reference").mkdir(parents=True)
            channels_path = root / "catalog/channels/channels.json"
            channels_path.write_text(json.dumps({"channels": [
                {"id": "c1", "name": "Canal Árvore HD", "logo_url": None},
                {"id": "c2", "name": "Já tem logo", "logo_url": "https://old.example/logo.png"},
                {"id": "c3", "name": "Sem referência", "logo_url": ""},
            ]}), encoding="utf-8")
            (root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps({
                "source": "https://example.org/reference",
                "entries": [
                    {"name": "Canal Arvore HD", "logo_url": "https://logos.example/arvore.png"},
                ],
            }), encoding="utf-8")
            before = channels_path.read_text(encoding="utf-8")
            report = build_report(root)
            after = channels_path.read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["catalog_mutated"])
        self.assertFalse(report["stream_or_drm_data_imported"])
        self.assertTrue(report["quality_markers_preserved"])
        self.assertEqual(report["counts"]["candidate_channels"], 1)
        self.assertEqual(report["counts"]["channels_missing_logo_examined"], 2)
        self.assertEqual(report["counts"]["no_reference_match"], 1)
        self.assertEqual(report["suggestions"][0]["channel_id"], "c1")
        self.assertFalse(report["suggestions"][0]["automatic_update"])

    def test_quality_variants_do_not_match_automatically(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/channels").mkdir(parents=True)
            (root / "catalog/reference").mkdir(parents=True)
            (root / "catalog/channels/channels.json").write_text(json.dumps({
                "channels": [{"id": "c1", "name": "Canal HD", "logo_url": None}]
            }), encoding="utf-8")
            (root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps({
                "entries": [{"name": "Canal", "logo_url": "https://logos.example/a.png"}]
            }), encoding="utf-8")
            report = build_report(root)

        self.assertEqual(report["counts"]["candidate_channels"], 0)
        self.assertEqual(report["counts"]["no_reference_match"], 1)

    def test_ambiguous_logo_matches_are_not_suggested(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/channels").mkdir(parents=True)
            (root / "catalog/reference").mkdir(parents=True)
            (root / "catalog/channels/channels.json").write_text(json.dumps({
                "channels": [{"id": "c1", "name": "Band", "logo_url": None}]
            }), encoding="utf-8")
            (root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps({
                "entries": [
                    {"name": "Band", "logo_url": "https://logos.example/a.png"},
                    {"name": "Band", "logo_url": "https://logos.example/b.png"},
                ]
            }), encoding="utf-8")
            report = build_report(root)

        self.assertEqual(report["counts"]["candidate_channels"], 0)
        self.assertEqual(report["counts"]["ambiguous_reference_matches"], 1)


if __name__ == "__main__":
    unittest.main()
