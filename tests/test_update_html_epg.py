import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from update_html_epg import update_document, write_json_atomic
from parse_html_epg import parse_guiadetv


class UpdateHtmlEpgTests(unittest.TestCase):
    def test_disabled_html_sources_remove_cached_schedules_without_fetching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
            (epg / "sources.json").write_text(json.dumps({
                "sources": [
                    {"id": "meuguia-br", "format": "html", "enabled": False},
                    {"id": "guia-de-tv-br", "format": "html", "enabled": False},
                    {"id": "xmltv-a", "format": "xmltv", "enabled": True},
                ]
            }), encoding="utf-8")
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {"HBO": "HBO"},
                "guiadetv_slugs": {"SONY Movies": "sony-movies"},
            }), encoding="utf-8")
            (epg / "html-programmes.json").write_text(json.dumps({
                "schema_version": 1, "timezone": "America/Sao_Paulo",
                "programmes": {
                    "HBO": {"source_id": "meuguia-br", "programmes": [{"title": "Grade antiga"}]},
                    "SONY Movies": {"source_id": "guia-de-tv-br", "programmes": [{"title": "Grade antiga"}]},
                },
                "health": {},
            }), encoding="utf-8")

            def forbidden_fetch(url):
                raise AssertionError("disabled HTML source must never be fetched")

            doc = update_document(root, forbidden_fetch, dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc))
            self.assertEqual(doc["programmes"], {})
            self.assertEqual(doc["active_sources"], [])
            self.assertEqual(doc["health"]["HBO"]["status"], "disabled")
            self.assertEqual(doc["health"]["SONY Movies"]["status"], "disabled")
            self.assertEqual(
                set(doc["policy"]["disabled_sources"]),
                {"meuguia-br", "guia-de-tv-br"},
            )

    def test_successful_meuguia_schedule_is_published_in_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
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
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
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
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
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
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
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
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
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

    def test_html_fetch_url_policy_rejects_non_https_private_and_unknown_hosts(self):
        import update_html_epg
        for url in (
            "http://meuguia.tv/programacao/canal/HBO",
            "https://127.0.0.1/admin",
            "https://localhost/",
            "https://example.com/",
            "https://user:pass@meuguia.tv/",
            "https://meuguia.tv:8443/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    update_html_epg._validate_epg_url(url)

    def test_html_fetch_redirect_policy_rejects_unapproved_target(self):
        import update_html_epg
        from types import SimpleNamespace
        handler = update_html_epg._SameSourceRedirectHandler()
        request = SimpleNamespace(full_url="https://meuguia.tv/programacao/canal/HBO")
        with self.assertRaises(ValueError):
            handler.redirect_request(
                request, None, 302, "Found", {}, "http://127.0.0.1/private"
            )
        with self.assertRaises(ValueError):
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://example.com/redirect"
            )

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


    def test_fetch_html_validates_initial_url_and_uses_redirect_allowlist(self):
        import update_html_epg
        from unittest.mock import MagicMock, patch

        response = MagicMock()
        response.status = 200
        response.headers.get.return_value = "text/html; charset=utf-8"
        response.read.side_effect = [b"<html>ok</html>", b""]
        response.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = response

        with patch("update_html_epg.urllib.request.build_opener", return_value=opener) as build:
            result = update_html_epg.fetch_html("https://meuguia.tv/programacao/canal/HBO")

        self.assertEqual(result, "<html>ok</html>")
        build.assert_called_once()
        self.assertIsInstance(build.call_args.args[0], update_html_epg._SameSourceRedirectHandler)
        opener.open.assert_called_once()

    def test_fetch_html_rejects_unapproved_initial_url_before_network(self):
        import update_html_epg
        from unittest.mock import patch

        with patch("update_html_epg.urllib.request.build_opener") as build:
            with self.assertRaises(ValueError):
                update_html_epg.fetch_html("https://example.com/epg")
        build.assert_not_called()


    def test_guiadetv_parses_visible_times_and_portuguese_date_headers(self):
        html = """
        <h2>Domingo, 25 de outubro</h2>
        <div><span>17:40</span><span>1h35</span><a href="/programa/ameaca">Ameaça Pré-Histórica</a></div>
        <div><span>19:15</span><span>1h40</span><a href="/programa/depois-da-terra">Depois da Terra</a></div>
        <h2>Segunda-feira, 26 de outubro</h2>
        <div><span>00:55</span><span>1h20</span><a href="/programa/hanna">Hanna</a></div>
        """
        items = parse_guiadetv(html, dt.date(2026, 10, 25))
        self.assertEqual([item["title"] for item in items], [
            "Ameaça Pré-Histórica", "Depois da Terra", "Hanna",
        ])
        self.assertEqual(items[0]["start"], "2026-10-25T17:40:00-03:00")
        self.assertEqual(items[1]["start"], "2026-10-25T19:15:00-03:00")
        self.assertEqual(items[2]["start"], "2026-10-26T00:55:00-03:00")

    def test_guiadetv_visible_time_fallback_handles_midnight_rollover(self):
        html = """
        <div><span>23:50</span><a href="/programa/noite">Programa da noite</a></div>
        <div><span>00:20</span><a href="/programa/madrugada">Programa da madrugada</a></div>
        """
        items = parse_guiadetv(html, dt.date(2026, 10, 31))
        self.assertEqual(items[0]["start"], "2026-10-31T23:50:00-03:00")
        self.assertEqual(items[1]["start"], "2026-11-01T00:20:00-03:00")



    def test_guiadetv_visible_schedule_is_published_with_reference_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epg = root / "catalog/epg"
            epg.mkdir(parents=True)
            (epg / "sources.json").write_text(json.dumps({"sources": [
                {"id": "meuguia-br", "format": "html", "enabled": True},
                {"id": "guia-de-tv-br", "format": "html", "enabled": True},
            ]}), encoding="utf-8")
            (epg / "channel-map.json").write_text(json.dumps({
                "meuguia_codes": {}, "guiadetv_slugs": {"SONY Movies": "sony-movies"},
            }), encoding="utf-8")
            html = """
            <h2>Domingo, 25 de outubro</h2>
            <div><span>17:40</span><span>1h35</span><a href="/programa/ameaca">Ameaça Pré-Histórica</a></div>
            <div><span>19:15</span><span>1h40</span><a href="/programa/depois">Depois da Terra</a></div>
            """
            doc = update_document(
                root, lambda url: html, dt.datetime(2026, 10, 25, 12, tzinfo=dt.timezone.utc)
            )
            items = doc["programmes"]["SONY Movies"]["programmes"]
            self.assertEqual(doc["health"]["SONY Movies"]["status"], "healthy")
            self.assertEqual(items[0]["start"], "2026-10-25T17:40:00-03:00")
            self.assertEqual(items[1]["title"], "Depois da Terra")



    def test_main_logs_unavailable_source_classification(self):
        import update_html_epg

        document = {
            "programmes": {"HBO": {"programmes": [{"title": "Programa válido"}]}},
            "health": {
                "HBO": {"status": "healthy", "source_id": "meuguia-br", "error": None},
                "Nickelodeon": {
                    "status": "unavailable",
                    "source_id": "meuguia-br",
                    "error": "ValueError: no programme entries parsed",
                },
                "Adult Swim": {
                    "status": "unavailable",
                    "source_id": "guia-de-tv-br",
                    "error": "HTTPError: HTTP Error 404: Not Found",
                },
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "html-programmes.json"
            stdout = io.StringIO()
            with patch.object(update_html_epg, "OUTPUT_FILE", output_path), patch.object(
                update_html_epg, "update_document", return_value=document
            ), redirect_stdout(stdout):
                self.assertEqual(update_html_epg.main(), 0)

        log = stdout.getvalue()
        self.assertIn("Nickelodeon", log)
        self.assertIn("ValueError: no programme entries parsed", log)
        self.assertIn("Adult Swim", log)
        self.assertIn("HTTP Error 404", log)


if __name__ == "__main__":
    unittest.main()
