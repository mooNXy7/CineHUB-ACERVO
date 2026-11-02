import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import apply_vod_poster_artwork_to_channels as artwork


class ChannelVodPosterArtworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "catalog/channels").mkdir(parents=True)
        (self.root / "catalog/vod/index").mkdir(parents=True)
        self.channels_path = self.root / "catalog/channels/channels.json"
        self.channels_path.write_text(json.dumps({"channels": [
            {"id": "ch-series", "name": "Friends - 24H", "logo_url": None,
             "sources": [{"url": "https://stream.example/live"}], "epg_id": "friends.br"},
            {"id": "ch-remake", "name": "A Família Addams 24H", "logo_url": None},
            {"id": "ch-year", "name": "Filme Exato (2021)", "logo_url": None},
            {"id": "ch-existing", "name": "Já tem logo 24H", "logo_url": "https://existing.example/logo.png"},
            {"id": "ch-movie-no-year", "name": "Homem Aranha 24H", "logo_url": None},
        ]}), encoding="utf-8")
        (self.root / "catalog/vod/index/movies.json").write_text(json.dumps([
            {"id": "movie-addams", "title": "A Família Addams", "year": "1991",
             "poster_url": "/movie-addams.jpg"},
            {"id": "movie-year", "title": "Filme Exato", "year": "2020",
             "poster_url": "/movie-year.jpg"},
            {"id": "movie-spider", "title": "Homem Aranha", "year": "",
             "poster_url": "/movie-spider.jpg"},
        ]), encoding="utf-8")
        (self.root / "catalog/vod/index/series.json").write_text(json.dumps([
            {"id": "series-friends", "title": "Friends", "year": "1994",
             "poster_url": "/friends.jpg"},
            {"id": "series-addams", "title": "A Família Addams", "year": "1964",
             "poster_url": "/series-addams.jpg"},
        ]), encoding="utf-8")
        (self.root / "catalog/vod/index/anime.json").write_text(json.dumps([
            {"id": "series-friends", "title": "Friends", "year": "1994",
             "poster_url": "/friends.jpg"},
        ]), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_series_poster_fills_only_missing_logo_and_preserves_streams(self):
        report = artwork.build_report(self.root)
        saved = json.loads(self.channels_path.read_text(encoding="utf-8"))
        channel = next(x for x in saved["channels"] if x["id"] == "ch-series")
        self.assertEqual(channel["logo_url"], "https://image.tmdb.org/t/p/w342/friends.jpg")
        self.assertEqual(channel["sources"], [{"url": "https://stream.example/live"}])
        self.assertEqual(channel["epg_id"], "friends.br")
        self.assertEqual(report["counts"]["artwork_applied"], 1)

    def test_remake_ambiguity_and_year_conflict_are_skipped(self):
        report = artwork.build_report(self.root)
        self.assertEqual(report["counts"]["ambiguous_vod_matches"], 1)
        self.assertEqual(report["counts"]["year_conflicts"], 1)

    def test_existing_logo_is_never_overwritten(self):
        report = artwork.build_report(self.root)
        saved = json.loads(self.channels_path.read_text(encoding="utf-8"))
        channel = next(x for x in saved["channels"] if x["id"] == "ch-existing")
        self.assertEqual(channel["logo_url"], "https://existing.example/logo.png")

    def test_movie_without_year_is_not_used_for_24h_artwork(self):
        report = artwork.build_report(self.root)
        self.assertEqual(report["counts"]["missing_year_for_movie"], 1)


if __name__ == "__main__":
    unittest.main()
