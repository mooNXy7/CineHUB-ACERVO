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



    def test_alternative_source_is_promoted_only_after_definitive_primary_failure(self):
        from scripts.probe_radio_streams import apply_alternative_probe_results
        radios = [{
            "id": "radio.test", "name": "Radio Test",
            "stream_url": "https://old.example/live", "source_id": "old-source",
            "sources": [{
                "url": "https://new.example/live", "priority": 70,
                "source_id": "verified-mirror", "status": "pending_validation",
            }],
        }]
        primary = [{
            "id": "radio.test", "name": "Radio Test",
            "status": "permanently_unavailable", "detail": "http_404_not_found",
            "http_status": 404, "content_type": None, "host": "old.example",
        }]
        alternatives = [{
            "id": "radio.test", "name": "Radio Test", "source_id": "verified-mirror",
            "priority": 70, "source_index": 0, "url": "https://new.example/live",
            "status": "functional", "detail": "audio_content_type", "http_status": 200,
            "content_type": "audio/mpeg", "host": "new.example",
        }]
        results, promotions, mutated = apply_alternative_probe_results(radios, primary, alternatives)
        self.assertTrue(mutated)
        self.assertEqual(radios[0]["stream_url"], "https://new.example/live")
        self.assertEqual(radios[0]["source_id"], "verified-mirror")
        self.assertEqual(radios[0]["sources"], [{
            "url": "https://old.example/live", "priority": 10,
            "source_id": "old-source", "status": "permanently_unavailable",
        }])
        self.assertEqual(results[0]["status"], "functional")
        self.assertEqual(results[0]["recovered_from"], "permanently_unavailable")
        self.assertEqual(len(promotions), 1)

    def test_temporary_or_unverified_primary_is_never_replaced(self):
        from scripts.probe_radio_streams import apply_alternative_probe_results
        for primary_status in ("temporarily_unavailable", "unverified", "functional"):
            radios = [{
                "id": "radio.test", "name": "Radio Test",
                "stream_url": "https://old.example/live", "source_id": "old-source",
                "sources": [{
                    "url": "https://new.example/live", "priority": 70,
                    "source_id": "verified-mirror", "status": "pending_validation",
                }],
            }]
            primary = [{
                "id": "radio.test", "name": "Radio Test", "status": primary_status,
                "detail": "probe", "http_status": None, "content_type": None, "host": "old.example",
            }]
            alternatives = [{
                "id": "radio.test", "name": "Radio Test", "source_id": "verified-mirror",
                "priority": 70, "source_index": 0, "url": "https://new.example/live",
                "status": "functional", "detail": "audio_content_type", "http_status": 200,
                "content_type": "audio/mpeg", "host": "new.example",
            }]
            results, promotions, mutated = apply_alternative_probe_results(radios, primary, alternatives)
            self.assertEqual(radios[0]["stream_url"], "https://old.example/live")
            self.assertEqual(radios[0]["sources"][0]["status"], "functional")
            self.assertEqual(promotions, [])
            self.assertEqual(results[0]["status"], primary_status)
            self.assertTrue(mutated)


if __name__ == "__main__":
    unittest.main()
