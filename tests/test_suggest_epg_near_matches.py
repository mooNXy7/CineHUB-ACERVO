import json
import tempfile
import unittest
from pathlib import Path

from scripts.suggest_epg_near_matches import build_report


class SuggestEpgNearMatchesTests(unittest.TestCase):
    def _root(self, temp, channel_names, xmltv_names):
        root = Path(temp)
        (root / "catalog/channels").mkdir(parents=True)
        (root / "catalog/epg").mkdir(parents=True)
        (root / "catalog/channels/channels.json").write_text(json.dumps({
            "channels": [{"id": f"c{i}", "name": name, "epg_id": None, "epg_sources": []}
                         for i, name in enumerate(channel_names)]
        }), encoding="utf-8")
        (root / "catalog/epg/xmltv-channels.json").write_text(json.dumps({
            "sources": {"feed-a": {"channels": [
                {"id": f"id{i}", "display_names": [name]}
                for i, name in enumerate(xmltv_names)
            ]}}
        }), encoding="utf-8")
        (root / "catalog/epg/channel-map.json").write_text(json.dumps({
            "xmltv_aliases": {}, "meuguia_codes": {}, "guiadetv_slugs": {}
        }), encoding="utf-8")
        return root

    def test_high_similarity_candidate_is_review_only_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp, ["Canal X Sports"], ["Canal X Sport"])
            before = (root / "catalog/channels/channels.json").read_text(encoding="utf-8")
            report = build_report(root)
            after = (root / "catalog/channels/channels.json").read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual(report["counts"]["candidate_channels"], 1)
        self.assertEqual(report["candidates"][0]["source_ids"]["feed-a"], ["id0"])
        self.assertFalse(report["candidates"][0]["automatic_update"])

    def test_equally_close_candidates_are_not_proposed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp, ["Canal X Sports"], ["Canal X Sport", "Canal X Sport HD"])
            report = build_report(root)

        self.assertEqual(report["counts"]["candidate_channels"], 0)
        self.assertGreaterEqual(report["counts"]["skipped_ambiguous"], 0)


if __name__ == "__main__":
    unittest.main()
