import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_epg_mappings import build_report


class SuggestEpgMappingsTests(unittest.TestCase):
    def make_root(self, root: Path):
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/epg").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(json.dumps({
            "channels": [
                {"id": "c1", "name": "Canal Árvore HD"},
                {"id": "c2", "name": "Canal Ambíguo"},
                {"id": "c3", "name": "Canal Sem EPG"},
                {"id": "c4", "name": "Já Mapeado", "epg_id": "mapped-id"},
                {"id": "c5", "name": "History Channel"},
            ]
        }), encoding="utf-8")
        (root / "catalog/epg/xmltv-channels.json").write_text(json.dumps({
            "sources": {
                "feed-a": {"channels": [
                    {"id": "arvore.a", "display_names": ["Canal Árvore"]},
                    {"id": "amb.1", "display_names": ["Canal Ambíguo"]},
                    {"id": "amb.2", "display_names": ["Canal Ambíguo"]},
                    {"id": "history.br", "display_names": ["History"]},
                ]},
                "feed-b": {"channels": [
                    {"id": "arvore.b", "display_names": ["Canal Arvore"]},
                ]},
            }
        }), encoding="utf-8")
        (root / "catalog/epg/channel-map.json").write_text(json.dumps({
            "xmltv_aliases": {"History": ["History Channel"]},
            "meuguia_codes": {"Canal Sem EPG": "CSE"},
            "guiadetv_slugs": {},
        }), encoding="utf-8")

    def test_only_exact_name_candidates_and_never_mutates_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_root(root)
            before = (root / "catalog/channels/channels.json").read_text(encoding="utf-8")
            report = build_report(root)
            after = (root / "catalog/channels/channels.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])
        candidates = {item["channel_name"]: item for item in report["candidates"]}
        self.assertIn("Canal Árvore HD", candidates)
        self.assertEqual(candidates["Canal Árvore HD"]["status"], "unique_exact_name_review")
        self.assertIn("Canal Ambíguo", candidates)
        self.assertEqual(candidates["Canal Ambíguo"]["status"], "ambiguous_exact_name_review")
        self.assertNotIn("Canal Sem EPG", candidates)
        self.assertNotIn("Já Mapeado", candidates)
        self.assertEqual(report["counts"]["channels_with_existing_html_epg_mapping"], 1)
        self.assertIn("History Channel", candidates)
        self.assertEqual(candidates["History Channel"]["source_ids"]["feed-a"], ["history.br"])

    def test_source_specific_ids_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_root(root)
            report = build_report(root)
        candidate = next(item for item in report["candidates"] if item["channel_name"] == "Canal Árvore HD")
        self.assertEqual(candidate["source_ids"]["feed-a"], ["arvore.a"])
        self.assertEqual(candidate["source_ids"]["feed-b"], ["arvore.b"])
        self.assertFalse(candidate["automatic_update"])


if __name__ == "__main__":
    unittest.main()
