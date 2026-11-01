import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_MAP = json.loads((ROOT / "catalog/epg/channel-map.json").read_text(encoding="utf-8"))
ARCHIVED_HTML_MAP = json.loads((ROOT / "catalog/epg/disabled-html-channel-map.json").read_text(encoding="utf-8"))
CHANNEL_DATA = json.loads((ROOT / "catalog/channels/channels.json").read_text(encoding="utf-8"))
CHANNELS = CHANNEL_DATA.get("channels", CHANNEL_DATA)


class AuthorizedReferenceEPGMappingsTests(unittest.TestCase):
    def test_meuguia_mappings_from_authorized_reference_are_present(self):
        expected = {
            "Telecine Cult": "TC5",
            "Telecine Fun": "TC6",
            "Telecine Touch": "TC3",
            "Globo MG": "GRD",
            "Globo RS": "GRD",
            "Globo ES": "GRD",
            "Globo AM": "GRD",
            "RedeTV!": "RTV",
            "Nickelodeon": "NIC",
            "TCM": "TCM",
            "Band News": "NEW",
        }
        names = {channel.get("name") for channel in CHANNELS}
        for name, code in expected.items():
            with self.subTest(channel=name):
                self.assertIn(name, names)
                self.assertEqual(ARCHIVED_HTML_MAP["meuguia_codes"].get(name), code)

    def test_guia_de_tv_mappings_from_authorized_reference_are_present(self):
        expected = {
            "HBO Pop": "hbo-pop",
            "HBO Xtreme": "hbo-xtreme",
            "HBO Mundi": "hbo-mundi",
            "CNN Brasil": "cnn-brasil",
            "Cartoonito": "cartoonito",
            "AMC": "amc",
            "TNT Novelas": "tnt-novelas",
            "History 2": "history-2",
            "Food Network": "food-network",
            "HGTV": "hgtv",
            "Multishow": "multishow",
            "BIS": "bis",
            "Arte 1": "arte-1",
            "Record News": "record-news",
            "Jovem Pan News": "jovem-pan-news",
            "TV Brasil": "tv-brasil",
            "TV Aparecida": "tv-aparecida",
            "Premiere 2": "premiere-2",
            "Premiere 3": "premiere-3",
            "Premiere 4": "premiere-4",
            "Adult Swim": "adult-swim",
        }
        names = {channel.get("name") for channel in CHANNELS}
        for name, slug in expected.items():
            with self.subTest(channel=name):
                self.assertIn(name, names)
                self.assertEqual(ARCHIVED_HTML_MAP["guiadetv_slugs"].get(name), slug)

    def test_active_html_maps_are_empty_until_redistribution_permission(self):
        self.assertEqual(CHANNEL_MAP.get("meuguia_codes"), {})
        self.assertEqual(CHANNEL_MAP.get("guiadetv_slugs"), {})

    def test_shared_globo_code_is_explicitly_documented(self):
        expected = {"Globo RJ", "Globo SP", "Globo MG", "Globo RS", "Globo ES", "Globo AM"}
        entries = [entry for entry in ARCHIVED_HTML_MAP.get("intentional_shared_meuguia_codes", [])
                   if entry.get("code") == "GRD"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(set(entries[0]["channel_names"]), expected)
        self.assertIn("Saimo-Cell-V2:data/epgMappings.ts", entries[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
