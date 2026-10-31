import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_megaembed_coverage as audit


class MegaEmbedCoverageAuditTests(unittest.TestCase):
    def test_counts_only_allowlisted_https_embed_routes_and_episode_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog/vod/index").mkdir(parents=True)
            (root / "catalog/vod/details/movies").mkdir(parents=True)
            (root / "catalog/vod/details/series").mkdir(parents=True)
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "schema_version": 1,
                "categories": {
                    "movies": {"index_path": "catalog/vod/index/movies.json"},
                    "series": {"index_path": "catalog/vod/index/series.json"}
                }
            }), encoding="utf-8")
            (root / "catalog/vod/index/movies.json").write_text(json.dumps([
                {"id": "m1", "detail_path": "catalog/vod/details/movies/A.json"}
            ]), encoding="utf-8")
            (root / "catalog/vod/index/series.json").write_text(json.dumps([
                {"id": "s1", "detail_path": "catalog/vod/details/series/A.json"}
            ]), encoding="utf-8")
            (root / "catalog/vod/details/movies/A.json").write_text(json.dumps([{
                "id": "m1", "tmdb_id": "123", "sources": [
                    {"url": "https://mgeb.top/embed/123", "source_type": "embed"},
                    {"url": "http://mgeb.top/embed/456", "source_type": "embed"},
                    {"url": "https://evil.example/embed/123", "source_type": "embed"}
                ]
            }]), encoding="utf-8")
            (root / "catalog/vod/details/series/A.json").write_text(json.dumps([{
                "id": "s1", "imdb_id": "tt1234567", "seasons": [{
                    "season": 1, "episodes": [{
                        "episode": 1, "sources": [
                            {"url": "https://megaembedapi.site/embed/tt1234567/1/1"}
                        ]
                    }]
                }]
            }]), encoding="utf-8")

            # Canonical importer format: seasons are keyed by their string number.
            (root / "catalog/vod/details/series/A.json").write_text(json.dumps([{
                "id": "s1", "imdb_id": "tt1234567", "seasons": {
                    "1": {"season": 1, "episodes": [{
                        "episode": 1, "sources": [
                            {"url": "https://megaembedapi.site/embed/tt1234567/1/1"}
                        ]
                    }]}
                }
            }]), encoding="utf-8")

            report = audit.audit(root)

        totals = report["totals"]
        self.assertTrue(report["read_only"])
        self.assertEqual(totals["records"], 2)
        self.assertEqual(totals["records_with_tmdb_id"], 1)
        self.assertEqual(totals["records_with_imdb_id"], 1)
        self.assertEqual(totals["records_with_megaembed"], 2)
        self.assertEqual(totals["megaembed_source_urls"], 2)
        self.assertEqual(totals["episodes"], 1)
        self.assertEqual(totals["episodes_with_megaembed"], 1)


if __name__ == "__main__":
    unittest.main()
