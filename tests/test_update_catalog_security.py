import sys
import unittest
from pathlib import Path
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_catalog


class CatalogSourceUrlSafetyTests(unittest.TestCase):
    def test_public_https_sources_and_stream_ports(self):
        self.assertTrue(update_catalog.safe_source_url("https://example.org/list.m3u"))
        self.assertTrue(update_catalog.safe_https_url("https://radio.example:8990/stream"))
        self.assertFalse(update_catalog.safe_source_url("https://example.org:8443/list.m3u"))

    def test_rejects_insecure_or_sensitive_source_urls(self):
        for url in (
            "http://example.org/list.m3u",
            "https://127.0.0.1/list.m3u",
            "https://localhost/list.m3u",
            "https://user:pass@example.org/list.m3u",
            "https://example.org/list.m3u?token=secret",
            "https://example.org/list%22%3E%3C/script%3E",
        ):
            with self.subTest(url=url):
                self.assertFalse(update_catalog.safe_source_url(url))

    def test_relative_redirect_is_resolved_and_allowed(self):
        handler = update_catalog.SafeRedirectHandler()
        request = Request("https://example.org/lists/current.m3u")
        redirected = handler.redirect_request(request, None, 302, "Found", {}, "../next.m3u")
        self.assertEqual(redirected.full_url, "https://example.org/next.m3u")

    def test_redirect_to_unsafe_target_is_rejected(self):
        handler = update_catalog.SafeRedirectHandler()
        request = Request("https://example.org/lists/current.m3u")
        for target in (
            "http://example.org/next.m3u",
            "https://127.0.0.1/private",
            "https://example.org:8443/next.m3u",
        ):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    handler.redirect_request(request, None, 302, "Found", {}, target)


if __name__ == "__main__":
    unittest.main()
