import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def word(name):
    return f"{{{WORD_NS}}}{name}"


def math(name):
    return f"{{{MATH_NS}}}{name}"


def element_text(element):
    return "".join(element.itertext())


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

    def test_latex_route_preserves_academic_structure_without_requiring_tex(self):
        """Catches omitting editable .tex output or making compilation mandatory."""
        root = Path(__file__).resolve().parents[1]
        reference = (
            root / "references" / "typesetting-and-formatting.md"
        ).read_text(encoding="utf-8")

        for required in (
            "latex",
            ".tex",
            "\\section",
            "\\textbf",
            "\\emph",
            "inline math",
            "display math",
            "tables",
            "captions",
            "\\label",
            "\\ref",
            "citations",
            "\\footnote",
            "tex distribution",
            "compilation",
            "existing toolchain",
        ):
            with self.subTest(required=required):
                self.assertIn(required, reference.lower())

    def test_reference_doc_demonstrates_editable_academic_features(self):
        """Catches replacing semantic Word structures with visual plain text."""
        root = Path(__file__).resolve().parents[1]
        reference_doc = root / "assets" / "reference.docx"

        with zipfile.ZipFile(reference_doc) as archive:
            parts = set(archive.namelist())
            self.assertIn("word/footnotes.xml", parts)
            document = ET.fromstring(archive.read("word/document.xml"))
            footnotes = ET.fromstring(archive.read("word/footnotes.xml"))
            styles = ET.fromstring(archive.read("word/styles.xml"))

        paragraphs = list(document.iter(word("p")))
        paragraph_texts = [element_text(paragraph) for paragraph in paragraphs]
        math_expressions = list(document.iter(math("oMath")))
        body = document.find(word("body"))
        body_blocks = list(body)
        table = next(block for block in body_blocks if block.tag == word("tbl"))
        table_index = body_blocks.index(table)
        caption = body_blocks[table_index - 1]
        caption_style = caption.find("./w:pPr/w:pStyle", {"w": WORD_NS})
        first_header_cell = table.find("./w:tr/w:tc", {"w": WORD_NS})
        style_names = {
            style.attrib[word("styleId")]: style.find(word("name")).attrib[word("val")]
            for style in styles.iter(word("style"))
            if style.find(word("name")) is not None
        }

        self.assertTrue(list(document.iter(word("b"))))
        self.assertTrue(list(document.iter(word("i"))))
        self.assertTrue(list(document.iter(word("numPr"))))
        self.assertTrue(list(document.iter(word("tbl"))))
        self.assertTrue(list(document.iter(word("hyperlink"))))
        self.assertTrue(list(document.iter(word("bookmarkStart"))))
        self.assertTrue(list(document.iter(math("oMathPara"))))
        self.assertTrue(math_expressions)
        self.assertTrue(list(document.iter(math("f"))))
        self.assertTrue(list(document.iter(math("sSub"))))
        self.assertTrue(list(footnotes.iter(word("footnote"))))
        self.assertIn("References", paragraph_texts)
        self.assertEqual(element_text(caption), "Table 1. Revenue-weighted country risk inputs")
        self.assertIsNotNone(caption_style)
        caption_style_id = caption_style.attrib[word("val")]
        self.assertIn(caption_style_id, style_names)
        self.assertIn("caption", style_names[caption_style_id].lower())
        self.assertEqual(element_text(first_header_cell), "Country")


if __name__ == "__main__":
    unittest.main()
