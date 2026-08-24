import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from research_artifacts import (  # noqa: E402
    atomic_write,
    canonical_json,
    ensure_within,
    initialize_project,
    normalize_evidence_state,
    redact_secrets,
    sha256_file,
    validate_project,
    versioned_path,
)


class PathAndSerializationTests(unittest.TestCase):
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

    def test_versioned_path_selects_first_available_name(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "paper.docx"
            target.write_bytes(b"one")
            (target.parent / "paper-v2.docx").write_bytes(b"two")
            self.assertEqual(versioned_path(target).name, "paper-v3.docx")


class ProjectContractTests(unittest.TestCase):
    def _skill_root(self, base: Path) -> Path:
        skill = base / "skill"
        (skill / "assets").mkdir(parents=True)
        (skill / "assets" / "evidence-ledger.csv").write_text(
            "claim_id,claim_text,claim_class,evidence_locator,evidence_state,"
            "evidence_date,exact_location,limitation,next_action\n",
            encoding="utf-8",
        )
        (skill / "assets" / "manuscript-template.md").write_text(
            "# Template\n", encoding="utf-8"
        )
        return skill

    def test_initialize_project_creates_missing_artifacts_without_clobbering(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            skill = self._skill_root(base)
            project = base / "project"
            manuscript_dir = project / "research" / "manuscript"
            manuscript_dir.mkdir(parents=True)
            manuscript = manuscript_dir / "manuscript.md"
            manuscript.write_text("# Author text\n", encoding="utf-8")

            first = initialize_project(project, skill)
            second = initialize_project(project, skill)

            self.assertEqual(manuscript.read_text(encoding="utf-8"), "# Author text\n")
            self.assertTrue((project / "research" / "sources").is_dir())
            self.assertTrue((project / "research" / "outputs").is_dir())
            self.assertTrue(
                (project / "research" / "evidence" / "evidence-ledger.csv").is_file()
            )
            self.assertIn("research/evidence/evidence-ledger.csv", first["created"])
            self.assertEqual(second["created"], [])
            self.assertIn("research/manuscript/manuscript.md", second["reused"])

    def test_evidence_state_defaults_to_unverified_and_rejects_unknown_state(self):
        self.assertEqual(normalize_evidence_state(""), "UNVERIFIED")
        self.assertEqual(normalize_evidence_state(None), "UNVERIFIED")
        with self.assertRaises(ValueError):
            normalize_evidence_state("CERTAIN")

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            ledger = project / "research" / "evidence" / "evidence-ledger.csv"
            ledger.parent.mkdir(parents=True)
            with ledger.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "claim_id",
                        "claim_text",
                        "claim_class",
                        "evidence_locator",
                        "evidence_state",
                        "evidence_date",
                        "exact_location",
                        "limitation",
                        "next_action",
                    ]
                )
                writer.writerow(["C1", "Claim", "causal", "table 1", "CERTAIN", "", "", "", ""])
            result = validate_project(project)
            self.assertFalse(result["valid"])
            self.assertIn("row 2 has invalid evidence_state: CERTAIN", result["errors"])

    def test_validate_project_reports_unresolved_citation_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manuscript = project / "research" / "manuscript" / "manuscript.md"
            manuscript.parent.mkdir(parents=True)
            manuscript.write_text("Known [@smith2020], missing [@jones2024].\n", encoding="utf-8")
            (project / "research" / "references.json").write_text(
                json.dumps([{"id": "smith2020"}]), encoding="utf-8"
            )
            result = validate_project(project)
            self.assertFalse(result["valid"])
            self.assertEqual(result["missing_citations"], ["jones2024"])

    def test_redact_secrets_removes_sensitive_values_recursively(self):
        value = {
            "api_key": "TEST_API_VALUE",
            "nested": {"authorization": "Bearer TEST_BEARER_VALUE"},
            "message": "request token=TEST_QUERY_VALUE failed",
        }
        redacted = redact_secrets(value)
        rendered = json.dumps(redacted, sort_keys=True)
        self.assertNotIn("TEST_API_VALUE", rendered)
        self.assertNotIn("TEST_BEARER_VALUE", rendered)
        self.assertNotIn("TEST_QUERY_VALUE", rendered)
        self.assertEqual(redacted["api_key"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
