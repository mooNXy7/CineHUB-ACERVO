import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def movie(title, year, tmdb_id):
    return {
        "id": "movie-" + title.lower().replace(" ", "-"),
        "title": title, "type": "movie", "year": year, "tmdb_id": tmdb_id,
        "poster_url": None, "genres": [], "sources": [], "provider_refs": [],
        "source_candidates_skipped": 0,
    }


def series(title, year, tmdb_id):
    return {
        "id": "series-" + title.lower().replace(" ", "-"),
        "title": title, "type": "series", "year": year, "tmdb_id": tmdb_id,
        "poster_url": None, "genres": [], "subtype": "series", "seasons": {},
        "sources": [], "provider_refs": [], "source_candidates_skipped": 0,
    }


class ExternalIdCollisionTests(unittest.TestCase):
    def test_movie_source_does_not_merge_on_conflicting_title_with_same_tmdb_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "vod/mgeb"
            path.mkdir(parents=True)
            (path / "links-filmes.txt").write_text(
                "Completely Different Film\ttmdb=100\tdub=https://media.example/new.m3u8\n",
                encoding="utf-8",
            )
            existing = movie("Original Film", "2001", "100")
            movies = {"original film": existing}
            counters = defaultdict(int)

            importer.parse_extra_movie_sources(root, movies, {}, counters)

        self.assertEqual(existing["sources"], [])
        new_item = movies["completely different film"]
        self.assertNotEqual(new_item["id"], existing["id"])
        self.assertEqual(new_item["title"], "Completely Different Film")
        self.assertEqual(new_item["tmdb_id"], "100")
        self.assertEqual(len(new_item["sources"]), 1)

    def test_series_source_does_not_merge_on_conflicting_title_with_same_tmdb_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "mgeb"
            path.mkdir(parents=True)
            (path / "links-series.txt").write_text(
                "@Completely Different Show\t2020\t100\n"
                "1\t1\tdub\thttps://media.example/episode.m3u8\n",
                encoding="utf-8",
            )
            existing = series("Original Show", "2001", "100")
            records = {("original show", "2001"): existing}
            counters = defaultdict(int)

            importer.parse_extra_series_sources(root, records, {}, counters)

        self.assertEqual(existing["seasons"], {})
        new_item = records[("completely different show", "2020")]
        self.assertNotEqual(new_item["id"], existing["id"])
        self.assertEqual(new_item["title"], "Completely Different Show")
        self.assertEqual(new_item["tmdb_id"], "100")
        self.assertEqual(len(new_item["seasons"]["1"]["episodes"][0]["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
