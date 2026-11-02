import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_epg


class PlutoIdOverrideTests(unittest.TestCase):
    def test_reviewed_override_is_used_for_channel_without_embedded_pluto_id(self):
        channel = {"id": "ch-avatar-a-lenda-de-aang-24h", "name": "Avatar A Lenda de Aang 24H"}
        overrides = {"ch-avatar-a-lenda-de-aang-24h": "6759eeb1bd523200083b4f29"}
        self.assertEqual(update_epg.pluto_id_for_channel(channel, overrides), "6759eeb1bd523200083b4f29")

    def test_invalid_override_falls_back_to_logo_or_stream_pattern(self):
        channel = {
            "id": "ch-avatar",
            "logo_url": "https://images.pluto.tv/channels/6759eeb1bd523200083b4f29/colorLogoPNG.png",
            "sources": [],
        }
        self.assertEqual(
            update_epg.pluto_id_for_channel(channel, {"ch-avatar": "not-a-pluto-id"}),
            "6759eeb1bd523200083b4f29",
        )

    def test_normalise_removes_codec_and_quality_markers_but_keeps_channel_number(self):
        self.assertEqual(update_epg.normalise("A&E FHD [H265]"), update_epg.normalise("A&E"))
        self.assertEqual(update_epg.normalise("AXN HD [LEG]"), update_epg.normalise("AXN"))
        self.assertNotEqual(update_epg.normalise("SporTV 2 FHD"), update_epg.normalise("SporTV 3 FHD"))

    def test_unique_xmltv_ids_skips_ambiguous_name_within_a_source(self):
        ids, ambiguous = update_epg.unique_xmltv_ids({
            "history": ["history.br"],
            "space": ["space.one", "space.two"],
        }, ["history", "space"])
        self.assertEqual(ids, ["history.br"])
        self.assertEqual(ambiguous, ["space"])

    def test_unknown_channel_without_override_or_embedded_id_returns_none(self):
        self.assertIsNone(update_epg.pluto_id_for_channel({"id": "ch-unknown", "name": "Unknown"}, {}))


if __name__ == "__main__":
    unittest.main()
