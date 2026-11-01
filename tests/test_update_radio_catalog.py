import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_radio_catalog


class UpdateRadioCatalogTests(unittest.TestCase):
    def test_parse_pipe_delimited_source_accepts_only_safe_https_streams(self):
        records, counts = update_radio_catalog.parse_radio_source(
            "Radio A|https://radio.example/live\n"
            "Radio B|http://radio.example/live\n"
            "Malformed line\n"
            "Radio C|https://radio.example/c\n",
            "saimoplayer-radios",
        )
        self.assertEqual([x["name"] for x in records], ["Radio A", "Radio C"])
        self.assertEqual(counts["unsafe_streams"], 1)
        self.assertEqual(counts["malformed"], 1)

    def test_parse_deduplicates_same_station_and_stream(self):
        records, counts = update_radio_catalog.parse_radio_source(
            "Radio A|https://radio.example/live\nRadio A|https://radio.example/live\n",
            "source",
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(counts["accepted"], 1)

    def test_parse_holds_same_name_with_different_streams_as_ambiguous(self):
        records, counts = update_radio_catalog.parse_radio_source(
            "Radio A|https://radio.example/one\nRadio A|https://radio.example/two\n",
            "source",
        )
        self.assertEqual(records, [])
        self.assertEqual(counts["ambiguous_names"], 1)

    def test_radio_browser_payload_keeps_only_working_brazilian_stations(self):
        stations = update_radio_catalog.parse_radio_browser_payload([
            {"name": "Radio A", "countrycode": "BR", "lastcheckok": 1},
            {"name": "Radio B", "countrycode": "US", "lastcheckok": 1},
            {"name": "Radio C", "countrycode": "BR", "lastcheckok": 0},
        ])
        self.assertEqual([x["name"] for x in stations], ["Radio A"])

    def test_genre_tags_map_only_recognized_categories(self):
        self.assertEqual(update_radio_catalog.genre_from_tags("brazil, sertanejo, portuguese"), "Sertanejo")
        self.assertIsNone(update_radio_catalog.genre_from_tags("brazil, portuguese, online"))

    def test_expanded_explicit_tags_cover_brazilian_radio_categories(self):
        self.assertEqual(update_radio_catalog.genre_from_tags("funk carioca, brasil"), "Funk")
        self.assertEqual(update_radio_catalog.genre_from_tags("louvor, worship"), "Gospel")
        self.assertEqual(update_radio_catalog.genre_from_tags("news/talk, politics"), "Jornalismo")
        self.assertEqual(update_radio_catalog.genre_from_tags("indie pop"), "Indie")

    def test_radio_source_fetch_retries_transient_connection_resets(self):
        with patch.object(update_radio_catalog, "fetch", side_effect=[
            OSError("connection reset by peer"), "[]"
        ]) as mocked_fetch, patch.object(update_radio_catalog.time, "sleep") as mocked_sleep:
            result = update_radio_catalog.fetch_radio_source("https://radio.example/metadata")
        self.assertEqual(result, "[]")
        self.assertEqual(mocked_fetch.call_count, 2)
        mocked_sleep.assert_called_once_with(1.5)

    def test_radio_source_fetch_does_not_retry_non_transient_http_errors(self):
        import urllib.error
        error = urllib.error.HTTPError("https://radio.example/metadata", 404, "not found", {}, None)
        with patch.object(update_radio_catalog, "fetch", side_effect=error) as mocked_fetch:
            with self.assertRaises(urllib.error.HTTPError):
                update_radio_catalog.fetch_radio_source("https://radio.example/metadata")
        self.assertEqual(mocked_fetch.call_count, 1)

    def test_station_favicon_must_belong_to_homepage_domain(self):
        self.assertEqual(
            update_radio_catalog.safe_station_favicon({
                "homepage": "https://radio.example",
                "favicon": "https://www.radio.example/logo.png",
            }),
            "https://www.radio.example/logo.png",
        )
        self.assertIsNone(update_radio_catalog.safe_station_favicon({
            "homepage": "https://radio.example",
            "favicon": "https://third-party.example/logo.png",
        }))

    def test_station_name_normalization_preserves_radio_brand_word(self):
        self.assertNotEqual(
            update_radio_catalog.normalize_station_name("Radio Disney"),
            update_radio_catalog.normalize_station_name("Disney FM"),
        )

    def test_radio_browser_match_requires_exact_name_and_stream_or_unique_name(self):
        radio = {"name": "Rádio A FM", "stream_url": "https://radio.example/live"}
        station = {
            "stationuuid": "station-a", "name": "Radio A",
            "url": "https://radio.example/live", "url_resolved": "https://radio.example/live",
            "countrycode": "BR", "lastcheckok": 1,
        }
        matched, method = update_radio_catalog.match_radio_browser_station(radio, [station])
        self.assertEqual(matched, station)
        self.assertEqual(method, "exact_stream_and_name")

    def test_radio_browser_metadata_fills_only_missing_genre_and_logo(self):
        radios = [{
            "id": "radio.radio-a", "name": "Rádio A FM",
            "stream_url": "https://radio.example/live", "genre": None, "logo_url": None,
        }]
        stations = [{
            "stationuuid": "station-a", "name": "Radio A",
            "url": "https://radio.example/live", "url_resolved": "https://radio.example/live",
            "homepage": "https://radio.example", "favicon": "https://radio.example/logo.png",
            "tags": "sertanejo,brazil", "countrycode": "BR", "lastcheckok": 1,
        }]
        counts = update_radio_catalog.apply_radio_browser_metadata(radios, stations)
        self.assertEqual(radios[0]["genre"], "Sertanejo")
        self.assertEqual(radios[0]["logo_url"], "https://radio.example/logo.png")
        self.assertEqual(counts["genres_filled"], 1)
        self.assertEqual(counts["logos_filled"], 1)

    def test_radio_browser_never_overwrites_existing_genre_or_logo(self):
        radios = [{
            "id": "radio.radio-a", "name": "Rádio A FM",
            "stream_url": "https://radio.example/live",
            "genre": "Jazz", "logo_url": "https://existing.example/logo.png",
        }]
        stations = [{
            "stationuuid": "station-a", "name": "Radio A",
            "url": "https://radio.example/live", "url_resolved": "https://radio.example/live",
            "homepage": "https://radio.example", "favicon": "https://radio.example/new-logo.png",
            "tags": "sertanejo", "countrycode": "BR", "lastcheckok": 1,
        }]
        counts = update_radio_catalog.apply_radio_browser_metadata(radios, stations)
        self.assertEqual(radios[0]["genre"], "Jazz")
        self.assertEqual(radios[0]["logo_url"], "https://existing.example/logo.png")
        self.assertEqual(counts["genres_filled"], 0)
        self.assertEqual(counts["logos_filled"], 0)

    def test_radio_browser_only_fallback_persists_metadata_when_stream_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sources").mkdir(parents=True)
            (root / "catalog/radios").mkdir(parents=True)
            (root / "sources/sources.json").write_text(json.dumps({"sources": [
                {"id": "saimoplayer-radio-reference", "category": "radio", "format": "pipe-delimited",
                 "enabled": True, "priority": 10,
                 "url": "https://raw.githubusercontent.com/fki1976/SaimoPlayer/main/vod/radios.txt"},
                {"id": "radio-browser-br-metadata", "category": "radio", "format": "radio-browser-json",
                 "enabled": True, "priority": 20,
                 "url": "https://de1.api.radio-browser.info/json/stations/bycountrycodeexact/BR?hidebroken=true&limit=10000&order=name"},
            ]}), encoding="utf-8")
            (root / "catalog/radios/radios.json").write_text(json.dumps({
                "schema_version": 1,
                "radios": [{
                    "id": "radio.radio-a", "name": "Rádio A FM",
                    "stream_url": "https://radio.example/live", "genre": None, "logo_url": None,
                }],
            }), encoding="utf-8")

            station = {
                "stationuuid": "station-a", "name": "Radio A",
                "url": "https://radio.example/live", "url_resolved": "https://radio.example/live",
                "homepage": "https://radio.example", "favicon": "https://radio.example/logo.png",
                "tags": "sertanejo", "countrycode": "BR", "lastcheckok": 1,
            }

            def fake_fetch(url):
                if "radio-browser.info" in url:
                    return json.dumps([station])
                raise OSError("authorized stream reference temporarily unavailable")

            with patch.object(update_radio_catalog, "fetch", side_effect=fake_fetch):
                report = update_radio_catalog.update(root)

            saved = json.loads((root / "catalog/radios/radios.json").read_text(encoding="utf-8"))
            self.assertTrue(report["catalog_mutated"])
            self.assertEqual(saved["radios"][0]["genre"], "Sertanejo")
            self.assertEqual(saved["radios"][0]["logo_url"], "https://radio.example/logo.png")

    def test_radio_browser_ambiguous_name_is_not_used(self):
        radio = {"name": "Rádio A FM", "stream_url": "https://unmatched.example/live"}
        stations = [
            {"stationuuid": "a1", "name": "Radio A", "url": "https://one.example/live", "countrycode": "BR", "lastcheckok": 1},
            {"stationuuid": "a2", "name": "Radio A", "url": "https://two.example/live", "countrycode": "BR", "lastcheckok": 1},
        ]
        matched, method = update_radio_catalog.match_radio_browser_station(radio, stations)
        self.assertIsNone(matched)
        self.assertEqual(method, "ambiguous_name")

    def test_merge_adds_new_station_and_preserves_existing_metadata(self):
        existing = [{
            "id": "radio.radio-a", "name": "Radio A",
            "stream_url": "https://old.example/live",
            "logo_url": "https://logo.example/a.png", "genre": "Jazz",
        }]
        incoming = [
            {"id": "radio.radio-a", "name": "Radio A", "stream_url": "https://new.example/live",
             "logo_url": None, "genre": None, "source_id": "source"},
            {"id": "radio.radio-b", "name": "Radio B", "stream_url": "https://radio.example/b",
             "logo_url": None, "genre": None, "source_id": "source"},
        ]
        merged, counts = update_radio_catalog.merge_radio_records(existing, incoming)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["stream_url"], "https://old.example/live")
        self.assertEqual(merged[0]["logo_url"], "https://logo.example/a.png")
        self.assertEqual(merged[0]["genre"], "Jazz")
        self.assertEqual(counts["stream_conflicts"], 1)
        self.assertEqual(counts["added"], 1)

    def test_merge_fills_only_missing_stream(self):
        existing = [{"id": "radio.radio-a", "name": "Radio A", "stream_url": None}]
        incoming = [{"id": "radio.radio-a", "name": "Radio A",
                     "stream_url": "https://radio.example/live", "source_id": "source"}]
        merged, counts = update_radio_catalog.merge_radio_records(existing, incoming)
        self.assertEqual(merged[0]["stream_url"], "https://radio.example/live")
        self.assertEqual(counts["filled_stream"], 1)

    def test_merge_does_not_guess_when_names_are_ambiguous(self):
        existing = [
            {"id": "radio.radio-a-1", "name": "Radio A", "stream_url": "https://a.example/live"},
            {"id": "radio.radio-a-2", "name": "Radio A", "stream_url": "https://b.example/live"},
        ]
        incoming = [{"id": "radio.radio-a", "name": "Radio A",
                     "stream_url": "https://new.example/live"}]
        merged, counts = update_radio_catalog.merge_radio_records(existing, incoming)
        self.assertEqual(len(merged), 2)
        self.assertEqual(counts["ambiguous_matches"], 1)


if __name__ == "__main__":
    unittest.main()
