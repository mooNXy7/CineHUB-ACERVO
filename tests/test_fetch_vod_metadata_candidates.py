import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_vod_metadata_candidates as fetcher


class FetchVodMetadataCandidateTests(unittest.TestCase):
    def _catalog(self, root: Path, title="A Test Film (2001)", tmdb_id="123"):
        (root / "catalog/vod/index").mkdir(parents=True)
        categories = {}
        for section in fetcher.SECTIONS:
            path = root / f"catalog/vod/index/{section}.json"
            records = []
            if section == "movies":
                records = [{
                    "id": "movie-test",
                    "title": title,
                    "type": "movie",
                    "tmdb_id": tmdb_id,
                    "year": None,
                    "poster_url": None,
                    "genres": [],
                }]
            path.write_text(json.dumps(records), encoding="utf-8")
            categories[section] = {"index_path": f"catalog/vod/index/{section}.json"}
        (root / "catalog/vod/index.json").write_text(
            json.dumps({"categories": categories}), encoding="utf-8"
        )

    def test_default_run_is_read_only_and_does_not_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._catalog(root)
            before = {
                str(path.relative_to(root)): path.read_bytes()
                for path in (root / "catalog").rglob("*.json")
            }
            report = fetcher.build_candidates(root, root / "out.json", limit=10, fetch=False)
            after = {
                str(path.relative_to(root)): path.read_bytes()
                for path in (root / "catalog").rglob("*.json")
            }

        self.assertFalse(report["network_accessed"])
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual(report["eligible_records_found"], 1)
        self.assertEqual(report["patch_candidates"][0]["status"], "eligible_id_present_not_fetched")
        self.assertEqual(before, after)

    def test_fetch_builds_patch_only_for_exact_title_and_compatible_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._catalog(root)
            payload = {
                "title": "A Test Film",
                "original_title": "A Test Film",
                "release_date": "2001-04-01",
                "poster_path": "/poster.jpg",
                "genres": [{"id": 1, "name": "Drama"}, {"id": 2, "name": "Comedy"}],
            }
            with patch.object(fetcher, "fetch_payload", return_value=(payload, "fetched")):
                report = fetcher.build_candidates(
                    root, root / "out.json", limit=10, fetch=True,
                    cache_path=root / "cache.sqlite3", api_key="test-key",
                )

        self.assertTrue(report["network_accessed"])
        self.assertFalse(report["catalog_mutated"])
        candidate = report["patch_candidates"][0]
        self.assertEqual(candidate["status"], "candidate_exact_title_match")
        self.assertEqual(candidate["patch"]["year"], "2001")
        self.assertEqual(candidate["patch"]["poster_url"], "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertEqual(candidate["patch"]["genres"], ["Drama", "Comedy"])
        self.assertTrue(candidate["requires_review_before_apply"])

    def test_title_mismatch_goes_to_manual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._catalog(root)
            payload = {
                "title": "Different Film",
                "original_title": "Different Film",
                "release_date": "2001-04-01",
                "poster_path": "/poster.jpg",
                "genres": [{"name": "Drama"}],
            }
            with patch.object(fetcher, "fetch_payload", return_value=(payload, "fetched")):
                report = fetcher.build_candidates(
                    root, root / "out.json", limit=10, fetch=True,
                    cache_path=root / "cache.sqlite3", api_key="test-key",
                )

        self.assertEqual(report["patch_candidates"], [])
        self.assertEqual(report["manual_review"][0]["status"], "title_mismatch")

    def test_fetch_requires_key_before_any_network_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._catalog(root)
            with patch.object(fetcher, "fetch_payload") as network:
                with self.assertRaisesRegex(ValueError, "TMDB_API_KEY"):
                    fetcher.build_candidates(root, root / "out.json", fetch=True, api_key=None)
                network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
