import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import suggest_saimoplayer_fichas_tmdb_ids as suggest


class SaimoPlayerFichasTmdbIdTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "catalog/vod/index").mkdir(parents=True)
        (self.root / "catalog/vod/index/movies.json").write_text(json.dumps([
            {"id": "m1", "title": "Filme Exato (2020)", "year": "2020", "tmdb_id": None},
            {"id": "m2", "title": "Remake (2021)", "year": "2021", "tmdb_id": None},
            {"id": "m3", "title": "Ambíguo (2019)", "year": "2019", "tmdb_id": None},
            {"id": "m4", "title": "Sem Ano", "year": "", "tmdb_id": None},
            {"id": "m5", "title": "Já Tem ID (2020)", "year": "2020", "tmdb_id": "123"},
        ]), encoding="utf-8")
        (self.root / "catalog/vod/index/series.json").write_text(json.dumps([
            {"id": "s1", "title": "Série com Mesmo Nome (2020)", "year": "2020", "tmdb_id": None},
        ]), encoding="utf-8")
        self.fichas = self.root / "fichas.txt"
        self.fichas.write_text(
            "# cabeçalho\n"
            "f\tFilme Exato (2020)\t100\t/poster.jpg\tDrama\n"
            "f\tRemake (2018)\t200\t/poster.jpg\tDrama\n"
            "f\tAmbíguo (2019)\t300\t/poster.jpg\tDrama\n"
            "f\tAmbíguo (2019)\t301\t/poster2.jpg\tDrama\n"
            "f\tSem Ano\t400\t/poster.jpg\tDrama\n"
            "f\tSérie com Mesmo Nome (2020)\t500\t/poster.jpg\tDrama\n"
            "s\tSérie com Mesmo Nome (2020)\t600\t/poster.jpg\tDrama\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_only_exact_title_type_unique_id_and_year_are_candidates(self):
        report = suggest.build_report(self.root, self.fichas)
        self.assertEqual(report["summary"]["unique_id_and_exact_year_candidates"], 2)
        self.assertEqual(len(report["candidates"]), 2)
        self.assertEqual(report["candidates"][0]["catalog_id"], "m1")
        self.assertEqual(report["candidates"][0]["candidates"][0]["tmdb_id_candidate"], "100")

    def test_ambiguous_ids_year_conflicts_and_missing_year_are_not_candidates(self):
        report = suggest.build_report(self.root, self.fichas)
        counts = report["summary"]
        self.assertEqual(counts["ambiguous_reference_ids"], 1)
        self.assertEqual(counts["year_conflicts"], 1)
        self.assertEqual(counts["missing_catalog_or_reference_year"], 1)

    def test_media_type_uses_matching_ficha_type(self):
        report = suggest.build_report(self.root, self.fichas)
        series_candidate = next(x for x in report["candidates"] if x["catalog_id"] == "s1")
        self.assertEqual(series_candidate["media_type"], "tv")
        self.assertEqual(series_candidate["candidates"][0]["tmdb_id_candidate"], "600")

    def test_existing_tmdb_id_is_never_reproposed(self):
        report = suggest.build_report(self.root, self.fichas)
        self.assertNotIn("m5", {x["catalog_id"] for x in report["candidates"]})


if __name__ == "__main__":
    unittest.main()
