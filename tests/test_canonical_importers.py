import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acervo_v2.importers import (
    apply_radio_reference_recovery, parse_channels_json, parse_epg_channel_index, parse_m3u,
    parse_radios_json, parse_radios_text, parse_vod_catalog, iter_vod_catalog,
    parse_vod_reference_movies, parse_vod_reference_series,
)
from acervo_v2.xmltv import parse_xmltv
import build_candidate_catalog
import enrich_vod_metadata as enrich
import suggest_vod_tmdb_matches as suggest
import apply_vod_metadata_patch as apply_metadata
import apply_vod_tmdb_id_candidates as apply_ids


FIXTURES = ROOT / "tests/fixtures/canonical"


class CanonicalParserTests(unittest.TestCase):
    def test_m3u_preserves_extinf_and_distinct_stream_variants(self):
        records, quarantine = parse_m3u(
            (FIXTURES / "channels.m3u").read_text(encoding="utf-8"),
            "fixture-m3u", "tests/fixtures/canonical/channels.m3u"
        )
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["id"], records[1]["id"])
        self.assertEqual(records[0]["streams"][0]["url"], "https://stream.example.test/live-a.m3u8")
        self.assertEqual(records[1]["streams"][0]["url"], "https://backup.example.test/live-b.m3u8")
        self.assertEqual(records[0]["raw"]["attributes"]["group-title"], "Públicos")
        self.assertEqual(quarantine[0]["reason"], "unsupported_or_missing_scheme")

    def test_radio_two_column_and_legacy_four_column_are_supported(self):
        two, q_two = parse_radios_text(
            (FIXTURES / "radios-two-column.txt").read_text(encoding="utf-8"),
            "radio-fixture", "radios-two-column.txt"
        )
        legacy, q_legacy = parse_radios_text(
            (FIXTURES / "radios-legacy.txt").read_text(encoding="utf-8"),
            "radio-legacy", "radios-legacy.txt"
        )
        self.assertEqual(two[0]["name"], "Estação Exemplo")
        self.assertEqual(len(two[0]["streams"]), 1)
        self.assertEqual(two[1]["streams"], [])
        self.assertEqual(q_two[0]["reason"], "image_url_in_audio_stream")
        self.assertEqual(legacy[0]["id"], "legacy-001")
        self.assertEqual(legacy[0]["logo_url"], "https://logos.example.test/radio.png")
        self.assertEqual(len(legacy[0]["streams"]), 1)
        again, _ = parse_radios_text(
            (FIXTURES / "radios-two-column.txt").read_text(encoding="utf-8"),
            "radio-fixture", "radios-two-column.txt"
        )
        self.assertEqual([x["id"] for x in two], [x["id"] for x in again])

    def test_radio_json_preserves_unknown_fields_and_deduplicates_identical_variants(self):
        doc = {"radios": [{"id": "radio.test", "name": "Rádio Teste", "stream_url": "https://a.example.test/live",
                           "streams": [{"url": "https://a.example.test/live", "source_id": "json-fixture"}],
                           "genre": None, "custom_unknown": {"keep": True}}]}
        records, quarantine = parse_radios_json(doc, "json-fixture")
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["streams"]), 1)
        self.assertTrue(records[0]["raw"]["custom_unknown"]["keep"])
        self.assertEqual(quarantine, [])

    def test_radio_json_quarantine_retains_provenance_and_flags_missing_stream(self):
        doc = {"radios": [
            {"id": "radio.image", "name": "Estação com logo", "stream_url": "https://assets.example.test/logo.png",
             "source_id": "reference-catalog"},
            {"id": "radio.missing", "name": "https://audio.example.test/live", "stream_url": ""},
        ]}
        records, quarantine = parse_radios_json(doc, "radio-fixture")
        self.assertEqual(len(records), 2)
        self.assertEqual({item["reason"] for item in quarantine},
                         {"image_url_in_audio_stream", "missing_stream_url"})
        self.assertTrue(all(item["provenance"][0]["source_ref"] == "catalog/radios/radios.json"
                            for item in quarantine))
        missing = next(item for item in quarantine if item["reason"] == "missing_stream_url")
        self.assertEqual(missing["raw"]["name"], "https://audio.example.test/live")

    def test_radio_parser_detects_image_url_extension_inside_query_value(self):
        records, quarantine = parse_radios_json({"radios": [{
            "id": "radio.query-logo",
            "name": "Tua Rádio Fátima",
            "stream_url": "https://www.tuaradio.com.br/image/resize?w=90&h=71&q=90&src=intranet/userfiles/logo.png",
        }]})
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["streams"], [])
        self.assertTrue(any(item.get("reason") == "image_url_in_audio_stream" for item in quarantine))

    def test_radio_reference_recovery_uses_exact_match_and_preserves_original_fields(self):
        document = {"radios": [
            {"id": "radio.image", "name": "https://audio.example.test/live",
             "stream_url": "https://assets.example.test/station.png"},
            {"id": "radio.missing", "name": "https://audio.example.test/other", "stream_url": ""},
        ]}
        records, quarantine = parse_radios_json(document)
        reference = {
            "source": {"source_id": "reference-radio-catalog",
                       "source_ref": "https://github.com/fki1976/SaimoPlayer/blob/pinned/vod/radios.txt",
                       "commit": "pinned", "blob_sha": "blob"},
            "records": [
                {"record_id": "radio.image", "source_name_url": "https://audio.example.test/live",
                 "name": "Station One", "stream_url": "https://audio.example.test/live",
                 "original_stream_url": "https://assets.example.test/station.png",
                 "logo_url_candidate": "https://assets.example.test/station.png",
                 "match_method": "casefold_and_trim_trailing_slash", "match_count": 1},
                {"record_id": "radio.missing", "source_name_url": "https://audio.example.test/other",
                 "name": "Station Two", "stream_url": "https://audio.example.test/other",
                 "original_stream_url": None, "logo_url_candidate": None,
                 "match_method": "casefold_and_trim_trailing_slash", "match_count": 1},
            ],
        }
        result = apply_radio_reference_recovery(records, quarantine, reference)
        self.assertEqual(result["applied_records"], 2)
        self.assertEqual(result["streams_added"], 2)
        self.assertEqual(result["logo_candidates_promoted"], 1)
        self.assertEqual(result["quarantine_items_resolved"], 2)
        first = next(item for item in records if item["id"] == "radio.image")
        self.assertEqual(first["name"], "Station One")
        self.assertEqual(first["raw"]["name"], "https://audio.example.test/live")
        self.assertEqual(first["raw"]["stream_url"], "https://assets.example.test/station.png")
        self.assertEqual(first["logo_url"], "https://assets.example.test/station.png")
        self.assertEqual(first["reference_recovery"]["logo_status"], "unverified")
        self.assertEqual(first["streams"][0]["url"], "https://audio.example.test/live")
        self.assertEqual(first["streams"][0]["source_id"], "catalog-existing")
        self.assertTrue(all(item.get("resolution", {}).get("status") == "recovered_from_pinned_reference"
                            for item in quarantine))

    def test_radio_reference_recovery_rejects_a_different_stream_url(self):
        records, quarantine = parse_radios_json({"radios": [
            {"id": "radio.mismatch", "name": "https://audio.example.test/live",
             "stream_url": "https://assets.example.test/logo.png"},
        ]})
        reference = {
            "source": {"source_id": "reference-radio-catalog"},
            "records": [{
                "record_id": "radio.mismatch",
                "source_name_url": "https://audio.example.test/live",
                "name": "Station",
                "stream_url": "https://different.example.test/live",
                "match_count": 1,
            }],
        }
        result = apply_radio_reference_recovery(records, quarantine, reference)
        self.assertEqual(result["applied_records"], 0)
        self.assertEqual(result["invalid_match_ids"], ["radio.mismatch"])
        self.assertTrue(any(item["reason"] == "radio_reference_stream_mismatch" for item in quarantine))
        self.assertEqual(records[0]["name"], "https://audio.example.test/live")
        self.assertEqual(records[0]["streams"], [])

    def test_vod_reference_movie_and_series_formats_keep_variants_and_provider_refs(self):
        movies, q_movies = parse_vod_reference_movies(
            (FIXTURES / "vod-movies.txt").read_text(encoding="utf-8"),
            "saimo-format-fixture", "vod/filmes-A.txt"
        )
        self.assertEqual(len(movies), 1)
        self.assertEqual(len(movies[0]["sources"]), 2)
        self.assertEqual(movies[0]["sources"][0]["audio"], "dub")
        self.assertEqual(movies[0]["provider_refs"][0]["ref"], "provider-movie-10")
        self.assertEqual(q_movies, [])
        series, q_series = parse_vod_reference_series(
            (FIXTURES / "vod-series.txt").read_text(encoding="utf-8"),
            "saimo-format-fixture", "vod/series-A-0.txt"
        )
        self.assertEqual(len(series), 1)
        self.assertEqual([x["season"] for x in series[0]["seasons"]], [1, 2])
        self.assertEqual(len(series[0]["seasons"][0]["episodes"][0]["sources"]), 1)
        leg_episode = next(x for x in series[0]["seasons"][0]["episodes"] if x["audio"] == "leg")
        self.assertEqual(leg_episode["provider_refs"][0]["ref"], "provider-episode-10")
        self.assertEqual(q_series, [])

    def test_epg_channel_index_preserves_provider_ids_and_is_deterministic(self):
        document = {"sources": {"feed-a": {"fetched_at": "2026-10-26T15:17:21Z",
            "channel_count": 1, "channels": [{"id": "provider-123",
            "display_names": ["Canal Exemplo"], "future_field": "preserved"}]}}}
        first, quarantine = parse_epg_channel_index(document)
        second, _ = parse_epg_channel_index(document)
        self.assertEqual(first[0]["id"], second[0]["id"])
        self.assertEqual(first[0]["provider_channel_id"], "provider-123")
        self.assertEqual(first[0]["raw"]["channel"]["future_field"], "preserved")
        self.assertEqual(first[0]["source_id"], "feed-a")
        self.assertEqual(quarantine, [])

    def test_xmltv_preserves_child_text_and_timezone_and_quarantines_invalid_programmes(self):
        channels, programmes, quarantine = parse_xmltv(
            (FIXTURES / "sample.xml").read_bytes(), "xmltv-fixture", "sample.xml"
        )
        self.assertEqual(channels[0]["display_names"], ["Canal Exemplo", "Canal Exemplo HD"])
        self.assertEqual(programmes[0]["title"], "Jornal da Manhã")
        self.assertEqual(programmes[0]["description"], "Programa de notícias.")
        self.assertEqual(programmes[0]["start"][-6:], "-03:00")
        self.assertEqual(quarantine[0]["reason"], "invalid_programme")

    def test_channels_json_keeps_raw_unknown_fields_and_stable_identity(self):
        doc = {"channels": [{"id": "br.tv.exemplo", "name": "TV Exemplo",
                             "sources": [{"url": "https://a.example.test/live"}],
                             "future_field": {"unmodeled": 7}}]}
        one, _ = parse_channels_json(doc, "catalog")
        two, _ = parse_channels_json(doc, "catalog")
        self.assertEqual(one[0]["id"], two[0]["id"])
        self.assertEqual(one[0]["raw"]["future_field"]["unmodeled"], 7)
        self.assertEqual(one[0]["streams"][0]["entity_id"], "br.tv.exemplo")

    def test_vod_catalog_rejects_path_traversal_and_reads_index_detail_relationship(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog/vod/index").mkdir(parents=True)
            (root / "catalog/vod/details/movies").mkdir(parents=True)
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}
            }), encoding="utf-8")
            (root / "catalog/vod/index/movies.json").write_text(json.dumps([{
                "id": "movie-1", "title": "Filme", "detail_path": "catalog/vod/details/movies/A.json"
            }]), encoding="utf-8")
            (root / "catalog/vod/details/movies/A.json").write_text(json.dumps([{
                "id": "movie-1", "title": "Filme", "type": "movie", "year": "2020",
                "sources": [{"url": "https://vod.example.test/a.m3u8"}], "custom": "kept"
            }]), encoding="utf-8")
            records, quarantine = parse_vod_catalog(root)
            self.assertEqual(records[0]["id"], "movie-1")
            self.assertEqual(records[0]["raw"]["detail"]["custom"], "kept")
            self.assertEqual(records[0]["sources"][0]["url"], "https://vod.example.test/a.m3u8")
            self.assertEqual(quarantine, [])
            index = root / "catalog/vod/index/movies.json"
            index.write_text(json.dumps([{"id": "movie-1", "detail_path": "../../outside.json"}]), encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_vod_catalog(root)


    def test_vod_identity_merges_duplicate_provider_entities_and_splits_conflicting_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for section in ("series", "anime", "doramas"):
                (root / f"catalog/vod/index/{section}.json").parent.mkdir(parents=True, exist_ok=True)
                (root / f"catalog/vod/details/{section}").mkdir(parents=True, exist_ok=True)
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "categories": {
                    "series": {"index_path": "catalog/vod/index/series.json"},
                    "anime": {"index_path": "catalog/vod/index/anime.json"},
                    "doramas": {"index_path": "catalog/vod/index/doramas.json"},
                }
            }), encoding="utf-8")
            entries = {
                "series": [
                    {"id": "series-shared", "title": "Título Original", "subtype": "anime",
                     "year": "2020", "tmdb_id": "100", "detail_path": "catalog/vod/details/series/A.json"},
                    {"id": "series-my-name", "title": "My Name", "subtype": "dorama",
                     "year": "2021", "tmdb_id": "110356", "detail_path": "catalog/vod/details/series/M.json"},
                ],
                "anime": [
                    {"id": "series-shared", "title": "Título Original", "subtype": "anime",
                     "year": "2020", "tmdb_id": "100", "detail_path": "catalog/vod/details/anime/A.json"},
                    {"id": "series-translated", "title": "Translated Title", "subtype": "anime",
                     "year": "2020", "tmdb_id": "100", "detail_path": "catalog/vod/details/anime/T.json"},
                ],
                "doramas": [
                    {"id": "series-my-name", "title": "My Name", "subtype": "dorama",
                     "year": "2021", "tmdb_id": "2317", "detail_path": "catalog/vod/details/doramas/M.json"},
                ],
            }
            for section, rows in entries.items():
                (root / f"catalog/vod/index/{section}.json").write_text(json.dumps(rows), encoding="utf-8")

            def detail(ident, title, tmdb, source_url, extra=None):
                value = {
                    "id": ident, "title": title, "type": "series",
                    "subtype": "anime" if tmdb == "100" else "dorama",
                    "year": "2020" if tmdb == "100" else "2021", "tmdb_id": tmdb,
                    "sources": [{"url": source_url, "audio": "dub", "source_id": "provider-a"}],
                    "seasons": [{"season": 1, "episodes": [{
                        "episode": 1, "audio": "dub",
                        "sources": [{"url": "https://vod.example.test/shared.m3u8",
                                     "audio": "dub", "source_id": "provider-a"}],
                        "provider_refs": [{"provider": "p", "ref": f"{tmdb}/1/1"}],
                    }]}],
                }
                if extra:
                    value.update(extra)
                return value

            (root / "catalog/vod/details/series/A.json").write_text(json.dumps([
                detail("series-shared", "Título Original", "100",
                       "https://vod.example.test/shared.m3u8", {"unknown_field": {"keep": 1}})
            ]), encoding="utf-8")
            (root / "catalog/vod/details/anime/A.json").write_text(json.dumps([
                detail("series-shared", "Título Original", "100",
                       "https://vod.example.test/shared.m3u8", {"other_unknown": "preserve"})
            ]), encoding="utf-8")
            (root / "catalog/vod/details/anime/T.json").write_text(json.dumps([
                detail("series-translated", "Translated Title", "100",
                       "https://vod.example.test/translated.m3u8")
            ]), encoding="utf-8")
            (root / "catalog/vod/details/series/M.json").write_text(json.dumps([
                detail("series-my-name", "My Name", "110356",
                       "https://vod.example.test/my-name-110356.m3u8")
            ]), encoding="utf-8")
            (root / "catalog/vod/details/doramas/M.json").write_text(json.dumps([
                detail("series-my-name", "My Name", "2317",
                       "https://vod.example.test/my-name-2317.m3u8")
            ]), encoding="utf-8")

            identity_report = {}
            quarantine = []
            first = list(iter_vod_catalog(root, quarantine=quarantine, identity_report=identity_report))
            second, _ = parse_vod_catalog(root)
            self.assertEqual(quarantine, [])
            self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
            self.assertEqual(len(first), 3)
            self.assertEqual(identity_report["input_index_entries"], 5)
            self.assertEqual(identity_report["canonical_identity_groups"], 3)
            self.assertEqual(identity_report["identity_groups_merged"], 1)
            self.assertEqual(identity_report["index_entries_consolidated"], 2)
            self.assertEqual(identity_report["same_legacy_id_duplicate_groups"], 1)
            self.assertEqual(identity_report["provider_identity_groups_merged_across_legacy_ids"], 1)
            self.assertEqual(identity_report["legacy_ids_reused_across_distinct_identities"], 1)
            self.assertEqual(identity_report["identity_groups_affected_by_legacy_id_conflict"], 2)
            self.assertEqual(identity_report["output_records"], 3)
            self.assertEqual(identity_report["identity_audit_version"], 2)
            self.assertEqual(len(identity_report["consolidations"]), 1)
            self.assertEqual(identity_report["consolidations"][0]["canonical_id"], "series-shared")
            self.assertEqual(identity_report["consolidations"][0]["index_reference_count"], 3)
            self.assertEqual(len(identity_report["legacy_id_conflicts"]), 1)
            self.assertEqual(identity_report["legacy_id_conflicts"][0]["legacy_id"], "series-my-name")
            self.assertEqual(
                {group["tmdb_ids"][0] for group in identity_report["legacy_id_conflicts"][0]["identity_groups"]},
                {"110356", "2317"},
            )
            shared = next(item for item in first if item["external_ids"]["tmdb"] == "100")
            self.assertEqual(shared["id"], "series-shared")
            self.assertEqual(shared["legacy_ids"], ["series-shared", "series-translated"])
            self.assertEqual(shared["catalog_sections"], ["series", "anime"])
            self.assertIn("Translated Title", shared["aliases"])
            self.assertEqual(len(shared["provenance"]), 3)
            self.assertEqual({item["url"] for item in shared["sources"]}, {
                "https://vod.example.test/shared.m3u8",
                "https://vod.example.test/translated.m3u8",
            })
            self.assertTrue(shared["raw"]["detail"]["unknown_field"]["keep"])
            self.assertTrue(any(x["detail"].get("other_unknown") == "preserve"
                                for x in shared["raw"].get("alternate_details", [])))
            episode = shared["seasons"][0]["episodes"][0]
            self.assertEqual(len(episode["provider_refs"]), 1)
            all_variants = list(shared["sources"]) + list(episode["sources"])
            self.assertEqual(len({x["id"] for x in all_variants}), len(all_variants))
            self.assertEqual({x["entity_id"] for x in all_variants}, {shared["id"]})
            self.assertNotEqual(shared["sources"][0]["id"], episode["sources"][0]["id"])

            my_names = [item for item in first if item["title"] == "My Name"]
            self.assertEqual({item["external_ids"]["tmdb"] for item in my_names}, {"110356", "2317"})
            self.assertEqual(len({item["id"] for item in my_names}), 2)
            self.assertIn("series-my-name", {item["id"] for item in my_names})
            self.assertTrue(any(item["id"].startswith("series-my-name~") for item in my_names))
            self.assertTrue(all(item["identity_resolution"]["legacy_id_conflict"] for item in my_names))

    def test_vod_identity_override_corrects_only_exact_reference_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for section in ("series", "doramas"):
                (root / f"catalog/vod/index/{section}.json").parent.mkdir(parents=True, exist_ok=True)
                (root / f"catalog/vod/details/{section}").mkdir(parents=True, exist_ok=True)
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "categories": {
                    "series": {"index_path": "catalog/vod/index/series.json"},
                    "doramas": {"index_path": "catalog/vod/index/doramas.json"},
                }
            }), encoding="utf-8")
            entries = {
                "series": [
                    {"id": "series-meu-nome-e", "title": "Meu Nome é", "subtype": "dorama",
                     "year": "2021", "tmdb_id": "2317", "detail_path": "catalog/vod/details/series/M-007.json"},
                    {"id": "series-my-name", "title": "My Name", "subtype": "dorama",
                     "year": "2021", "tmdb_id": "110356", "detail_path": "catalog/vod/details/series/M-013.json"},
                ],
                "doramas": [
                    {"id": "series-my-name", "title": "My Name", "subtype": "dorama",
                     "year": "2021", "tmdb_id": "2317", "detail_path": "catalog/vod/details/doramas/M-000.json"},
                ],
            }
            for section, rows in entries.items():
                (root / f"catalog/vod/index/{section}.json").write_text(json.dumps(rows), encoding="utf-8")

            def detail(ident, title, tmdb):
                return [{
                    "id": ident, "title": title, "subtype": "dorama", "year": "2021", "tmdb_id": tmdb,
                    "seasons": [{"season": 1, "episodes": [{
                        "episode": 1, "audio": "dub",
                        "sources": [{"url": "https://vod.example.test/my-name/1", "source_id": "provider-a"}],
                        "provider_refs": [{"provider": "p", "ref": "110356/1/1"}],
                    }]}],
                }]

            (root / "catalog/vod/details/series/M-007.json").write_text(json.dumps(detail("series-meu-nome-e", "Meu Nome é", "2317")), encoding="utf-8")
            (root / "catalog/vod/details/series/M-013.json").write_text(json.dumps(detail("series-my-name", "My Name", "110356")), encoding="utf-8")
            (root / "catalog/vod/details/doramas/M-000.json").write_text(json.dumps(detail("series-my-name", "My Name", "2317")), encoding="utf-8")
            override_doc = {
                "source": {"source_id": "reference-vod-identity",
                           "files": [{"source_ref": "https://reference.example/catalogo-series.txt"}],
                           "commit": "pinned"},
                "overrides": [{
                    "id": "my-name-2021-tmdb-correction", "expected_matches": 2,
                    "match": {"titles": ["Meu Nome é", "My Name"], "media_type": "dorama",
                              "year": "2021", "tmdb_id": "2317",
                              "catalog_sections": ["series", "doramas"],
                              "legacy_ids": ["series-meu-nome-e", "series-my-name"]},
                    "canonical": {"id": "series-my-name", "tmdb_id": "110356", "title": "My Name", "year": "2021"},
                    "reason": "Pinned reference confirms TMDB 110356 for My Name 2021.",
                    "evidence": [{"path": "catalogo-series.txt", "line": 1, "text": "110356\\tMy Name\\t2021\\t8"}],
                }],
            }
            identity_report, quarantine = {}, []
            records = list(iter_vod_catalog(root, quarantine=quarantine,
                                            identity_report=identity_report,
                                            identity_overrides=override_doc))
            self.assertEqual(quarantine, [])
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["id"], "series-my-name")
            self.assertEqual(record["external_ids"]["tmdb"], "110356")
            self.assertEqual(set(record["legacy_ids"]), {"series-meu-nome-e", "series-my-name"})
            self.assertEqual(set(record["catalog_sections"]), {"series", "doramas"})
            self.assertEqual(record["raw"]["detail"]["tmdb_id"], "2317")
            self.assertEqual(record["identity_resolution"]["identity_override"]["source_tmdb_id"], "2317")
            self.assertEqual(identity_report["legacy_id_conflicts"], [])
            self.assertEqual(identity_report["identity_overrides"][0]["applied_index_reference_count"], 2)
            self.assertEqual(identity_report["consolidations"][0]["index_reference_count"], 3)
            self.assertEqual(identity_report["canonical_identity_groups"], 1)
            self.assertEqual(identity_report["output_records"], 1)

    def test_vod_identity_requires_matching_year_and_scopes_variants_to_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog/vod/index").mkdir(parents=True)
            (root / "catalog/vod/details/movies").mkdir(parents=True)
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}
            }), encoding="utf-8")
            rows = [
                {"id": "movie-same-title-2020", "title": "Same Title", "year": "2020",
                 "tmdb_id": "900", "detail_path": "catalog/vod/details/movies/A.json"},
                {"id": "movie-same-title-2022", "title": "Same Title", "year": "2022",
                 "tmdb_id": "900", "detail_path": "catalog/vod/details/movies/A.json"},
                {"id": "movie-same-title-no-id", "title": "Same Title", "year": "2020",
                 "detail_path": "catalog/vod/details/movies/A.json"},
            ]
            (root / "catalog/vod/index/movies.json").write_text(json.dumps(rows), encoding="utf-8")
            shared_url = "https://vod.example.test/shared-across-entities.m3u8"
            details = [
                {"id": "movie-same-title-2020", "title": "Same Title", "type": "movie",
                 "year": "2020", "tmdb_id": "900",
                 "sources": [{"url": shared_url, "source_id": "provider-a"}]},
                {"id": "movie-same-title-2022", "title": "Same Title", "type": "movie",
                 "year": "2022", "tmdb_id": "900",
                 "sources": [{"url": shared_url, "source_id": "provider-a"}]},
                {"id": "movie-same-title-no-id", "title": "Same Title", "type": "movie",
                 "year": "2020", "sources": [{"url": shared_url, "source_id": "provider-a"}]},
            ]
            (root / "catalog/vod/details/movies/A.json").write_text(json.dumps(details), encoding="utf-8")
            records, quarantine = parse_vod_catalog(root)
            self.assertEqual(quarantine, [])
            self.assertEqual(len(records), 3)
            self.assertEqual({item["year"] for item in records}, {"2020", "2022"})
            self.assertEqual(len({item["id"] for item in records}), 3)
            variants = [item["sources"][0] for item in records]
            self.assertEqual(len({item["id"] for item in variants}), 3)
            self.assertEqual({item["entity_id"] for item in variants}, {item["id"] for item in records})
            self.assertEqual({item["scope"] for item in variants}, {"entity"})

    def test_import_canonical_cli_resolves_package_from_external_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "candidate.json"
            fixture = FIXTURES / "channels.m3u"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/import_canonical.py"),
                 "--format", "m3u", "--input", str(fixture),
                 "--source-id", "external-cwd-fixture", "--root", tmp,
                 "--output", str(output)],
                cwd=tmp, check=True, capture_output=True, text=True,
            )
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["domain"], "channels")
            self.assertEqual(len(document["records"]), 3)
            self.assertGreaterEqual(len(document["quarantine"]), 1)

class CandidateBuildTests(unittest.TestCase):
    def test_candidate_build_is_offline_and_never_mutates_active_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in ["catalog/channels", "catalog/radios", "catalog/vod/index",
                         "catalog/vod/details/movies", "catalog/epg", "sources/m3u"]:
                (root / path).mkdir(parents=True, exist_ok=True)
            (root / "catalog/channels/channels.json").write_text(json.dumps({
                "schema_version": 1, "channels": [{"id": "ch.test", "name": "Canal Teste",
                "logo_url": "https://logos.example.test/ch.png", "sources": [{"url": "https://stream.example.test/a.m3u8"}]}]
            }), encoding="utf-8")
            (root / "catalog/radios/radios.json").write_text(json.dumps({
                "schema_version": 1, "radios": [{"id": "radio.test", "name": "Rádio Teste",
                "stream_url": "https://audio.example.test/live", "logo_url": "https://logos.example.test/r.png"}]
            }), encoding="utf-8")
            (root / "catalog/vod/index.json").write_text(json.dumps({
                "categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}
            }), encoding="utf-8")
            (root / "catalog/vod/index/movies.json").write_text(json.dumps([{
                "id": "movie.test", "title": "Filme Teste", "detail_path": "catalog/vod/details/movies/A.json"
            }]), encoding="utf-8")
            (root / "catalog/vod/details/movies/A.json").write_text(json.dumps([{
                "id": "movie.test", "title": "Filme Teste", "type": "movie", "year": "2020",
                "sources": [{"url": "https://vod.example.test/movie.m3u8"}]
            }]), encoding="utf-8")
            (root / "catalog/epg/sources.json").write_text(json.dumps({
                "sources": [{"id": "epg.test", "name": "EPG Teste", "type": "xmltv",
                "format": "xmltv", "url": "https://epg.example.test/epg.xml", "priority": 1, "enabled": True}]
            }), encoding="utf-8")
            (root / "sources/sources.json").write_text(json.dumps({"sources": [{
                "id": "public-test", "name": "Public test", "category": "channels",
                "url": "https://source.example.test/list.m3u", "format": "m3u",
                "enabled": True, "priority": 10, "license": "fixture"
            }]}), encoding="utf-8")
            (root / "catalog/epg/channel-map.json").write_text(json.dumps({
                "meuguia_codes": {"Canal Teste": "CT"}, "guiadetv_slugs": {}, "xmltv_aliases": {}
            }), encoding="utf-8")
            (root / "catalog/epg/xmltv-channels.json").write_text(json.dumps({
                "sources": {"epg.test": {"fetched_at": "2026-10-26T15:17:21Z", "channel_count": 1,
                "channels": [{"id": "CT", "display_names": ["Canal Teste"]}]}}
            }), encoding="utf-8")
            (root / "sources/m3u/public-brazil.m3u").write_text("#EXTM3U\n", encoding="utf-8")
            protected = {p: (root / p).read_bytes() for p in [
                "catalog/channels/channels.json", "catalog/radios/radios.json",
                "catalog/vod/index.json", "catalog/vod/index/movies.json",
                "catalog/vod/details/movies/A.json", "catalog/epg/sources.json",
                "catalog/epg/channel-map.json", "sources/sources.json"
            ]}
            output = root / "candidate"
            # Exercise the documented CLI from outside the repository. This catches
            # sys.path regressions hidden when importing the script from the test runner.
            env = os.environ.copy()
            env["SOURCE_DATE_EPOCH"] = "1760000000"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_candidate_catalog.py"),
                 "--root", str(root), "--output", str(output)],
                cwd=tmp, env=env, check=True, capture_output=True, text=True,
            )
            second_output = root / "candidate-second"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_candidate_catalog.py"),
                 "--root", str(root), "--output", str(second_output)],
                cwd=tmp, env=env, check=True, capture_output=True, text=True,
            )
            self.assertEqual(
                sorted(p.name for p in output.iterdir()),
                sorted(p.name for p in second_output.iterdir()),
            )
            for candidate_file in output.iterdir():
                self.assertEqual(candidate_file.read_bytes(),
                                 (second_output / candidate_file.name).read_bytes())
            for path, content in protected.items():
                self.assertEqual((root / path).read_bytes(), content)
            self.assertTrue((output / "manifest.json").exists())
            self.assertFalse(json.loads((output / "report.json").read_text())["active_catalogs_modified"])
            epg_channels = json.loads((output / "epg-channels.json").read_text())["records"]
            epg_mappings = json.loads((output / "epg-mappings.json").read_text())["records"]
            self.assertEqual(len(epg_channels), 1)
            self.assertEqual(epg_channels[0]["provider_channel_id"], "CT")
            self.assertEqual(epg_channels[0]["source_priority"], 1)
            self.assertEqual(epg_mappings[0]["channel_id"], "ch.test")
            self.assertEqual(epg_mappings[0]["candidate_channel_ids"], ["ch.test"])
            self.assertEqual(epg_mappings[0]["match_status"], "matched")
            quality_audit = json.loads((output / "report.json").read_text())["quality_audit"]
            self.assertEqual(quality_audit["epg"]["channel_records"], 1)
            self.assertEqual(quality_audit["logos"]["local_image_files"], 0)
            from validate_schemas import validate_candidate_integrity
            integrity_errors, metrics = validate_candidate_integrity(output)
            self.assertEqual(integrity_errors, [])
            self.assertEqual(metrics["logos_associated"], 2)
            self.assertEqual(metrics["epg_channels"], 1)
            self.assertEqual(metrics["epg_mappings"]["matched"], 1)
            with patch("sys.argv", ["validate_schemas.py", "--candidate-dir", str(output)]):
                from validate_schemas import main as validate_schemas_main
                validate_schemas_main()


class VODCandidateSafetyTests(unittest.TestCase):
    def test_all_four_vod_entrypoints_support_offline_cli_help(self):
        scripts = [
            "enrich_vod_metadata.py",
            "apply_vod_metadata_patch.py",
            "suggest_vod_tmdb_matches.py",
            "apply_vod_tmdb_id_candidates.py",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for script in scripts:
                with self.subTest(script=script):
                    subprocess.run(
                        [sys.executable, str(ROOT / "scripts" / script), "--help"],
                        cwd=tmp, check=True, capture_output=True, text=True,
                    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "catalog/vod/index").mkdir(parents=True)
        (self.root / "catalog/vod/details/movies").mkdir(parents=True)
        self.index_path = self.root / "catalog/vod/index/movies.json"
        self.detail_path = self.root / "catalog/vod/details/movies/A.json"
        self.record = {"id": "movie-a-2020", "title": "A Movie (2020)", "type": "movie",
                       "year": "2020", "tmdb_id": "123", "poster_url": None,
                       "genres": [], "overview": None, "sources": [{"url": "https://stream.example.test/keep.m3u8"}]}
        self.index_path.write_text(json.dumps([{
            "id": self.record["id"], "title": self.record["title"], "year": "2020",
            "tmdb_id": "123", "detail_path": "catalog/vod/details/movies/A.json"
        }]), encoding="utf-8")
        self.detail_path.write_text(json.dumps([self.record]), encoding="utf-8")
        (self.root / "catalog/vod/index.json").write_text(json.dumps({
            "categories": {"movies": {"index_path": "catalog/vod/index/movies.json"}}
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_enrichment_generates_review_patch_without_network_or_catalog_mutation(self):
        before = (self.index_path.read_bytes(), self.detail_path.read_bytes())
        payload = {"id": 123, "title": "A Movie", "original_title": "A Movie",
                   "release_date": "2020-01-01", "poster_path": "/poster.jpg",
                   "genres": [{"name": "Drama"}], "overview": "Synopsis"}
        with patch.object(enrich, "fetch_tmdb_details", return_value=(payload, "ok")):
            report = enrich.build_patch(self.root, self.root / "patch.json", self.root / "cache.sqlite3",
                                        10, "fake-public-key", delay=0)
        self.assertEqual(report["summary"]["ready"], 1)
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual((self.index_path.read_bytes(), self.detail_path.read_bytes()), before)

    def test_metadata_patch_writes_overlay_only(self):
        patch_doc = {"report_type": "review_only_tmdb_metadata_patch", "catalog_mutated": False,
                     "patches": [{"section": "movies", "id": "movie-a-2020", "title": "A Movie (2020)",
                     "matched_title": "A Movie", "tmdb_id": "123",
                     "confidence": "exact_provider_id_and_title",
                     "proposed_fields": {"overview": "Synopsis"}}]}
        patch_path = self.root / "patch.json"
        patch_path.write_text(json.dumps(patch_doc), encoding="utf-8")
        before = (self.index_path.read_bytes(), self.detail_path.read_bytes())
        staging = self.root / "staging"
        summary = apply_metadata.apply_patch(self.root, patch_path, self.root / "summary.json", staging)
        self.assertFalse(summary["catalog_mutated"])
        self.assertTrue(summary["candidate_mutated"])
        self.assertEqual((self.index_path.read_bytes(), self.detail_path.read_bytes()), before)
        overlay = json.loads((staging / "catalog/vod/details/movies/A.json").read_text())[0]
        self.assertEqual(overlay["overview"], "Synopsis")
        self.assertTrue((staging / "candidate-manifest.json").exists())

    def test_suggestion_and_unique_exact_year_assignment_stay_in_candidate_overlay(self):
        before = (self.index_path.read_bytes(), self.detail_path.read_bytes())
        # This record has an existing ID, so create a separate no-ID candidate in the fixture.
        index = json.loads(self.index_path.read_text())
        detail = json.loads(self.detail_path.read_text())
        index[0]["tmdb_id"] = ""
        detail[0]["tmdb_id"] = ""
        self.index_path.write_text(json.dumps(index), encoding="utf-8")
        self.detail_path.write_text(json.dumps(detail), encoding="utf-8")
        result = {"id": 12345, "title": "A Movie", "original_title": "A Movie",
                  "release_date": "2020-01-01", "poster_path": "/poster.jpg", "overview": "x"}
        report_path = self.root / "candidate-report.json"
        with patch.object(suggest, "search_catalog_proxy", return_value=([result], "ok")):
            report = suggest.build_report(self.root, report_path,
                "https://project.example.test/functions/v1/cinehub-catalog", "",
                limit=1, delay=0)
        self.assertFalse(report["catalog_mutated"])
        self.assertEqual(report["summary"]["exact_title_candidates"], 1)
        staging = self.root / "id-staging"
        summary = apply_ids.apply_reports(self.root, [report_path], self.root / "id-summary.json", staging)
        self.assertFalse(summary["catalog_mutated"])
        self.assertEqual(summary["counts"]["ids_assigned"], 1)
        self.assertEqual(json.loads(self.index_path.read_text())[0]["tmdb_id"], "")
        overlay = json.loads((staging / "catalog/vod/index/movies.json").read_text())[0]
        self.assertEqual(overlay["tmdb_id"], "12345")

    def test_ambiguous_tmdb_candidates_are_not_assigned(self):
        index = json.loads(self.index_path.read_text())
        detail = json.loads(self.detail_path.read_text())
        index[0]["tmdb_id"] = ""
        detail[0]["tmdb_id"] = ""
        self.index_path.write_text(json.dumps(index), encoding="utf-8")
        self.detail_path.write_text(json.dumps(detail), encoding="utf-8")
        report_path = self.root / "candidate-report.json"
        report_path.write_text(json.dumps({"report_type": "review_only_tmdb_id_candidates",
            "read_only": True, "catalog_mutated": False, "candidates": [{
            "section": "movies", "catalog_id": "movie-a-2020", "catalog_title": "A Movie (2020)",
            "catalog_year": "2020", "media_type": "movie", "status": "exact_title_review",
            "candidates": [{"tmdb_id_candidate": "12345", "matched_title": "A Movie", "year": "2020"},
                           {"tmdb_id_candidate": "99999", "matched_title": "A Movie", "year": "2020"}]}]}), encoding="utf-8")
        summary = apply_ids.apply_reports(self.root, [report_path], self.root / "summary.json", self.root / "staging")
        self.assertEqual(summary["counts"]["skipped_multiple_candidates"], 1)
        self.assertEqual(json.loads(self.index_path.read_text())[0]["tmdb_id"], "")


if __name__ == "__main__":
    unittest.main()
