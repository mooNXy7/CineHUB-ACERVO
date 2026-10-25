import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def movie_record(title, year, ident):
    return {
        "id": ident,
        "title": title,
        "type": "movie",
        "year": year,
        "tmdb_id": None,
        "poster_url": None,
        "genres": [],
        "sources": [],
        "provider_refs": [],
        "source_candidates_skipped": 0,
    }


class ReferenceMovieIdentityTests(unittest.TestCase):
    def test_ambiguous_title_does_not_merge_extra_source_into_remake(self):
        older = movie_record("The Remake (1998)", "1998", "movie-remake-1998")
        newer = movie_record("The Remake (2020)", "2020", "movie-remake-2020")
        movies = {
            importer.norm(older["title"]): older,
            importer.norm(newer["title"]): newer,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "vod" / "mgeb"
            folder.mkdir(parents=True)
            (folder / "links-filmes.txt").write_text(
                "The Remake\tdub=https://media.example/movie.m3u8\n",
                encoding="utf-8",
            )
            counters = {"skipped_urls": 0, "sources_added": 0, "provider_refs_added": 0}
            importer.parse_extra_movie_sources(root, movies, {}, counters)

        self.assertEqual(older["sources"], [])
        self.assertEqual(newer["sources"], [])
        self.assertEqual(len(movies), 3)
        created = next(item for item in movies.values() if item["id"] not in {
            "movie-remake-1998", "movie-remake-2020"
        })
        self.assertEqual(created["title"], "The Remake")
        self.assertEqual(len(created["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
