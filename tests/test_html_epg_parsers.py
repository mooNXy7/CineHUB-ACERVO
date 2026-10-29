import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from parse_html_epg import parse_guiadetv, parse_meuguia


class HtmlEpgParserTests(unittest.TestCase):
    def test_meuguia_extracts_date_time_title_genre_and_interval(self):
        document = """
        <ul>
          <li class="subheader">25/10</li>
          <li><span class="time">18:30</span><h2>Jornal &amp; Notícias</h2><h3>Jornalismo</h3></li>
          <li><span class="time">19:00</span><h2>Filme de Teste</h2></li>
        </ul>
        """
        result = parse_meuguia(document, dt.date(2026, 10, 25))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Jornal & Notícias")
        self.assertEqual(result[0]["genre"], "Jornalismo")
        self.assertEqual(result[0]["start"], "2026-10-25T18:30:00-03:00")
        self.assertEqual(result[0]["end"], "2026-10-25T19:00:00-03:00")
        self.assertEqual(result[1]["end"], "2026-10-25T20:00:00-03:00")

    def test_meuguia_ignores_invalid_times_and_empty_markup(self):
        document = '<li><span class="time">99:99</span><h2>Inválido</h2></li>'
        self.assertEqual(parse_meuguia(document, dt.date(2026, 10, 25)), [])
        self.assertEqual(parse_meuguia("<html><body>sem programação</body></html>"), [])

    def test_guiadetv_sorts_entries_and_uses_next_start_as_end(self):
        document = """
        <div data-dt="2026-10-25 20:00:00"></div>
        <a href="/programa/filme-b">Filme B</a>
        <div data-dt="2026-10-25 19:00:00"></div>
        <a href="/programa/jornal-a">Jornal A</a>
        """
        result = parse_guiadetv(document)
        self.assertEqual([item["title"] for item in result], ["Jornal A", "Filme B"])
        self.assertEqual(result[0]["end"], "2026-10-25T20:00:00-03:00")
        self.assertEqual(result[1]["end"], "2026-10-25T21:00:00-03:00")

    def test_guiadetv_ignores_invalid_and_unrelated_links(self):
        document = """
        <div data-dt="not-a-date"></div><a href="/programa/a">Sem data</a>
        <div data-dt="2026-02-30 20:00:00"></div><a href="/programa/b">Data inválida</a>
        <div data-dt="2026-10-25 20:00:00"></div><a href="/noticia/c">Notícia</a>
        """
        self.assertEqual(parse_guiadetv(document), [])
        self.assertEqual(parse_guiadetv("<html>sem programação</html>"), [])

    def test_duplicate_start_and_title_are_removed(self):
        document = """
        <div data-dt="2026-10-25 19:00:00"></div><a href="/programa/a">Mesmo Programa</a>
        <div data-dt="2026-10-25 19:00:00"></div><a href="/programa/b">Mesmo Programa</a>
        """
        result = parse_guiadetv(document)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
