import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_channel_logo_matches import build_report
from scripts.apply_exact_channel_logo_suggestions import apply


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
        self.assertEqual(report["counts"]["candidate_channels"], 1)
        self.assertEqual(report["counts"]["higher_confidence_exact_candidates"], 1)
        self.assertEqual(report["counts"]["lower_confidence_quality_marker_candidates"], 0)
        self.assertEqual(report["counts"]["channels_missing_logo_examined"], 2)
        self.assertEqual(report["counts"]["no_reference_match"], 1)
        self.assertEqual(report["suggestions"][0]["channel_id"], "c1")
        self.assertFalse(report["suggestions"][0]["automatic_update"])

    def test_quality_variant_is_separated_as_lower_confidence(self):
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

        self.assertEqual(report["counts"]["candidate_channels"], 1)
        self.assertEqual(report["counts"]["higher_confidence_exact_candidates"], 0)
        self.assertEqual(report["counts"]["lower_confidence_quality_marker_candidates"], 1)
        self.assertEqual(report["suggestions"][0]["confidence"], "lower")
        self.assertFalse(report["suggestions"][0]["automatic_update"])

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


    def test_apply_updates_only_exact_logos_and_preserves_stream_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/channels").mkdir(parents=True)
            (root / "catalog/reference").mkdir(parents=True)
            channels_path = root / "catalog/channels/channels.json"
            channels_path.write_text(json.dumps({"channels": [
                {"id": "c1", "name": "Film&Arts", "logo_url": None, "stream_url": "https://stream.example/1"},
                {"id": "c2", "name": "France 24 HD", "logo_url": "", "stream_url": "https://stream.example/2"},
                {"id": "c3", "name": "Already", "logo_url": "https://old.example/logo.png",
                 "stream_url": "https://stream.example/3"},
            ]}), encoding="utf-8")
            (root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps({
                "source": "https://example.org/reference",
                "entries": [
                    {"name": "Film & Arts", "logo_url": "https://logos.example/film-arts.png"},
                    {"name": "France 24", "logo_url": "https://logos.example/france24.png"},
                ],
            }), encoding="utf-8")

            result = apply(root)
            updated = json.loads(channels_path.read_text(encoding="utf-8"))["channels"]

        by_id = {item["id"]: item for item in updated}
        self.assertEqual(result["applied"], 1)
        self.assertEqual(result["skipped_lower_confidence"], 1)
        self.assertTrue(result["catalog_mutated"])
        self.assertEqual(by_id["c1"]["logo_url"], "https://logos.example/film-arts.png")
        self.assertEqual(by_id["c2"]["logo_url"], "")
        self.assertEqual(by_id["c3"]["logo_url"], "https://old.example/logo.png")
        self.assertEqual(by_id["c1"]["stream_url"], "https://stream.example/1")
        self.assertEqual(by_id["c2"]["stream_url"], "https://stream.example/2")
        self.assertEqual(by_id["c3"]["stream_url"], "https://stream.example/3")


    def test_codec_markers_are_removed_for_reviewed_quality_variants(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "catalog/channels").mkdir(parents=True)
            (root / "catalog/reference").mkdir(parents=True)
            (root / "catalog/channels/channels.json").write_text(json.dumps({
                "channels": [{
                    "id": "c1",
                    "name": "CNN Brasil Money FHD [H265]",
                    "logo_url": None,
                }]
            }), encoding="utf-8")
            (root / "catalog/reference/saimo-channel-logos.json").write_text(json.dumps({
                "entries": [{
                    "name": "CNN Brasil Money",
                    "logo_url": "https://logos.example/cnn-brasil-money.png",
                }]
            }), encoding="utf-8")
            report = build_report(root)

        self.assertEqual(report["counts"]["candidate_channels"], 1)
        self.assertEqual(report["counts"]["lower_confidence_quality_marker_candidates"], 1)
        self.assertEqual(report["suggestions"][0]["reference_name"], "CNN Brasil Money")
        self.assertEqual(report["suggestions"][0]["confidence"], "lower")
        self.assertFalse(report["suggestions"][0]["automatic_update"])


if __name__ == "__main__":
    unittest.main()
