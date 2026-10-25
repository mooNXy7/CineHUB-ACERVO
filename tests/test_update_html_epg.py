import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_html_epg import update_document, write_json_atomic


class UpdateHtmlEpgTests(unittest.TestCase):
    def test_successful_meuguia_schedule_is_published_in_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {"HBO": "HBO"}, "guiadetv_slugs": {},
            }), encoding="utf-8")
            html = '<li class="subheader">domingo, 25/10</li><li><span class="time">18:30</span><h2>Filme A</h2><h3>Filme</h3></li>'
            doc = update_document(root, lambda url: html, dt.datetime(2026, 10, 25, 12, tzinfo=dt.timezone.utc))
            self.assertEqual(doc["programmes"]["HBO"]["source_id"], "meuguia-br")
            self.assertEqual(doc["programmes"]["HBO"]["programmes"][0]["title"], "Filme A")
            self.assertEqual(doc["health"]["HBO"]["status"], "healthy")
            self.assertFalse((root / "catalog/channels/channels.json").exists())

    def test_empty_or_failed_fetch_preserves_last_known_good_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {"HBO": "HBO"}, "guiadetv_slugs": {},
            }), encoding="utf-8")
            old = {
                "schema_version": 1, "timezone": "America/Sao_Paulo",
                "programmes": {"HBO": {"source_id": "meuguia-br", "fetched_at": "2026-10-24T10:00:00Z",
                                       "programmes": [{"start": "2026-10-24T18:00:00-03:00", "end": "2026-10-24T19:00:00-03:00", "title": "Último válido", "genre": None}]}},
                "health": {"HBO": {"consecutive_failures": 2}},
            }
            (epg / "html-programmes.json").write_text(json.dumps(old), encoding="utf-8")
            doc = update_document(root, lambda url: "<html>bloqueado</html>", dt.datetime(2026, 10, 25, tzinfo=dt.timezone.utc))
            self.assertEqual(doc["programmes"]["HBO"]["programmes"][0]["title"], "Último válido")
            self.assertEqual(doc["health"]["HBO"]["status"], "stale")
            self.assertEqual(doc["health"]["HBO"]["consecutive_failures"], 3)

    def test_guiadetv_is_used_when_no_meuguia_schedule_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {}, "guiadetv_slugs": {"SONY Movies": "sony-movies"},
            }), encoding="utf-8")
            html = '<div data-dt="2026-10-25 20:00:00"></div><a href="/programa/filme">Filme Sony</a>'
            doc = update_document(root, lambda url: html, dt.datetime(2026, 10, 25, 12, tzinfo=dt.timezone.utc))
            self.assertEqual(doc["programmes"]["SONY Movies"]["source_id"], "guia-de-tv-br")
            self.assertEqual(doc["programmes"]["SONY Movies"]["programmes"][0]["title"], "Filme Sony")


    def test_existing_guiadetv_schedule_is_refreshed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {}, "guiadetv_slugs": {"SONY Movies": "sony-movies"},
            }), encoding="utf-8")
            old = {
                "schema_version": 1, "timezone": "America/Sao_Paulo",
                "programmes": {"SONY Movies": {"source_id": "guia-de-tv-br", "fetched_at": "2026-10-24T10:00:00Z",
                                               "programmes": [{"start": "2026-10-24T18:00:00-03:00", "end": "2026-10-24T19:00:00-03:00", "title": "Programa antigo", "genre": None}]}},
                "health": {"SONY Movies": {"consecutive_failures": 0}},
            }
            (epg / "html-programmes.json").write_text(json.dumps(old), encoding="utf-8")
            html = '<div data-dt="2026-10-25 20:00:00"></div><a href="/programa/novo">Programa atualizado</a>'
            doc = update_document(root, lambda url: html, dt.datetime(2026, 10, 25, 12, tzinfo=dt.timezone.utc))
            self.assertEqual(doc["programmes"]["SONY Movies"]["programmes"][0]["title"], "Programa atualizado")
            self.assertEqual(doc["health"]["SONY Movies"]["status"], "healthy")

    def test_fallback_does_not_replace_cached_primary_schedule_when_primary_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {"HBO": "HBO"},
                "guiadetv_slugs": {"HBO": "hbo"},
            }), encoding="utf-8")
            old = {
                "schema_version": 1, "timezone": "America/Sao_Paulo",
                "programmes": {"HBO": {
                    "source_id": "meuguia-br",
                    "fetched_at": "2026-10-25T11:00:00Z",
                    "programmes": [{
                        "start": "2026-10-25T10:00:00-03:00",
                        "end": "2026-10-25T11:00:00-03:00",
                        "title": "Grade principal válida", "genre": None,
                    }],
                }},
                "health": {"HBO": {"consecutive_failures": 0}},
            }
            (epg / "html-programmes.json").write_text(json.dumps(old), encoding="utf-8")

            def fetcher(url):
                if "meuguia.tv" in url:
                    raise OSError("simulated primary source failure")
                return '<div data-dt="2026-10-25 12:00:00"></div><a href="/programa/fallback">Grade reserva</a>'

            doc = update_document(
                root, fetcher, dt.datetime(2026, 10, 25, 12, tzinfo=dt.timezone.utc)
            )
            self.assertEqual(
                doc["programmes"]["HBO"]["programmes"][0]["title"],
                "Grade principal válida",
            )
            self.assertEqual(doc["programmes"]["HBO"]["source_id"], "meuguia-br")
            self.assertEqual(doc["health"]["HBO"]["status"], "stale")

    def test_atomic_writer_preserves_previous_file_if_replace_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text('{"old": true}\n', encoding="utf-8")
            import update_html_epg
            original = update_html_epg.os.replace
            try:
                update_html_epg.os.replace = lambda *_: (_ for _ in ()).throw(OSError("simulated failure"))
                with self.assertRaises(OSError):
                    write_json_atomic(path, {"new": True})
            finally:
                update_html_epg.os.replace = original
            self.assertEqual(path.read_text(encoding="utf-8"), '{"old": true}\n')
            self.assertEqual(list(Path(tmp).glob(".result.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
