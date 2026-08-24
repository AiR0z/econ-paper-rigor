import unittest
from pathlib import Path


class TypesettingContractTests(unittest.TestCase):
    def test_writing_and_release_route_to_semantic_typesetting_guidance(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        reference = (
            root / "references" / "typesetting-and-formatting.md"
        ).read_text(encoding="utf-8") if (root / "references" / "typesetting-and-formatting.md").exists() else ""

        self.assertIn("references/typesetting-and-formatting.md", skill)
        self.assertIn("writing", skill)
        self.assertIn("release", skill)
        self.assertIn("**bold**", reference)
        self.assertIn("inline and display mathematics", reference.lower())
        self.assertIn("editable equations", reference.lower())
        self.assertIn("conversion loss", reference.lower())


if __name__ == "__main__":
    unittest.main()
