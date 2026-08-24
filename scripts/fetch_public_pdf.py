#!/usr/bin/env python3
"""Retrieve one lawful public PDF into a contained research project."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Protocol

from artifact_utils import atomic_write, canonical_json, ensure_within, sha256_file


USER_AGENT = "econ-paper-rigor/0.1"
REDIRECT_CODES = {301, 302, 303, 307, 308}


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    chunks: Iterable[bytes]


@dataclass(frozen=True)
class RetrievalRequest:
    url: str
    project_root: Path
    destination: Path
    identifier: str | None = None
    max_bytes: int = 25 * 1024 * 1024
    max_redirects: int = 3
    min_pdf_bytes: int = 256
    timeout: float = 20.0


class HttpTransport(Protocol):
    def resolve(self, host: str, port: int, type: int = socket.SOCK_STREAM): ...

    def robots_allowed(self, url: str, user_agent: str) -> bool: ...

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class DefaultHttpTransport:
    def __init__(self):
        self._opener = urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def resolve(host: str, port: int, type: int = socket.SOCK_STREAM):
        return socket.getaddrinfo(host, port, type=type)

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        try:
            response = self._opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc

        def chunks():
            with response:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk

        return HttpResponse(int(response.status), dict(response.headers.items()), chunks())

    def robots_allowed(self, url: str, user_agent: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        robots_url = urllib.parse.urlunsplit(("https", parsed.netloc, "/robots.txt", "", ""))
        validate_url(robots_url, resolver=self.resolve)
        try:
            response = self.get(robots_url, {"User-Agent": user_agent}, 10.0)
            if response.status == 404:
                return True
            if response.status != 200:
                return False
            body = b""
            for chunk in response.chunks:
                body += chunk
                if len(body) > 256 * 1024:
                    return False
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(body.decode("utf-8", errors="replace").splitlines())
            return parser.can_fetch(user_agent, url)
        except (OSError, urllib.error.URLError):
            return False


def validate_url(url: str, *, resolver=socket.getaddrinfo) -> tuple[str, ...]:
    """Validate public HTTPS and return the resolved public addresses."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("only HTTPS URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("embedded URL credentials are not allowed")
    if not parsed.hostname:
        raise ValueError("URL hostname is required")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise ValueError("invalid URL port") from exc
    try:
        answers = resolver(parsed.hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("hostname could not be resolved") from exc
    addresses: set[str] = set()
    for answer in answers:
        address = answer[4][0]
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global:
            raise ValueError("URL resolves to a non-public network address")
        addresses.add(str(ip))
    if not addresses:
        raise ValueError("hostname returned no usable address")
    return tuple(sorted(addresses))


def _header(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return str(value)
    return None


def _known_hashes(manifest: Path) -> set[str]:
    hashes: set[str] = set()
    if not manifest.is_file():
        return hashes
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            digest = value["sha256"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"retrieval manifest line {line_number} is invalid") from exc
        hashes.add(str(digest))
    return hashes


def _append_manifest(manifest: Path, record: dict[str, object]) -> None:
    previous = manifest.read_bytes() if manifest.is_file() else b""
    if previous and not previous.endswith(b"\n"):
        previous += b"\n"
    atomic_write(manifest, previous + canonical_json(record) + b"\n", overwrite=True)


def fetch(
    request: RetrievalRequest, *, transport: HttpTransport | None = None
) -> dict[str, object]:
    """Fetch and validate one PDF, then append its provenance manifest."""
    project = Path(request.project_root).resolve()
    destination = ensure_within(project, Path(request.destination))
    if destination.suffix.lower() != ".pdf":
        raise ValueError("destination must use the .pdf extension")
    if destination.exists():
        raise FileExistsError(destination)
    if request.max_bytes <= 0 or request.min_pdf_bytes <= 0:
        raise ValueError("byte limits must be positive")
    destination.parent.mkdir(parents=True, exist_ok=True)
    client = transport or DefaultHttpTransport()
    current = request.url
    redirects = 0

    while True:
        validate_url(current, resolver=client.resolve)
        if not client.robots_allowed(current, USER_AGENT):
            raise PermissionError("robots policy does not allow this path")
        response = client.get(
            current,
            {"User-Agent": USER_AGENT, "Accept": "application/pdf"},
            request.timeout,
        )
        if response.status in REDIRECT_CODES:
            location = _header(response.headers, "Location")
            if not location:
                raise ValueError("redirect is missing a Location header")
            redirects += 1
            if redirects > request.max_redirects:
                raise ValueError("redirect limit exceeded")
            current = urllib.parse.urljoin(current, location)
            continue
        if response.status < 200 or response.status >= 300:
            raise ValueError(f"unexpected HTTP status: {response.status}")
        break

    content_type = (_header(response.headers, "Content-Type") or "").split(";", 1)[0].strip().lower()
    if content_type not in {"application/pdf", "application/x-pdf"}:
        raise ValueError("response Content-Type is not PDF")
    content_length_header = _header(response.headers, "Content-Length")
    if content_length_header is not None:
        try:
            declared_length = int(content_length_header)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if declared_length > request.max_bytes:
            raise OverflowError("PDF exceeds the configured byte limit")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".part", dir=destination.parent
    )
    temporary = Path(temporary_name)
    finalized = False
    try:
        total = 0
        prefix = b""
        with os.fdopen(descriptor, "wb") as handle:
            for chunk in response.chunks:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise ValueError("transport yielded a non-byte body chunk")
                total += len(chunk)
                if total > request.max_bytes:
                    raise OverflowError("PDF exceeds the configured byte limit")
                if len(prefix) < 5:
                    prefix += bytes(chunk[: 5 - len(prefix)])
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if total < request.min_pdf_bytes:
            raise ValueError("PDF is shorter than the configured minimum")
        if not prefix.startswith(b"%PDF-"):
            raise ValueError("file does not have a PDF signature")

        digest = sha256_file(temporary)
        manifest = ensure_within(
            project, project / "research" / "sources" / "retrieval-manifest.jsonl"
        )
        if digest in _known_hashes(manifest):
            raise FileExistsError("an identical PDF is already recorded")
        os.link(temporary, destination)
        finalized = True
        temporary.unlink(missing_ok=True)
        record: dict[str, object] = {
            "source_url": request.url,
            "final_url": current,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "identifier": request.identifier,
            "content_length": total,
            "sha256": digest,
            "destination": destination.relative_to(project).as_posix(),
        }
        _append_manifest(manifest, record)
        return {**record, "destination": str(destination), "manifest": str(manifest)}
    except Exception:
        temporary.unlink(missing_ok=True)
        if finalized:
            destination.unlink(missing_ok=True)
        raise


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--identifier")
    arguments = parser.parse_args()
    try:
        result = fetch(
            RetrievalRequest(
                arguments.url,
                arguments.project_root,
                arguments.destination,
                identifier=arguments.identifier,
            )
        )
        print(canonical_json(result).decode("utf-8"))
        return 0
    except Exception as exc:
        print(canonical_json({"ok": False, "error": str(exc)}).decode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
