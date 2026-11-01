import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_saimotv_channel_reference as importer


class SaimoTVChannelReferenceTests(unittest.TestCase):
    def test_imports_only_safe_non_drm_hls_into_exact_missing_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog/channels").mkdir(parents=True)
            channels = {
                "schema_version": 1,
                "channels": [
                    {"id": "ch-cazetv-hd", "name": "CazéTV HD", "sources": [], "logo_url": "https://logos.example/caze.png"},
                    {"id": "ch-cnn-brasil", "name": "CNN Brasil", "sources": []},
                    {"id": "ch-sbt", "name": "SBT", "sources": []},
                    {"id": "ch-tv-brasil", "name": "TV Brasil", "sources": [{"url": "https://existing.example/live.m3u8"}]},
                ],
            }
            (root / "catalog/channels/channels.json").write_text(json.dumps(channels), encoding="utf-8")
            reference = {
                "data": [
                    {"name": "CazéTV", "drm_system": {"clearKey": "", "widevine": ""},
                     "streams": [{"url": "https://cdn.example/caze/index.m3u8", "quality": "HD",
                                  "headers": {"user-agent": "CineHUB-Test", "referer": "https://caze.example/", "origin": "https://caze.example", "authorization": "Bearer secret", "cookie": "session=secret"}}]},
                    {"name": "CNN Brasil", "drm_system": {"clearKey": "secret", "widevine": ""},
                     "streams": [{"url": "https://cdn.example/cnn/index.m3u8", "quality": "HD"}]},
                    {"name": "SBT", "drm_system": {"clearKey": "", "widevine": ""},
                     "streams": [{"url": "http://cdn.example/sbt/index.m3u8", "quality": "HD"}]},
                    {"name": "TV Brasil", "drm_system": {"clearKey": "", "widevine": ""},
                     "streams": [{"url": "https://cdn.example/tvbrasil/index.m3u8", "quality": "HD"}]},
                ],
            }
            reference_file = root / "offline.json"
            reference_file.write_text(json.dumps(reference), encoding="utf-8")

            report = importer.update(root, reference_file)
            saved = json.loads((root / "catalog/channels/channels.json").read_text(encoding="utf-8"))
            by_id = {item["id"]: item for item in saved["channels"]}

            self.assertEqual(by_id["ch-cazetv-hd"]["sources"][0]["url"], "https://cdn.example/caze/index.m3u8")
            self.assertEqual(by_id["ch-cazetv-hd"]["sources"][0]["user_agent"], "CineHUB-Test")
            self.assertEqual(by_id["ch-cazetv-hd"]["sources"][0]["referer"], "https://caze.example/")
            self.assertNotIn("origin", by_id["ch-cazetv-hd"]["sources"][0])
            self.assertNotIn("authorization", by_id["ch-cazetv-hd"]["sources"][0])
            self.assertNotIn("cookie", by_id["ch-cazetv-hd"]["sources"][0])
            self.assertEqual(by_id["ch-cazetv-hd"]["logo_url"], "https://logos.example/caze.png")
            self.assertEqual(by_id["ch-cnn-brasil"]["sources"], [])
            self.assertEqual(by_id["ch-sbt"]["sources"], [])
            self.assertEqual(by_id["ch-tv-brasil"]["sources"], [{"url": "https://existing.example/live.m3u8"}])
            self.assertEqual(report["counts"]["streams_added"], 1)
            self.assertEqual(report["counts"]["skipped_drm"], 1)
            self.assertEqual(report["counts"]["skipped_unsafe"], 1)
            self.assertEqual(report["counts"]["already_has_stream"], 1)

    def test_broadcaster_name_spacing_and_accents_are_normalized(self):
        self.assertEqual(
            importer.normalize_channel_name("CazéTV HD"),
            importer.normalize_channel_name("Caze TV"),
        )

    def test_quality_variant_selects_matching_channel_and_leaves_other_variants(self):
        channels = [
            {"id": "ch-jp-hd", "name": "Jovem Pan News HD"},
            {"id": "ch-jp-sd", "name": "Jovem Pan News SD"},
        ]
        target = importer.choose_channel(channels, "HD")
        self.assertEqual(target["id"], "ch-jp-hd")

    def test_ambiguous_quality_variants_are_not_guessed(self):
        channels = [
            {"id": "ch-jp-hd-1", "name": "Jovem Pan News HD"},
            {"id": "ch-jp-hd-2", "name": "Jovem Pan News HD"},
        ]
        self.assertIsNone(importer.choose_channel(channels, "HD"))

    def test_rejects_non_hls_and_sensitive_stream_paths(self):
        record = {"drm_system": {"clearKey": "", "widevine": ""}}
        self.assertFalse(importer.source_is_safe({"url": "https://cdn.example/live/user/pass/stream.m3u8"}, record))
        self.assertFalse(importer.source_is_safe({"url": "https://cdn.example/live.mpd"}, record))
        self.assertTrue(importer.source_is_safe({"url": "https://cdn.example/live/index.m3u8"}, record))


if __name__ == "__main__":
    unittest.main()
