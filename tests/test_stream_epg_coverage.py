import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_stream_epg_coverage import audit_coverage


class StreamEpgCoverageTests(unittest.TestCase):
    def test_structural_coverage_and_aliases_are_channel_specific(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "catalog/channels/channels.json": {
                    "schema_version": 1,
                    "channels": [
                        {"id": "a", "name": "History", "epg_id": "history.xml", "sources": [{"url": "https://example.org/a.m3u8"}]},
                        {"id": "b", "name": "Unknown Local", "sources": []},
                        {"id": "c", "name": "Sony Channel", "sources": [{"url": "https://example.org/c.m3u8"}]},
                    ],
                },
                "catalog/radios/radios.json": {
                    "schema_version": 1,
                    "radios": [{"id": "r1", "name": "Radio A", "stream_url": "https://example.org/radio"}],
                },
                "catalog/epg/channel-map.json": {
                    "meuguia_codes": {"History": "HIS", "History Alias": "HIS"}, "guiadetv_slugs": {"Sony Channel": "sony-channel", "Missing TV": "missing-tv"},
                    "xmltv_aliases": {"Sony Channel": ["Sony"]},
                },
                "catalog/epg/xmltv-channels.json": {
                    "sources": {"feed": {"channels": [
                        {"id": "history.xml", "display_names": ["History Channel"]},
                        {"id": "sony.xml", "display_names": ["Sony"]},
                    ]}},
                },
            }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = audit_coverage(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

            self.assertEqual(before, after)
            self.assertEqual(result["counts"]["channels"], 3)
            self.assertEqual(result["counts"]["channels_with_stream_reference"], 2)
            self.assertEqual(result["counts"]["channels_with_epg_association"], 2)
            self.assertEqual(result["counts"]["epg_ids_found_in_xmltv_index"], 1)
            self.assertEqual(result["examples_limited_to_25"]["no_epg_association"], ["Unknown Local"])
            self.assertEqual(result["coverage"]["channel_epg_structural_association_pct"], 66.67)
            self.assertEqual(result["counts"]["radios_with_stream_reference"], 1)
            self.assertEqual(result["epg_map_review"]["meuguia_map_entries"], 2)
            self.assertEqual(result["epg_map_review"]["meuguia_entries_without_exact_catalog_name"]["examples"], ["History Alias"])
            self.assertEqual(result["epg_map_review"]["guiadetv_entries_without_exact_catalog_name"]["examples"], ["Missing TV"])
            self.assertEqual(result["epg_map_review"]["duplicate_meuguia_codes"]["count"], 1)
            self.assertEqual(result["network_requests"], 0)
            self.assertFalse(result["catalog_files_modified"])


if __name__ == "__main__":
    unittest.main()
