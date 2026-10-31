import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog/vod/providers/megaembed.json"


class MegaEmbedProviderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registry_declares_embed_fallback_not_direct_media(self):
        self.assertEqual(self.data["schema_version"], 1)
        self.assertEqual(self.data["id"], "megaembed")
        self.assertEqual(self.data["kind"], "iframe_embed")
        self.assertEqual(self.data["role"], "fallback")
        self.assertFalse(self.data["direct_media"])
        self.assertTrue(self.data["external_player_required"])

    def test_all_templates_use_only_allowlisted_https_hosts(self):
        allowed = set(self.data["allowed_hosts"])
        for section in ("movies", "series"):
            self.assertTrue(self.data[section])
            for route in self.data[section]:
                parsed = urlsplit(route["url_template"])
                self.assertEqual(parsed.scheme, "https")
                self.assertIn(parsed.hostname, allowed)
                self.assertGreater(route["priority"], 0)
                placeholders = set(re.findall(r"\\{([a-z_]+)\\}", route["url_template"]))
                self.assertTrue(set(route["requires"]).issubset(placeholders | {"title"}))

    def test_identity_policy_prevents_title_similarity_id_assignment(self):
        policy = self.data["identity_policy"]
        self.assertTrue(policy["title_lookup_is_last_resort"])
        self.assertTrue(policy["never_assign_tmdb_id_from_title_similarity"])
        self.assertTrue(policy["require_exact_media_type"])

    def test_series_routes_require_episode_coordinates(self):
        for route in self.data["series"]:
            self.assertIn("season", route["requires"])
            self.assertIn("episode", route["requires"])


if __name__ == "__main__":
    unittest.main()
