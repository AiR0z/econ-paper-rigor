import json
import socket
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_public_pdf import (  # noqa: E402
    HttpResponse,
    RetrievalRequest,
    fetch,
    validate_url,
)
from produce_docx import ProductionRequest, produce  # noqa: E402


PUBLIC_IP = "93.184.216.34"


def resolver_for(addresses):
    def resolve(host, port, type=socket.SOCK_STREAM):
        address = addresses.get(host, PUBLIC_IP)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    return resolve


def valid_pdf(size=400):
    return b"%PDF-1.7\n" + (b"x" * (size - 9))


class FakeTransport:
    def __init__(self, responses, *, addresses=None, robots_allowed=True):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.resolve = resolver_for(addresses or {})
        self._robots_allowed = robots_allowed

    def robots_allowed(self, url, user_agent):
        return self._robots_allowed

    def get(self, url, headers, timeout):
        return self.responses[url].pop(0)


class PdfRetrievalTests(unittest.TestCase):
    def test_validate_url_accepts_public_https_and_rejects_unsafe_targets(self):
        self.assertEqual(
            validate_url("https://papers.example/article.pdf", resolver=resolver_for({})),
            (PUBLIC_IP,),
        )
        cases = [
            ("http://papers.example/article.pdf", {}),
            ("https://user:pass@papers.example/article.pdf", {}),
            ("https://private.example/article.pdf", {"private.example": "10.0.0.7"}),
            ("https://loop.example/article.pdf", {"loop.example": "127.0.0.1"}),
            ("https://link.example/article.pdf", {"link.example": "169.254.10.20"}),
        ]
        for url, addresses in cases:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url, resolver=resolver_for(addresses))

    def test_fetch_revalidates_redirect_and_obeys_robots(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = "https://papers.example/start"
            redirect = "https://private.example/paper.pdf"
            transport = FakeTransport(
                {
                    source: [HttpResponse(302, {"Location": redirect}, ())],
                },
                addresses={"private.example": "10.0.0.7"},
            )
            request = RetrievalRequest(source, project, Path("research/sources/paper.pdf"))
            with self.assertRaises(ValueError):
                fetch(request, transport=transport)

            blocked = FakeTransport({}, robots_allowed=False)
            with self.assertRaises(PermissionError):
                fetch(request, transport=blocked)

    def test_fetch_rejects_invalid_bodies_and_cleans_temporary_files(self):
        body_cases = [
            HttpResponse(200, {"Content-Type": "text/html"}, (valid_pdf(),)),
            HttpResponse(200, {"Content-Type": "application/pdf"}, (b"not a pdf" * 50,)),
            HttpResponse(200, {"Content-Type": "application/pdf"}, (b"%PDF-short",)),
            HttpResponse(200, {"Content-Type": "application/pdf", "Content-Length": "1000"}, (valid_pdf(),)),
        ]
        for response in body_cases:
            with self.subTest(headers=response.headers):
                with tempfile.TemporaryDirectory() as directory:
                    project = Path(directory)
                    source = "https://papers.example/paper.pdf"
                    transport = FakeTransport({source: [response]})
                    request = RetrievalRequest(
                        source,
                        project,
                        Path("research/sources/paper.pdf"),
                        max_bytes=500,
                    )
                    with self.assertRaises((ValueError, OverflowError)):
                        fetch(request, transport=transport)
                    self.assertFalse((project / "research/sources/paper.pdf").exists())
                    self.assertEqual(list(project.rglob("*.part")), [])

    def test_fetch_rejects_path_escape_and_duplicate_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            source = "https://papers.example/paper.pdf"
            with self.assertRaises(ValueError):
                fetch(
                    RetrievalRequest(source, project, project / ".." / "paper.pdf"),
                    transport=FakeTransport({}),
                )

            first_transport = FakeTransport(
                {source: [HttpResponse(200, {"Content-Type": "application/pdf"}, (valid_pdf(),))]}
            )
            first = fetch(
                RetrievalRequest(source, project, Path("research/sources/one.pdf")),
                transport=first_transport,
            )
            second_transport = FakeTransport(
                {source: [HttpResponse(200, {"Content-Type": "application/pdf"}, (valid_pdf(),))]}
            )
            with self.assertRaises(FileExistsError):
                fetch(
                    RetrievalRequest(source, project, Path("research/sources/two.pdf")),
                    transport=second_transport,
                )
            self.assertTrue(Path(first["destination"]).is_file())
            self.assertFalse((project / "research/sources/two.pdf").exists())
            self.assertEqual(list(project.rglob("*.part")), [])

    def test_fetch_writes_complete_manifest_record(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = "https://papers.example/paper.pdf"
            response = HttpResponse(
                200,
                {"Content-Type": "application/pdf", "Content-Length": "400"},
                (valid_pdf(),),
            )
            result = fetch(
                RetrievalRequest(
                    source,
                    project,
                    Path("research/sources/paper.pdf"),
                    identifier="10.1000/example",
                ),
                transport=FakeTransport({source: [response]}),
            )
            manifest = project / "research/sources/retrieval-manifest.jsonl"
            record = json.loads(manifest.read_text(encoding="utf-8").strip())
            self.assertEqual(record["source_url"], source)
            self.assertEqual(record["final_url"], source)
            self.assertEqual(record["identifier"], "10.1000/example")
            self.assertEqual(record["content_length"], 400)
            self.assertEqual(record["destination"], "research/sources/paper.pdf")
            self.assertEqual(record["sha256"], result["sha256"])
            self.assertRegex(record["retrieved_at"], r"^\d{4}-\d{2}-\d{2}T")


class FakePandocRunner:
    def __init__(self, *, fail=False, invalid=False):
        self.fail = fail
        self.invalid = invalid
        self.commands = []

    def __call__(self, arguments, **kwargs):
        self.commands.append(list(arguments))
        if "--version" in arguments:
            return SimpleNamespace(returncode=0, stdout="pandoc 3.6.1\n", stderr="")
        if self.fail:
            return SimpleNamespace(returncode=2, stdout="", stderr="conversion failed")
        output = Path(arguments[arguments.index("--output") + 1])
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            if not self.invalid:
                archive.writestr("_rels/.rels", "<Relationships/>")
                archive.writestr("word/document.xml", "<w:document xmlns:w='urn:test'/>")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class DocxProductionTests(unittest.TestCase):
    def _request(self, project: Path, **changes):
        source = project / "research/manuscript/paper.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# Paper\n\nText [@item].\n", encoding="utf-8")
        values = {
            "project_root": project,
            "source": source,
            "output": project / "research/outputs/paper.docx",
            "bibliography": project / "research/references.bib",
            "csl": project / "research/style.csl",
            "reference_doc": project / "research/reference.docx",
            "pandoc": "pandoc",
        }
        values.update(changes)
        Path(values["bibliography"]).write_text("@article{item, title={Test}}\n", encoding="utf-8")
        Path(values["csl"]).write_text("<style/>\n", encoding="utf-8")
        Path(values["reference_doc"]).parent.mkdir(parents=True, exist_ok=True)
        if not Path(values["reference_doc"]).exists():
            Path(values["reference_doc"]).write_bytes(b"reference")
        return ProductionRequest(**values)

    def test_produce_uses_argument_list_options_versions_output_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / "research/outputs/paper.docx"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"author output")
            runner = FakePandocRunner()
            result = produce(self._request(project), runner=runner)

            output = Path(result["output"])
            self.assertEqual(output.name, "paper-v2.docx")
            self.assertEqual(existing.read_bytes(), b"author output")
            command = runner.commands[1]
            self.assertEqual(command[0], "pandoc")
            self.assertIn("--citeproc", command)
            self.assertIn("--bibliography", command)
            self.assertIn("--csl", command)
            self.assertIn("--reference-doc", command)
            self.assertNotIn("shell=True", command)
            receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["pandoc_version"], "pandoc 3.6.1")
            self.assertEqual(receipt["output_sha256"], result["sha256"])
            self.assertEqual(receipt["output"], "research/outputs/paper-v2.docx")

    def test_produce_rejects_path_escape_and_preserves_files_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            request = self._request(project, output=project / ".." / "outside.docx")
            with self.assertRaises(ValueError):
                produce(request, runner=FakePandocRunner())

            failed = self._request(project)
            with self.assertRaises(RuntimeError):
                produce(failed, runner=FakePandocRunner(fail=True))
            self.assertFalse(Path(failed.output).exists())
            self.assertEqual(list(project.rglob("*.tmp.docx")), [])

    def test_produce_rejects_structurally_invalid_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            request = self._request(project)
            with self.assertRaises(ValueError):
                produce(request, runner=FakePandocRunner(invalid=True))
            self.assertFalse(Path(request.output).exists())
            self.assertEqual(list(project.rglob("*.tmp.docx")), [])


if __name__ == "__main__":
    unittest.main()
