import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from artifact_utils import (  # noqa: E402
    atomic_write,
    canonical_json,
    ensure_within,
    redact_secrets,
    sha256_file,
)


class ArtifactUtilityTests(unittest.TestCase):
    def test_ensure_within_rejects_parent_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            with self.assertRaises(ValueError):
                ensure_within(root, root / ".." / "outside.txt")

    def test_atomic_write_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.txt"
            target.write_bytes(b"author copy")
            with self.assertRaises(FileExistsError):
                atomic_write(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"author copy")
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_canonical_json_and_hash_are_deterministic(self):
        payload = {"z": 1, "a": "é", "nested": {"b": False, "a": None}}
        self.assertEqual(
            canonical_json(payload),
            '{"a":"é","nested":{"a":null,"b":false},"z":1}'.encode(),
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "value.json"
            target.write_bytes(b"abc")
            self.assertEqual(
                sha256_file(target),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_redact_secrets_removes_sensitive_values_recursively(self):
        value = {
            "api_key": "TEST_API_VALUE",
            "nested": {"authorization": "Bearer TEST_BEARER_VALUE"},
            "message": "request token=TEST_QUERY_VALUE failed",
        }
        rendered = json.dumps(redact_secrets(value), sort_keys=True)
        self.assertNotIn("TEST_API_VALUE", rendered)
        self.assertNotIn("TEST_BEARER_VALUE", rendered)
        self.assertNotIn("TEST_QUERY_VALUE", rendered)
