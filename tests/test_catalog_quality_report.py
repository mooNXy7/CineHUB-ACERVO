import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog_quality_report import build_report, normalize_title

class CatalogQualityReportTests(unittest.TestCase):
    def test_normalizes_accents_and_punctuation(self):
        self.assertEqual(normalize_title("  São-Paulo! "), "sao paulo")

    def test_report_is_read_only_and_does_not_expose_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = {
                "catalog/channels/channels.json": {"channels": [{"id":"ch-1","name":"Canal A","sources":[{"url":"https://secret.example/live"}]}]},
                "catalog/radios/radios.json": {"radios": [{"id":"r-1","name":"Rádio Rock","stream_url":"https://secret.example/radio"}]},
                "catalog/vod/index.json": {"categories": {s: {"index_path":f"catalog/vod/index/{s}.json"} for s in ("movies","series","anime","doramas")}},
                "catalog/vod/index/movies.json": [{"id":"m-1","title":"São Paulo","detail_path":"detail/a.json"},{"id":"m-2","title":"Sao-Paulo"}],
                "catalog/vod/index/series.json": [], "catalog/vod/index/anime.json": [], "catalog/vod/index/doramas.json": [],
            }
            for rel, value in docs.items():
                path = root / rel; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            before = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob("*") if p.is_file()}
            report = build_report(root)
            after = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob("*") if p.is_file()}
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertEqual(before, after)
            self.assertEqual(report["counts"]["vod_total"], 2)
            self.assertEqual(report["missing_metadata"]["radios_missing_genre"]["count"], 1)
            self.assertEqual(report["duplicate_title_candidates"]["count_included"], 1)
            self.assertNotIn("secret.example", serialized)
            self.assertNotIn("https://", serialized)

    def test_report_keeps_true_counts_when_findings_are_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("catalog/channels", "catalog/radios", "catalog/vod/index"):
                (root / rel).mkdir(parents=True, exist_ok=True)
            channels = [{"id": f"c-{i}", "name": f"Canal {i}"} for i in range(501)]
            (root / "catalog/channels/channels.json").write_text(json.dumps({"channels": channels}), encoding="utf-8")
            (root / "catalog/radios/radios.json").write_text(json.dumps({"radios": []}), encoding="utf-8")
            sections = ("movies", "series", "anime", "doramas")
            manifest = {"categories": {s: {"index_path": f"catalog/vod/index/{s}.json"} for s in sections}}
            (root / "catalog/vod/index.json").write_text(json.dumps(manifest), encoding="utf-8")
            for section in sections:
                (root / f"catalog/vod/index/{section}.json").write_text("[]", encoding="utf-8")
            finding = build_report(root)["missing_metadata"]["channels_missing_logo"]
            self.assertEqual(finding["count"], 501)
            self.assertEqual(finding["items_included"], 500)
            self.assertTrue(finding["truncated"])

if __name__ == "__main__": unittest.main()
