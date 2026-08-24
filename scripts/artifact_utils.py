#!/usr/bin/env python3
"""Small shared helpers for safe research-file operations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|authorization|password|secret|token)",
    re.IGNORECASE,
)
_QUERY_SECRET = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|token|secret|password)=([^&\s]+)"
)
_BEARER_SECRET = re.compile(r"(?i)bearer\s+[^\s,;]+")


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
