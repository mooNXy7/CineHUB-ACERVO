import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_catalogo_channel_sources import (
    build_report,
    parse_catalogo,
    safe_reference_stream,
)


class CatalogoChannelSourceTests(unittest.TestCase):
    def test_accepts_public_https_candidate_without_claiming_it_is_live(self):
        ok, reason = safe_reference_stream(
            "https://nexustvplay.bbroot.com/nxs/stream/ae/ae.m3u8"
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "eligible_unverified")

    def test_rejects_http_and_sensitive_query(self):
        self.assertFalse(safe_reference_stream("http://example.com/live.m3u8")[0])
        self.assertEqual(
            safe_reference_stream("https://example.com/live.m3u8?token=abc")[1],
            "sensitive_query",
        )

    def test_rejects_direct_and_base64_encoded_credential_paths(self):
        self.assertEqual(
            safe_reference_stream("https://example.com/live/user123/pass456/stream.m3u8")[1],
            "credential_path",
        )
        encoded = base64.urlsafe_b64encode(
            b"http://origin.example/live/user123/pass456/71760.m3u8"
        ).decode().rstrip("=")
        self.assertEqual(
            safe_reference_stream(f"https://relay.example/relay/m/{encoded}.m3u8")[1],
            "encoded_credential_path",
        )

    def test_rejects_opaque_hex_path_tokens(self):
        self.assertEqual(
            safe_reference_stream(
                "https://cdn.example/8e8e8b142192ea65/stream.m3u8"
            )[1],
            "opaque_path_token",
        )

    def test_parser_keeps_source_order_and_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalogo.txt"
            path.write_text(
                "canal: A&E\n"
                "categoria: Documentários\n"
                "fonte: https://one.example/ae.m3u8\n"
                "qualidade: FHD\n"
                "fonte: https://two.example/ae.m3u8\n"
                "qualidade: HD\n",
                encoding="utf-8",
            )
            rows = parse_catalogo(path)
        self.assertEqual([x["source_order"] for x in rows[0]["sources"]], [1, 2])
        self.assertEqual([x["quality"] for x in rows[0]["sources"]], ["FHD", "HD"])

    def test_report_only_lists_exact_matches_without_existing_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channels = root / "channels.json"
            reference = root / "catalogo.txt"
            output = root / "report.json"
            channels.write_text(json.dumps({
                "channels": [
                    {"id": "a", "name": "A&E", "sources": []},
                    {"id": "b", "name": "AMC", "sources": [{"url": "https://live.example/amc.m3u8"}]},
                    {"id": "c1", "name": "History", "sources": []},
                    {"id": "c2", "name": "History", "sources": []},
                ]
            }), encoding="utf-8")
            reference.write_text(
                "canal: A&E\nfonte: https://live.example/ae.m3u8\n"
                "canal: AMC\nfonte: https://live.example/amc2.m3u8\n"
                "canal: History\nfonte: https://live.example/history.m3u8\n"
                "canal: Unknown\nfonte: https://live.example/unknown.m3u8\n",
                encoding="utf-8",
            )
            report = build_report(channels, reference, output)
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual(report["counts"]["channels_with_candidates"], 1)
        self.assertEqual(report["candidates"][0]["channel_id"], "a")
        self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
