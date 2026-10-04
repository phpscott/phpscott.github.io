import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_manifest import ManifestError, load_manifest, validate  # noqa: E402


MANIFEST = ROOT / "dist" / "manifest.json"


class ManifestContractTests(unittest.TestCase):
    def setUp(self):
        self.document = load_manifest(MANIFEST)

    def test_production_manifest_is_valid(self):
        validated = validate(self.document)
        self.assertEqual(validated["manifestVersion"], 1)
        self.assertEqual(validated["environment"], "production")
        self.assertEqual(validated["catalog"]["schemaVersion"], 1)
        self.assertEqual(validated["catalog"]["release"], "r000001")
        self.assertTrue(validated["catalog"]["downloadUrl"].startswith("https://"))
        self.assertIsNone(validated["catalog"]["compatibility"]["maximumApplicationVersion"])

    def test_unknown_fields_are_tolerated(self):
        document = copy.deepcopy(self.document)
        document["futureOptional"] = {"enabled": True}
        document["catalog"]["notes"] = "ignored by version 1 readers"
        validate(document)

    def test_http_url_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["links"]["privacy"] = "http://trust.scottstcgbinder.com/privacy/"
        with self.assertRaises(ManifestError):
            validate(document)

    def test_bad_sha256_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["catalog"]["sha256"] = "abc"
        with self.assertRaises(ManifestError):
            validate(document)

    def test_non_positive_size_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["catalog"]["sizeBytes"] = 0
        with self.assertRaises(ManifestError):
            validate(document)

    def test_invalid_semver_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["catalog"]["compatibility"]["minimumApplicationVersion"] = "1.0"
        with self.assertRaises(ManifestError):
            validate(document)

    def test_invalid_release_id_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["catalog"]["release"] = "release-1"
        with self.assertRaises(ManifestError):
            validate(document)

    def test_invalid_timestamp_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["generatedAt"] = "October 4, 2026"
        with self.assertRaises(ManifestError):
            validate(document)

    def test_empty_download_url_is_rejected(self):
        document = copy.deepcopy(self.document)
        document["catalog"]["downloadUrl"] = ""
        with self.assertRaises(ManifestError):
            validate(document)

    def test_json_round_trip_has_no_trailing_comma(self):
        text = MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn(",\n}", text)
        self.assertNotIn(",\n]", text)
        json.loads(text)


if __name__ == "__main__":
    unittest.main()
