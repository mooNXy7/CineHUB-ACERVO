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
            "Radio A|https://radio.example/one\\nRadio A|https://radio.example/two\\n",
            "source",
        )
        self.assertEqual(records, [])
        self.assertEqual(counts["ambiguous_names"], 1)

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
