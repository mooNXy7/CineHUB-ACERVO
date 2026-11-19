import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acervo_v2.importers import parse_epg_sources, parse_source_registry, safe_stream_url
from source_registry import (
    load_registry, normalize_source, parse_source_payload,
    validate_resolved_addresses, validate_source_url,
)


class SourceRegistryTests(unittest.TestCase):
    def test_public_https_url_is_accepted(self):
        self.assertEqual(validate_source_url("https://feeds.example.test/list.m3u"), (True, "ok"))

    def test_private_local_and_credentialed_urls_are_rejected(self):
        rejected = {
            "http://127.0.0.1/feed": "non_public_ip",
            "https://10.0.0.5/feed": "non_public_ip",
            "http://localhost/feed": "local_hostname",
            "https://user:pass@example.test/feed": "embedded_credentials",
            "https://example.test/feed?token=secret": "sensitive_query_parameter",
            "file:///etc/passwd": "unsupported_scheme",
        }
        for url, reason in rejected.items():
            with self.subTest(url=url):
                self.assertEqual(validate_source_url(url), (False, reason))

    def test_resolved_private_addresses_are_rejected(self):
        self.assertEqual(validate_resolved_addresses(["8.8.8.8"]), (True, "ok"))
        self.assertEqual(validate_resolved_addresses(["8.8.8.8", "192.168.1.2"]),
                         (False, "resolved_non_public_address"))

    def test_registry_normalizes_legacy_entry_and_keeps_provenance_fields(self):
        legacy = {
            "id": "public-brazil-broadcasters", "name": "Emissoras públicas",
            "category": "channels", "url": "https://feeds.example.test/channels.m3u",
            "format": "m3u", "enabled": True, "priority": 10,
            "license": "Termos públicos",
        }
        record, error = normalize_source(legacy)
        self.assertIsNone(error)
        self.assertEqual(record["domain"], "channels")
        self.assertEqual(record["provider"], "Emissoras públicas")
        self.assertEqual(record["origin"]["kind"], "url")
        self.assertEqual(record["authorization"]["terms"], "Termos públicos")
        self.assertTrue(record["enabled"])

    def test_registry_quarantines_duplicate_ids_and_unsafe_urls(self):
        doc = {"schema_version": 1, "sources": [
            {"id": "source-one", "category": "channels", "format": "m3u",
             "url": "https://feeds.example.test/one.m3u", "enabled": True},
            {"id": "source-one", "category": "channels", "format": "m3u",
             "url": "https://feeds.example.test/two.m3u", "enabled": True},
            {"id": "source-private", "category": "channels", "format": "m3u",
             "url": "http://127.0.0.1/private.m3u", "enabled": True},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            accepted, quarantine = load_registry(path)
        self.assertEqual([item["id"] for item in accepted], ["source-one"])
        self.assertEqual({item["reason"] for item in quarantine},
                         {"duplicate_source_id", "non_public_ip"})

    def test_repository_paths_cannot_escape_repository(self):
        item = {"id": "local-source", "domain": "vod", "format": "vod_catalog",
                "origin": {"kind": "repository_path", "value": "../outside"}}
        record, error = normalize_source(item)
        self.assertIsNone(record)
        self.assertEqual(error, "unsafe_repository_path")

    def test_m3u_adapter_dispatches_to_existing_canonical_parser(self):
        source = {"id": "m3u-fixture", "domain": "channels", "format": "m3u",
                  "origin": {"kind": "repository_path", "value": "fixture.m3u"}}
        records, quarantine = parse_source_payload(
            source, '#EXTM3U\n#EXTINF:-1 tvg-name="Canal",Canal\nhttps://stream.example.test/live.m3u8'
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "Canal")
        self.assertEqual(quarantine, [])

    def test_txt_adapter_requires_explicit_vod_variant(self):
        source = {"id": "text-vod", "domain": "vod", "format": "txt",
                  "origin": {"kind": "repository_path", "value": "movies.txt"}}
        with self.assertRaisesRegex(ValueError, "explicit adapter"):
            parse_source_payload(source, "Filme|2020|https://vod.example.test/movie.m3u8")



    def test_central_registry_loads_and_keeps_pending_sources_disabled(self):
        accepted, quarantine = load_registry(ROOT / "sources/sources.json")
        self.assertGreaterEqual(len(accepted), 5)
        self.assertEqual(quarantine, [])
        pluto = next(item for item in accepted if item["id"] == "pluto-br-xmltv")
        self.assertEqual(pluto["status"], "pending_review")
        self.assertFalse(pluto["enabled"])

    def test_canonical_source_parser_preserves_registry_lifecycle_metadata(self):
        document = {"schema_version": 1, "sources": [{
            "id": "source-example", "domain": "channels", "category": "channels",
            "format": "m3u", "url": "https://feed.example.test/list.m3u",
            "origin": {"kind": "url", "value": "https://feed.example.test/list.m3u"},
            "enabled": True, "status": "active", "priority": 4,
            "language": "pt-BR", "region": "BR",
            "authorization": {"status": "approved"},
            "update_frequency": "daily", "error_history": [],
        }]}
        records, quarantine = parse_source_registry(document)
        self.assertEqual(quarantine, [])
        self.assertEqual(records[0]["status"], "active")
        self.assertTrue(records[0]["enabled"])
        self.assertEqual(records[0]["provider"], "source-example")
        self.assertEqual(records[0]["authorization"]["status"], "approved")
        self.assertEqual(records[0]["language"], "pt-BR")


    def test_registry_quarantines_duplicate_origins_even_with_different_ids(self):
        doc = {"schema_version": 1, "sources": [
            {"id": "source-alpha", "domain": "channels", "format": "m3u",
             "origin": {"kind": "url", "value": "https://FEED.example.test:443/list.m3u"},
             "enabled": True},
            {"id": "source-beta", "domain": "channels", "format": "m3u",
             "origin": {"kind": "url", "value": "https://feed.example.test/list.m3u"},
             "enabled": True},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            accepted, quarantine = load_registry(path)
        self.assertEqual([item["id"] for item in accepted], ["source-alpha"])
        self.assertEqual(quarantine[0]["reason"], "duplicate_source_origin")

    def test_central_registry_records_provider_for_every_source(self):
        accepted, quarantine = load_registry(ROOT / "sources/sources.json")
        self.assertEqual(quarantine, [])
        self.assertTrue(all(item["provider"].strip() for item in accepted))


    def test_legacy_importer_never_enables_pending_review_sources(self):
        document = {"schema_version": 1, "sources": [{
            "id": "pending-source", "domain": "epg", "format": "xmltv",
            "url": "https://epg.example.test/feed.xml", "enabled": True,
            "status": "pending_review", "provider": "Example EPG",
        }]}
        records, quarantine = parse_source_registry(document)
        self.assertEqual(quarantine, [])
        self.assertFalse(records[0]["enabled"])
        self.assertEqual(records[0]["provider"], "Example EPG")

    def test_legacy_importer_quarantines_private_urls_instead_of_importing_them(self):
        document = {"schema_version": 1, "sources": [{
            "id": "private-source", "domain": "channels", "format": "m3u",
            "url": "http://192.168.1.10/feed.m3u", "enabled": True,
        }]}
        records, quarantine = parse_source_registry(document)
        self.assertEqual(records, [])
        self.assertEqual(quarantine[0]["reason"], "non_public_ip")

    def test_quarantine_redacts_secret_values(self):
        doc = {"schema_version": 1, "sources": [{
            "id": "secret-source", "domain": "channels", "format": "m3u",
            "url": "https://feed.example.test/list.m3u?token=do-not-log",
            "password": "do-not-log-either", "enabled": True,
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            accepted, quarantine = load_registry(path)
        self.assertEqual(accepted, [])
        serialized = json.dumps(quarantine)
        self.assertNotIn("do-not-log", serialized)
        self.assertIn("[REDACTED]", serialized)


    def test_local_m3u_source_is_loaded_from_inside_repository(self):
        source = {
            "id": "public-brazil-broadcasters", "domain": "channels", "format": "m3u",
            "origin": {"kind": "repository_path", "value": "sources/m3u/public-brazil.m3u"},
            "enabled": True, "status": "active",
        }
        records, quarantine = parse_source_payload(source)
        self.assertGreaterEqual(len(records), 5)
        self.assertEqual(quarantine, [])

    def test_missing_local_source_file_is_quarantined(self):
        doc = {"schema_version": 1, "sources": [{
            "id": "missing-local", "domain": "channels", "format": "m3u",
            "origin": {"kind": "repository_path", "value": "sources/m3u/does-not-exist.m3u"},
            "enabled": True,
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            accepted, quarantine = load_registry(path)
        self.assertEqual(accepted, [])
        self.assertEqual(quarantine[0]["reason"], "repository_source_missing_or_unsafe")


    def test_json_channel_and_radio_adapters_load_local_catalogs(self):
        channels, channel_quarantine = parse_source_payload({
            "id": "local-channels", "domain": "channels", "format": "json",
            "origin": {"kind": "repository_path", "value": "catalog/channels/channels.json"},
        })
        radios, radio_quarantine = parse_source_payload({
            "id": "local-radios", "domain": "radios", "format": "json",
            "origin": {"kind": "repository_path", "value": "catalog/radios/radios.json"},
        })
        self.assertGreater(len(channels), 0)
        self.assertGreater(len(radios), 0)
        self.assertEqual(channel_quarantine, [])
        self.assertEqual(radio_quarantine, [])

    def test_txt_radio_and_vod_adapters_load_their_declared_variants(self):
        radios, radio_quarantine = parse_source_payload({
            "id": "fixture-radio", "domain": "radios", "format": "txt",
            "adapter": "radio_text",
            "origin": {"kind": "repository_path", "value": "tests/fixtures/canonical/radios-two-column.txt"},
        })
        movies, movie_quarantine = parse_source_payload({
            "id": "fixture-movies", "domain": "vod", "format": "txt",
            "adapter": "vod_movies",
            "origin": {"kind": "repository_path", "value": "tests/fixtures/canonical/vod-movies.txt"},
        })
        series, series_quarantine = parse_source_payload({
            "id": "fixture-series", "domain": "vod", "format": "txt",
            "adapter": "vod_series",
            "origin": {"kind": "repository_path", "value": "tests/fixtures/canonical/vod-series.txt"},
        })
        self.assertGreater(len(radios), 0)
        self.assertGreater(len(movies), 0)
        self.assertGreater(len(series), 0)
        self.assertEqual(radio_quarantine, [])
        self.assertEqual(movie_quarantine, [])
        self.assertEqual(series_quarantine, [])

    def test_xmltv_adapter_parses_valid_records_and_quarantines_invalid_programme(self):
        channels, programmes, quarantine = parse_source_payload({
            "id": "fixture-xmltv", "domain": "epg", "format": "xmltv",
            "origin": {"kind": "repository_path", "value": "tests/fixtures/canonical/sample.xml"},
        })
        self.assertEqual(len(channels), 1)
        self.assertEqual(len(programmes), 1)
        self.assertEqual([item["reason"] for item in quarantine], ["invalid_programme"])


    def test_vod_catalog_adapter_uses_only_the_declared_local_manifest(self):
        records, quarantine = parse_source_payload({
            "id": "catalog-vod", "domain": "vod", "format": "vod_catalog",
            "origin": {"kind": "repository_path", "value": "catalog/vod/index.json"},
        })
        self.assertGreater(len(records), 0)
        self.assertEqual(quarantine, [])
        with self.assertRaisesRegex(ValueError, "catalog/vod/index.json"):
            parse_source_payload({
                "id": "wrong-vod", "domain": "vod", "format": "vod_catalog",
                "origin": {"kind": "repository_path", "value": "catalog/channels/channels.json"},
            })


    def test_source_rejects_credential_values_and_conflicting_origin_urls(self):
        base = {"id": "source-credential", "domain": "channels", "format": "m3u",
                "origin": {"kind": "url", "value": "https://feed.example.test/list.m3u"},
                "enabled": True}
        record, error = normalize_source({**base, "credentials_ref": "actual/secret=value"})
        self.assertIsNone(record)
        self.assertEqual(error, "invalid_credentials_ref")
        record, error = normalize_source({**base, "url": "https://other.example.test/feed.m3u"})
        self.assertIsNone(record)
        self.assertEqual(error, "origin_url_mismatch")


    def test_legacy_epg_source_parser_emits_required_provider_field(self):
        records, quarantine = parse_epg_sources({"sources": [{
            "id": "epg-example", "name": "EPG Example", "format": "xmltv",
            "url": "https://epg.example.test/feed.xml", "enabled": False,
        }]})
        self.assertEqual(quarantine, [])
        self.assertEqual(records[0]["provider"], "EPG Example")


    def test_sensitive_query_variants_and_malformed_ports_are_rejected(self):
        for url in (
            "https://feed.example.test/list.m3u?x-api-key=secret",
            "https://feed.example.test/list.m3u?auth_token=secret",
            "https://feed.example.test:99999/list.m3u",
        ):
            with self.subTest(url=url):
                self.assertFalse(validate_source_url(url)[0])
                self.assertFalse(safe_stream_url(url)[0])

if __name__ == "__main__":
    unittest.main()
