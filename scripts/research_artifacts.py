#!/usr/bin/env python3
"""Safe project artifacts for econometric-paper work."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


EVIDENCE_HEADERS = [
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
EVIDENCE_STATES = {
    "VERIFIED",
    "PARTIAL",
    "UNVERIFIED",
    "CONTRADICTED",
    "NOT_APPLICABLE",
}
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|authorization|password|secret|token)",
    re.IGNORECASE,
)
_QUERY_SECRET = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|token|secret|password)=([^&\s]+)"
)
_BEARER_SECRET = re.compile(r"(?i)bearer\s+[^\s,;]+")
_CITATION = re.compile(r"(?<![\w@])@([A-Za-z0-9_:.+\-]+)")
_BIB_ENTRY = re.compile(r"@[A-Za-z]+\s*\{\s*([^,\s]+)", re.IGNORECASE)


def ensure_within(root: Path, candidate: Path) -> Path:
    """Resolve *candidate* and reject paths outside *root*."""
    root_path = Path(root).resolve()
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = root_path / candidate_path
    resolved = candidate_path.resolve()
    try:
        common = Path(os.path.commonpath((str(root_path), str(resolved))))
    except ValueError as exc:
        raise ValueError("path is outside the allowed root") from exc
    if common != root_path:
        raise ValueError("path is outside the allowed root")
    return resolved


def atomic_write(path: Path, payload: bytes, *, overwrite: bool = False) -> Path:
    """Write bytes through a same-directory temporary file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, target)
        else:
            try:
                os.link(temporary, target)
            except FileExistsError:
                raise
            finally:
                temporary.unlink(missing_ok=True)
        return target
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def versioned_path(path: Path) -> Path:
    """Return *path* when free, otherwise the first ``-vN`` variant."""
    target = Path(path)
    if not target.exists():
        return target
    version = 2
    while True:
        candidate = target.with_name(f"{target.stem}-v{version}{target.suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def canonical_json(value: object) -> bytes:
    """Serialize JSON deterministically as UTF-8."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_evidence_state(value: str | None) -> str:
    """Normalize a ledger state, treating absence as unresolved evidence."""
    state = (value or "").strip().upper() or "UNVERIFIED"
    if state not in EVIDENCE_STATES:
        raise ValueError(f"invalid evidence_state: {state}")
    return state


def redact_secrets(value: Any) -> Any:
    """Return a recursively redacted value suitable for logs and receipts."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEY.fullmatch(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, str):
        redacted = _QUERY_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
        return _BEARER_SECRET.sub("Bearer [REDACTED]", redacted)
    return value


def _relative(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def initialize_project(project_root: Path, skill_root: Path) -> dict[str, object]:
    """Create only missing research directories and starter artifacts."""
    project = Path(project_root).resolve()
    skill = Path(skill_root).resolve()
    project.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    reused: list[str] = []

    for relative in (
        Path("research/sources"),
        Path("research/evidence"),
        Path("research/manuscript"),
        Path("research/outputs"),
    ):
        directory = ensure_within(project, project / relative)
        if directory.exists():
            if not directory.is_dir():
                raise NotADirectoryError(directory)
            reused.append(relative.as_posix())
        else:
            directory.mkdir(parents=True)
            created.append(relative.as_posix())

    starters = (
        (
            skill / "assets" / "evidence-ledger.csv",
            project / "research" / "evidence" / "evidence-ledger.csv",
        ),
        (
            skill / "assets" / "manuscript-template.md",
            project / "research" / "manuscript" / "manuscript.md",
        ),
    )
    for source, target_candidate in starters:
        target = ensure_within(project, target_candidate)
        if target.exists():
            reused.append(_relative(project, target))
            continue
        atomic_write(target, source.read_bytes())
        created.append(_relative(project, target))

    return {"project_root": str(project), "created": sorted(created), "reused": sorted(reused)}


def _reference_keys(project: Path) -> set[str]:
    keys: set[str] = set()
    json_path = project / "research" / "references.json"
    if json_path.is_file():
        value = json.loads(json_path.read_text(encoding="utf-8"))
        entries = value if isinstance(value, list) else value.get("items", [])
        for entry in entries:
            if isinstance(entry, dict):
                key = entry.get("id") or entry.get("citation_key")
                if key:
                    keys.add(str(key))
    for bibliography in (project / "research").glob("**/*.bib"):
        keys.update(_BIB_ENTRY.findall(bibliography.read_text(encoding="utf-8")))
    return keys


def validate_project(project_root: Path) -> dict[str, object]:
    """Validate evidence, citations, and retrieved-file provenance."""
    project = Path(project_root).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    ledger = project / "research" / "evidence" / "evidence-ledger.csv"
    if ledger.is_file():
        with ledger.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != EVIDENCE_HEADERS:
                errors.append("evidence ledger headers do not match the required schema")
            else:
                for row_number, row in enumerate(reader, start=2):
                    try:
                        normalize_evidence_state(row.get("evidence_state"))
                    except ValueError:
                        state = (row.get("evidence_state") or "").strip()
                        errors.append(
                            f"row {row_number} has invalid evidence_state: {state}"
                        )
    else:
        warnings.append("evidence ledger not found")

    citation_keys: set[str] = set()
    manuscript_root = project / "research" / "manuscript"
    if manuscript_root.is_dir():
        for manuscript in manuscript_root.glob("**/*.md"):
            citation_keys.update(_CITATION.findall(manuscript.read_text(encoding="utf-8")))
    known_keys = _reference_keys(project)
    missing_citations = sorted(citation_keys - known_keys)
    if missing_citations:
        errors.append("unresolved citation keys: " + ", ".join(missing_citations))

    manifest = project / "research" / "sources" / "retrieval-manifest.jsonl"
    if manifest.is_file():
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                destination = ensure_within(project, project / record["destination"])
                if not destination.is_file():
                    errors.append(f"manifest line {line_number} destination is missing")
                elif sha256_file(destination) != record.get("sha256"):
                    errors.append(f"manifest line {line_number} hash mismatch")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                errors.append(f"manifest line {line_number} is invalid")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "missing_citations": missing_citations,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    initialize = subparsers.add_parser("initialize")
    initialize.add_argument("project_root", type=Path)
    initialize.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    validate = subparsers.add_parser("validate")
    validate.add_argument("project_root", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "initialize":
            result = initialize_project(arguments.project_root, arguments.skill_root)
        else:
            result = validate_project(arguments.project_root)
        print(canonical_json(redact_secrets(result)).decode("utf-8"))
        return 0 if result.get("valid", True) else 1
    except Exception as exc:  # keep command output machine-readable
        print(canonical_json({"ok": False, "error": str(redact_secrets(str(exc)))}).decode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
