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

    def test_unknown_channel_without_override_or_embedded_id_returns_none(self):
        self.assertIsNone(update_epg.pluto_id_for_channel({"id": "ch-unknown", "name": "Unknown"}, {}))


if __name__ == "__main__":
    unittest.main()
