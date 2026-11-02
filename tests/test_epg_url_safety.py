import sys
import unittest
from pathlib import Path
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_epg
import validate_catalog


class EpgUrlSafetyTests(unittest.TestCase):
    def test_known_public_https_sources_are_accepted(self):
        for url in (
            "https://raw.githubusercontent.com/example/epg.xml",
            "https://iptv-epg.org/files/epg-br.xml",
            "https://meuguia.tv/programacao/canal/HBO",
        ):
            with self.subTest(url=url):
                self.assertTrue(update_epg.safe_https_url(url))
                self.assertTrue(validate_catalog.safe_source_url(url))

    def test_unsafe_source_urls_are_rejected(self):
        for url in (
            "http://example.com/epg.xml",
            "https://127.0.0.1/epg.xml",
            "https://10.0.0.5/epg.xml",
            "https://localhost/epg.xml",
            "https://server.local/epg.xml",
            "https://user:pass@example.com/epg.xml",
            "https://example.com:8443/epg.xml",
            "https://example.com/epg.xml?token=secret",
        ):
            with self.subTest(url=url):
                self.assertFalse(update_epg.safe_https_url(url))
                self.assertFalse(validate_catalog.safe_source_url(url))

    def test_redirect_to_unsafe_target_is_rejected(self):
        handler = update_epg.SafeRedirectHandler()
        request = Request("https://raw.githubusercontent.com/feed.xml")
        for target in ("http://127.0.0.1/private", "https://localhost/", "https://evil.example:8443/"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_redirect_to_public_https_target_is_allowed(self):
        handler = update_epg.SafeRedirectHandler()
        request = Request("https://raw.githubusercontent.com/feed.xml")
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://cdn.example.org/feed.xml"
        )
        self.assertEqual(redirected.full_url, "https://cdn.example.org/feed.xml")


if __name__ == "__main__":
    unittest.main()
