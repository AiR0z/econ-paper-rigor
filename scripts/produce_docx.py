#!/usr/bin/env python3
"""Produce a versioned DOCX and adjacent integrity receipt with Pandoc."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from artifact_utils import (
    atomic_write,
    canonical_json,
    ensure_within,
    redact_secrets,
    sha256_file,
)


REQUIRED_DOCX_MEMBERS = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}


@dataclass(frozen=True)
class ProductionRequest:
    project_root: Path
    source: Path
    output: Path
    bibliography: Path | None = None
    csl: Path | None = None
    reference_doc: Path | None = None
    pandoc: str = "pandoc"


def _contained_file(project: Path, candidate: Path, label: str) -> Path:
    path = ensure_within(project, Path(candidate))
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _external_file(candidate: Path, label: str) -> Path:
    path = Path(candidate).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _validate_docx(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            missing = REQUIRED_DOCX_MEMBERS - names
            if missing:
                raise ValueError("DOCX is missing required OOXML members")
            for member in REQUIRED_DOCX_MEMBERS:
                ET.fromstring(archive.read(member))
    except zipfile.BadZipFile as exc:
        raise ValueError("Pandoc output is not a valid DOCX container") from exc
    except ET.ParseError as exc:
        raise ValueError("DOCX contains malformed required XML") from exc


def _relative_or_name(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return path.name


def _receipt_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".receipt.json")


def _available_output(requested: Path) -> Path:
    candidate = requested
    version = 1
    while candidate.exists() or _receipt_path(candidate).exists():
        version += 1
        candidate = requested.with_name(
            f"{requested.stem}-v{version}{requested.suffix}"
        )
    return candidate


def _pandoc_version(pandoc: str, runner) -> str:
    result = runner(
        [pandoc, "--version"], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Pandoc version check failed")
    first_line = (result.stdout or "").splitlines()
    return first_line[0].strip() if first_line else "pandoc version unavailable"


def produce(
    request: ProductionRequest, *, runner=subprocess.run
) -> dict[str, object]:
    """Convert canonical Markdown to a validated, versioned DOCX."""
    project = Path(request.project_root).resolve()
    source = _contained_file(project, request.source, "source manuscript")
    requested_output = ensure_within(project, Path(request.output))
    if requested_output.suffix.lower() != ".docx":
        raise ValueError("output must use the .docx extension")
    output = _available_output(requested_output)
    output.parent.mkdir(parents=True, exist_ok=True)

    bibliography = (
        _contained_file(project, request.bibliography, "bibliography")
        if request.bibliography is not None
        else None
    )
    csl = _contained_file(project, request.csl, "CSL style") if request.csl is not None else None
    reference_doc = (
        _external_file(request.reference_doc, "reference DOCX")
        if request.reference_doc is not None
        else None
    )

    pandoc_version = _pandoc_version(request.pandoc, runner)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}.", suffix=".tmp.docx", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    command = [
        request.pandoc,
        str(source),
        "--from",
        "markdown",
        "--to",
        "docx",
        "--standalone",
        "--citeproc",
    ]
    if bibliography is not None:
        command.extend(["--bibliography", str(bibliography)])
    if csl is not None:
        command.extend(["--csl", str(csl)])
    if reference_doc is not None:
        command.extend(["--reference-doc", str(reference_doc)])
    command.extend(["--output", str(temporary)])

    finalized = False
    receipt_path = _receipt_path(output)
    try:
        result = runner(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            message = str(redact_secrets(result.stderr or "Pandoc conversion failed"))
            raise RuntimeError(message.strip())
        _validate_docx(temporary)
        digest = sha256_file(temporary)
        os.link(temporary, output)
        finalized = True
        temporary.unlink(missing_ok=True)

        inputs = {"source": sha256_file(source)}
        if bibliography is not None:
            inputs["bibliography"] = sha256_file(bibliography)
        if csl is not None:
            inputs["csl"] = sha256_file(csl)
        if reference_doc is not None:
            inputs["reference_doc"] = sha256_file(reference_doc)
        safe_command = []
        for item in command:
            path = Path(item)
            if path.is_absolute():
                safe_command.append(_relative_or_name(project, path))
            else:
                safe_command.append(item)
        receipt: dict[str, object] = {
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": _relative_or_name(project, source),
            "output": output.relative_to(project).as_posix(),
            "pandoc_version": pandoc_version,
            "command": safe_command,
            "input_sha256": inputs,
            "output_sha256": digest,
        }
        atomic_write(receipt_path, canonical_json(redact_secrets(receipt)) + b"\n")
        return {
            "output": str(output),
            "receipt": str(receipt_path),
            "sha256": digest,
            "pandoc_version": pandoc_version,
        }
    except Exception:
        temporary.unlink(missing_ok=True)
        if finalized:
            output.unlink(missing_ok=True)
        raise


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bibliography", type=Path)
    parser.add_argument("--csl", type=Path)
    parser.add_argument("--reference-doc", type=Path)
    parser.add_argument("--pandoc", default="pandoc")
    arguments = parser.parse_args()
    try:
        result = produce(
            ProductionRequest(
                project_root=arguments.project_root,
                source=arguments.source,
                output=arguments.output,
                bibliography=arguments.bibliography,
                csl=arguments.csl,
                reference_doc=arguments.reference_doc,
                pandoc=arguments.pandoc,
            )
        )
        print(canonical_json(result).decode("utf-8"))
        return 0
    except Exception as exc:
        print(canonical_json({"ok": False, "error": str(redact_secrets(str(exc)))}).decode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
