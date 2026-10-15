import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_catalog import merge_channels, parse_m3u, safe_https_url


class CatalogShapeTests(unittest.TestCase):
    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_channels_shape(self):
        data = self.load("catalog/channels/channels.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["channels"], list)

    def test_radios_shape(self):
        data = self.load("catalog/radios/radios.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["radios"], list)

    def test_vod_categories(self):
        data = self.load("catalog/vod/index.json")
        for category in ("movies", "series", "anime", "doramas"):
            self.assertIsInstance(data[category], list)


class SourceSafetyTests(unittest.TestCase):
    def test_accepts_public_https_url(self):
        self.assertTrue(safe_https_url("https://example.com/list.m3u"))

    def test_rejects_http_url(self):
        self.assertFalse(safe_https_url("http://example.com/live.m3u"))

    def test_rejects_embedded_credentials(self):
        self.assertFalse(safe_https_url("https://user:pass@example.com/live"))

    def test_rejects_local_and_private_hosts(self):
        for url in (
            "https://localhost/list.m3u",
            "https://192.168.1.10/live",
            "https://127.0.0.1/live",
            "https://printer.local/list",
        ):
            with self.subTest(url=url):
                self.assertFalse(safe_https_url(url))

    def test_m3u_parser_keeps_only_safe_https_streams(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-name="Canal Exemplo" group-title="Brasil",Canal Exemplo
https://cdn.example.org/channel.m3u8
#EXTINF:-1 tvg-name="Canal HTTP",Canal HTTP
http://cdn.example.org/channel.m3u8
#EXTINF:-1 tvg-name="Canal com credencial",Canal com credencial
https://user:pass@cdn.example.org/channel.m3u8
"""
        channels = parse_m3u(text, "test-source", 1)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["name"], "Canal Exemplo")
        self.assertEqual(channels[0]["group"], "Brasil")
        self.assertEqual(channels[0]["sources"][0]["source_id"], "test-source")

    def test_merge_preserves_existing_metadata_and_deduplicates_sources(self):
        existing = [{
            "id": "ch-canal-exemplo",
            "name": "Canal Exemplo",
            "group": "Grupo Curado",
            "logo_url": "https://logos.example.org/canal.png",
            "sources": [{"url": "https://cdn.example.org/old.m3u8", "priority": 5}],
        }]
        incoming = [{
            "id": "ch-canal-exemplo",
            "name": "Canal Exemplo",
            "group": "Grupo Fonte",
            "logo_url": "https://logos.example.org/new.png",
            "sources": [
                {"url": "https://cdn.example.org/old.m3u8", "priority": 5},
                {"url": "https://cdn.example.org/new.m3u8", "priority": 1},
            ],
        }]
        merged, added = merge_channels(existing, incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["group"], "Grupo Curado")
        self.assertEqual(merged[0]["logo_url"], "https://logos.example.org/canal.png")
        self.assertEqual(len(merged[0]["sources"]), 2)
        self.assertEqual(added, 1)


if __name__ == "__main__":
    unittest.main()
