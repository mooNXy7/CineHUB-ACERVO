import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_reference_catalog as importer


def series_record(title, year, ident):
    return {
        "id": ident,
        "title": title,
        "type": "series",
        "year": year,
        "tmdb_id": None,
        "poster_url": None,
        "genres": [],
        "seasons": {},
        "sources": [],
        "provider_refs": [],
        "source_candidates_skipped": 0,
    }


class ReferenceSeriesIdentityTests(unittest.TestCase):
    def _run_import(self, line, series):
        with tempfile.TemporaryDirectory() as tmp:
            vod = Path(tmp)
            folder = vod / "mgeb"
            folder.mkdir()
            (folder / "links-series.txt").write_text(
                line + "\n1\t1\tdub\thttps://media.example/episode.m3u8\n",
                encoding="utf-8",
            )
            counters = {"skipped_urls": 0, "sources_added": 0, "provider_refs_added": 0}
            importer.parse_extra_series_sources(vod, series, {}, counters)
            return counters

    def test_remake_matches_exact_year_not_first_title_candidate(self):
        older = series_record("The Remake (1998)", "1998", "series-remake-1998")
        newer = series_record("The Remake (2020)", "2020", "series-remake-2020")
        series = {
            ("the remake 1998", "1998"): older,
            ("the remake 2020", "2020"): newer,
        }

        self._run_import("@The Remake\t2020", series)

        self.assertEqual(older["seasons"], {})
        self.assertEqual(len(newer["seasons"]), 1)
        self.assertEqual(newer["seasons"]["1"]["episodes"][0]["episode"], 1)
        self.assertEqual(len(newer["seasons"]["1"]["episodes"][0]["sources"]), 1)
        self.assertEqual(len(series), 2)

    def test_missing_year_does_not_merge_when_title_is_ambiguous(self):
        older = series_record("The Remake (1998)", "1998", "series-remake-1998")
        newer = series_record("The Remake (2020)", "2020", "series-remake-2020")
        series = {
            ("the remake 1998", "1998"): older,
            ("the remake 2020", "2020"): newer,
        }

        self._run_import("@The Remake", series)

        self.assertEqual(older["seasons"], {})
        self.assertEqual(newer["seasons"], {})
        self.assertEqual(len(series), 3)
        created = next(item for item in series.values() if item["id"] not in {
            "series-remake-1998", "series-remake-2020"
        })
        self.assertEqual(created["title"], "The Remake")
        self.assertIsNone(created["year"])
        self.assertEqual(len(created["seasons"]), 1)


if __name__ == "__main__":
    unittest.main()
