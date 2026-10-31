import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


class ReferenceMovieMetadataPreservationTests(unittest.TestCase):
    def test_reference_enrichment_fills_gaps_without_overwriting_existing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            vod = reference / "vod"
            vod.mkdir()
            (vod / "filmes-main.txt").write_text(
                "A Test Film (2001)\tdub=https://media.example/film.m3u8\n",
                encoding="utf-8",
            )
            item = {
                "id": "movie-existing-id",
                "title": "A Test Film (2001)",
                "type": "movie",
                "year": None,
                "tmdb_id": "111",
                "poster_url": "https://images.example/existing-poster.jpg",
                "genres": ["Drama"],
                "sources": [{
                    "url": "https://media.example/existing.m3u8",
                    "audio": "leg",
                    "priority": 10,
                    "source_id": "existing-source",
                    "source_type": "direct",
                }],
                "provider_refs": [],
                "source_candidates_skipped": 0,
            }
            movies = {importer.norm(item["title"]): item}
            counters = {"skipped_urls": 0, "source_urls_merged_into_reference_candidates": 0, "provider_refs_merged_into_reference_candidates": 0}
            fichas = {
                ("f", importer.norm(item["title"])): {
                    "tmdb_id": "222",
                    "poster_path": "https://images.example/reference-poster.jpg",
                    "genres": ["Drama", "Comedy"],
                    "imdb_id": "tt1234567",
                }
            }

            importer.parse_movies(reference, fichas, {}, counters, movies)

        self.assertEqual(item["id"], "movie-existing-id")
        self.assertEqual(item["tmdb_id"], "111")
        self.assertEqual(item["imdb_id"], "tt1234567")
        self.assertEqual(item["poster_url"], "https://images.example/existing-poster.jpg")
        self.assertEqual(item["year"], "2001")
        self.assertEqual(item["genres"], ["Drama", "Comedy"])
        self.assertEqual(len(item["sources"]), 2)
        self.assertEqual(item["sources"][0]["source_id"], "existing-source")
        self.assertEqual(counters["source_urls_merged_into_reference_candidates"], 1)


    def test_extra_movie_sources_preserve_imdb_id_and_mark_embed_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            mgeb = reference / "vod/mgeb"
            mgeb.mkdir(parents=True)
            (mgeb / "links-filmes.txt").write_text(
                "A New Film (2020)\\tdub=https://mgeb.top/embed/123,https://megaembedapi.site/embed/123\\ttmdb=123\\timdb=tt1234567\\n",
                encoding="utf-8",
            )
            movies = {}
            counters = {"skipped_urls": 0, "source_urls_merged_into_reference_candidates": 0,
                        "provider_refs_merged_into_reference_candidates": 0}
            importer.parse_extra_movie_sources(reference, movies, {}, counters)
            item = movies[importer.norm("A New Film (2020)")]

        self.assertEqual(item["tmdb_id"], "123")
        self.assertEqual(item["imdb_id"], "tt1234567")
        self.assertEqual(len(item["sources"]), 2)
        self.assertTrue(all(source["source_type"] == "embed" for source in item["sources"]))


if __name__ == "__main__":
    unittest.main()
