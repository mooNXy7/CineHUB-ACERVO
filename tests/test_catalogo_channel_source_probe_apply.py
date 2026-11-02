import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_catalogo_channel_sources import apply_verified_sources
from scripts.probe_catalogo_channel_sources import classify_payload


class CatalogoChannelProbeTests(unittest.TestCase):
    def test_hls_requires_m3u_header(self):
        self.assertEqual(classify_payload(b"#EXTM3U\n#EXT-X-VERSION:3", "hls"), "hls_ok")
        self.assertEqual(classify_payload(b"<html>blocked</html>", "hls"), "invalid_playlist")

    def test_dash_requires_mpd_payload(self):
        self.assertEqual(classify_payload(b"<?xml version='1.0'?><MPD></MPD>", "dash"), "dash_ok")
        self.assertEqual(classify_payload(b"not a manifest", "dash"), "unknown_format")


class CatalogoChannelApplyTests(unittest.TestCase):
    def test_applies_only_hls_ok_and_preserves_existing_catalog_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channels = root / "channels.json"
            candidates = root / "candidates.json"
            health = root / "health.json"
            output = root / "application.json"
            channels.write_text(json.dumps({
                "generated_at": "old",
                "channels": [
                    {"id": "a", "name": "A&E", "sources": [], "logo_url": "https://img.example/ae.png", "epg_id": "A&E"},
                    {"id": "b", "name": "AMC", "sources": [{"url": "https://old.example/amc.m3u8"}]},
                ],
            }), encoding="utf-8")
            candidates.write_text(json.dumps({"candidates": [
                {"channel_id": "a", "sources": [
                    {"url": "https://good.example/ae.m3u8", "source_order": 1, "source_type": "hls", "headers": {}},
                    {"url": "https://bad.example/ae.m3u8", "source_order": 2, "source_type": "hls", "headers": {}},
                    {"url": "https://dash.example/ae.mpd", "source_order": 3, "source_type": "dash", "headers": {}},
                ]},
                {"channel_id": "b", "sources": [
                    {"url": "https://new.example/amc.m3u8", "source_order": 1, "source_type": "hls", "headers": {}},
                ]},
            ]}), encoding="utf-8")
            health.write_text(json.dumps({"results": [
                {"channel_id": "a", "source_order": 1, "probe_status": "hls_ok"},
                {"channel_id": "a", "source_order": 2, "probe_status": "invalid_playlist"},
                {"channel_id": "a", "source_order": 3, "probe_status": "dash_ok"},
                {"channel_id": "b", "source_order": 1, "probe_status": "hls_ok"},
            ]}), encoding="utf-8")
            report = apply_verified_sources(channels, candidates, health, output)
            saved = json.loads(channels.read_text(encoding="utf-8"))
            self.assertTrue(output.exists())
        self.assertTrue(report["catalog_mutated"])
        self.assertEqual(report["counts"]["channels_updated"], 1)
        self.assertEqual(report["counts"]["hls_sources_added"], 1)
        self.assertEqual(saved["channels"][0]["sources"][0]["source_id"], "saimoplayer-catalogo")
        self.assertEqual(saved["channels"][0]["logo_url"], "https://img.example/ae.png")
        self.assertEqual(saved["channels"][0]["epg_id"], "A&E")
        self.assertEqual(saved["channels"][1]["sources"][0]["url"], "https://old.example/amc.m3u8")


if __name__ == "__main__":
    unittest.main()
