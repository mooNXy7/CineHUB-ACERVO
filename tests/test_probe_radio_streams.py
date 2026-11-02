import unittest
from scripts.probe_radio_streams import classify_http_error, classify_payload


class ProbeRadioStreamsTests(unittest.TestCase):
    def test_audio_mime_requires_nonempty_payload(self):
        self.assertEqual(classify_payload("audio/mpeg", b""), ("unverified", "empty_response"))
        self.assertEqual(classify_payload("audio/mpeg", b"\x00\x01audio"), ("functional", "audio_content_type"))

    def test_hls_playlist_requires_stream_markers(self):
        self.assertEqual(
            classify_payload("application/vnd.apple.mpegurl", b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n"),
            ("functional", "hls_playlist"),
        )
        self.assertEqual(
            classify_payload("application/vnd.apple.mpegurl", b"#EXTM3U\n# comment only\n"),
            ("unverified", "incomplete_hls_playlist"),
        )

    def test_known_audio_signatures_are_recognized(self):
        self.assertEqual(classify_payload("application/octet-stream", b"ID3\x04\x00\x00"), ("functional", "audio_signature"))
        self.assertEqual(classify_payload("application/octet-stream", b"OggS\x00\x02"), ("functional", "audio_signature"))

    def test_html_is_not_audio_even_when_http_is_successful(self):
        self.assertEqual(classify_payload("text/html", b"<!doctype html><html>"), ("non_audio", "html_response"))

    def test_unknown_payload_is_unverified(self):
        self.assertEqual(
            classify_payload("application/json", b'{"ok":true}'),
            ("unverified", "unsupported_content_type_or_signature"),
        )

    def test_transient_and_permanent_http_errors_are_separated(self):
        self.assertEqual(classify_http_error(503), ("temporarily_unavailable", "http_503_transient"))
        self.assertEqual(classify_http_error(404), ("permanently_unavailable", "http_404_not_found"))
        self.assertEqual(classify_http_error(401), ("unverified", "http_401"))


if __name__ == "__main__":
    unittest.main()
