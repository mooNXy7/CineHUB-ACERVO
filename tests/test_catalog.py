import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_catalog import merge_channels, parse_m3u, safe_https_url
from import_reference_catalog import canonical_key, dedupe_records, merge_record, parse_search_index, safe_candidate, split_sources
from update_epg import normalise, parse_xmltv, parse_xmltv_date


class CatalogShapeTests(unittest.TestCase):
    def load(self, path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    def test_epg_registry_shape_and_priorities(self):
        data = self.load("catalog/epg/sources.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertGreaterEqual(len(data["sources"]), 5)
        priorities = [x["priority"] for x in data["sources"]]
        self.assertEqual(priorities, sorted(priorities))
        self.assertTrue(all(x.get("url") or x.get("url_template") for x in data["sources"]))

    def test_epg_normalization_and_xmltv_dates(self):
        self.assertEqual(normalise("TV Câmara HD BR"), "tv camara")
        parsed = parse_xmltv_date("20261015193000 -0300")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.utcoffset().total_seconds(), -10800)

    def test_xmltv_indexer_parses_channels_and_window(self):
        xml = b'''<?xml version="1.0"?><tv><channel id="canal.1"><display-name>TV Camara</display-name></channel><programme start="20261015193000 -0300" stop="20261015200000 -0300" channel="canal.1"><title>Jornal</title></programme></tv>'''
        now = dt.datetime(2026, 10, 15, 22, 0, tzinfo=dt.timezone.utc)
        channels, total, window = parse_xmltv(xml, now=now)
        self.assertEqual(channels[0]["id"], "canal.1")
        self.assertEqual(channels[0]["display_names"], ["TV Camara"])
        self.assertEqual(total, 1)
        self.assertEqual(window, 1)

    def test_channels_shape(self):
        data = self.load("catalog/channels/channels.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["channels"], list)

    def test_radios_shape(self):
        data = self.load("catalog/radios/radios.json")
        self.assertEqual(data["schema_version"], 1)
        self.assertIsInstance(data["radios"], list)

    def test_vod_categories(self):
        data = self.load("catalog/vod/index.json")
        for category in ("movies", "series", "anime", "doramas"):
            if isinstance(data.get(category), list):
                items = data[category]
            else:
                info = data["categories"][category]
                items = self.load(info["index_path"])
                self.assertEqual(info["count"], len(items))
            self.assertIsInstance(items, list)


class SourceSafetyTests(unittest.TestCase):
    def test_accepts_public_https_url(self):
        self.assertTrue(safe_https_url("https://example.com/list.m3u"))

    def test_rejects_http_url(self):
        self.assertFalse(safe_https_url("http://example.com/live.m3u"))

    def test_rejects_embedded_credentials(self):
        self.assertFalse(safe_https_url("https://user:pass@example.com/live"))

    def test_rejects_tokenized_query_urls(self):
        for url in (
            "https://example.com/live.m3u8?token=abc",
            "https://example.com/live.m3u8?auth=abc",
            "https://example.com/live.m3u8?signature=abc",
        ):
            with self.subTest(url=url):
                self.assertFalse(safe_https_url(url))

    def test_rejects_local_and_private_hosts(self):
        for url in (
            "https://localhost/list.m3u",
            "https://192.168.1.10/live",
            "https://127.0.0.1/live",
            "https://printer.local/list",
        ):
            with self.subTest(url=url):
                self.assertFalse(safe_https_url(url))

    def test_reference_import_filters_credentials_but_keeps_public_http_sources(self):
        self.assertTrue(safe_candidate("http://cdn.example.org/channel.m3u8"))
        self.assertFalse(safe_candidate("https://user:pass@example.org/live"))
        self.assertFalse(safe_candidate("https://example.org/live.m3u8?token=abc"))
        self.assertFalse(safe_candidate("http://example.org/movie/user/pass/123.mp4"))

    def test_canonical_key_deduplicates_title_variants(self):
        self.assertEqual(
            canonical_key({"id": "a", "title": "Filme Exemplo (2020)", "year": "2020"}),
            canonical_key({"id": "b", "title": "Filme Exemplo", "year": "2020"}),
        )
        self.assertEqual(
            canonical_key({"id": "a", "title": "Nome A", "tmdb_id": "123"}),
            canonical_key({"id": "b", "title": "Nome B", "tmdb_id": "123"}),
        )

    def test_dedupe_records_merges_same_id_but_preserves_tmdb_collision(self):
        records = [
            {"id": "movie-one", "title": "Filme (2020)", "year": "2020", "tmdb_id": "123",
             "sources": [{"url": "https://cdn.example.org/a.m3u8"}], "provider_refs": []},
            {"id": "movie-one", "title": "Filme (2020)", "year": "2020",
             "sources": [{"url": "https://cdn.example.org/b.m3u8"}], "provider_refs": []},
            {"id": "movie-two", "title": "Título alternativo", "tmdb_id": "123",
             "sources": [{"url": "https://cdn.example.org/c.m3u8"}], "provider_refs": []},
        ]
        merged = dedupe_records(records)
        self.assertEqual(len(merged), 2)
        by_id = {item["id"]: item for item in merged}
        self.assertEqual(len(by_id["movie-one"]["sources"]), 2)
        self.assertEqual(len(by_id["movie-two"]["sources"]), 1)
        self.assertEqual(by_id["movie-two"]["sources"][0]["url"], "https://cdn.example.org/c.m3u8")

    def test_embed_sources_are_typed_and_prioritized(self):
        urls, refs, skipped = split_sources(
            "https://mgeb.top/embed/123", "dub", source_id="reference-mgeb", priority=20
        )
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0]["source_type"], "embed")
        self.assertEqual(urls[0]["priority"], 20)
        self.assertEqual(urls[0]["source_id"], "reference-mgeb")
        self.assertEqual(refs, [])
        self.assertEqual(skipped, 0)

    def test_reference_search_index_parses_movies_and_series(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "busca.txt"
            path.write_text("Filme Exemplo (2020)\tf\tF\nSérie Exemplo\ts\tS\t2022\n", encoding="utf-8")
            movies, series = parse_search_index(path)
        self.assertEqual(len(movies), 1)
        self.assertEqual(len(series), 1)
        self.assertEqual(next(iter(movies.values()))["year"], "2020")
        self.assertEqual(next(iter(series.values()))["year"], "2022")

    def test_merge_record_preserves_old_sources_and_episode_sources(self):
        old = {
            "id": "series-exemplo", "title": "Série Exemplo", "sources": [
                {"url": "https://cdn.example.org/old.m3u8", "priority": 5}
            ], "provider_refs": [], "seasons": [
                {"season": 1, "episodes": [{"episode": 1, "audio": "dub", "sources": [
                    {"url": "https://cdn.example.org/ep1.m3u8"}
                ], "provider_refs": []}]}
            ]
        }
        incoming = {
            "id": "series-exemplo", "title": "Série Exemplo", "sources": [
                {"url": "https://cdn.example.org/new.m3u8", "priority": 1}
            ], "provider_refs": [], "seasons": [
                {"season": 1, "episodes": [{"episode": 1, "audio": "dub", "sources": [
                    {"url": "https://cdn.example.org/ep1-new.m3u8"}
                ], "provider_refs": []}]}
            ]
        }
        merged = merge_record(old, incoming)
        self.assertEqual(len(merged["sources"]), 2)
        self.assertEqual(len(merged["seasons"][0]["episodes"][0]["sources"]), 2)

    def test_m3u_parser_keeps_only_safe_https_streams(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-name="Canal Exemplo" group-title="Brasil",Canal Exemplo
https://cdn.example.org/channel.m3u8
#EXTINF:-1 tvg-name="Canal HTTP",Canal HTTP
http://cdn.example.org/channel.m3u8
#EXTINF:-1 tvg-name="Canal com credencial",Canal com credencial
https://user:pass@cdn.example.org/channel.m3u8
"""
        channels = parse_m3u(text, "test-source", 1)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["name"], "Canal Exemplo")
        self.assertEqual(channels[0]["group"], "Brasil")
        self.assertEqual(channels[0]["sources"][0]["source_id"], "test-source")

    def test_merge_preserves_existing_metadata_and_deduplicates_sources(self):
        existing = [{
            "id": "ch-canal-exemplo",
            "name": "Canal Exemplo",
            "group": "Grupo Curado",
            "logo_url": "https://logos.example.org/canal.png",
            "sources": [{"url": "https://cdn.example.org/old.m3u8", "priority": 5}],
        }]
        incoming = [{
            "id": "ch-canal-exemplo",
            "name": "Canal Exemplo",
            "group": "Grupo Fonte",
            "logo_url": "https://logos.example.org/new.png",
            "sources": [
                {"url": "https://cdn.example.org/old.m3u8", "priority": 5},
                {"url": "https://cdn.example.org/new.m3u8", "priority": 1},
            ],
        }]
        merged, added = merge_channels(existing, incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["group"], "Grupo Curado")
        self.assertEqual(merged[0]["logo_url"], "https://logos.example.org/canal.png")
        self.assertEqual(len(merged[0]["sources"]), 2)
        self.assertEqual(added, 1)

    def test_merge_matches_names_without_accent_difference(self):
        existing = [{"id": "br.tv-camara", "name": "TV Câmara", "sources": []}]
        incoming = [{
            "id": "ch-tv-camara",
            "name": "TV Camara",
            "sources": [{"url": "https://stream.example.org/tv.m3u8", "priority": 1}],
        }]
        merged, added = merge_channels(existing, incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], "br.tv-camara")
        self.assertEqual(len(merged[0]["sources"]), 1)
        self.assertEqual(added, 1)


if __name__ == "__main__":
    unittest.main()
