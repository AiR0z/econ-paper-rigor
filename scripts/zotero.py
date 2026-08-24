#!/usr/bin/env python3
"""Narrow Zotero reads and confirmed creation of one bibliographic item."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from research_artifacts import canonical_json, redact_secrets


API_VERSION = "3"
LOCAL_BASE = "http://127.0.0.1:23119/api"
WEB_BASE = "https://api.zotero.org"
USER_AGENT = "econ-paper-rigor/0.1"
_UNSET = object()
_TEXT_FIELDS = (
    "abstractNote",
    "publicationTitle",
    "volume",
    "issue",
    "pages",
    "date",
    "series",
    "seriesTitle",
    "seriesText",
    "journalAbbreviation",
    "language",
    "ISSN",
    "shortTitle",
    "url",
    "accessDate",
    "archive",
    "archiveLocation",
    "libraryCatalog",
    "callNumber",
    "rights",
    "extra",
)
_NON_BIBLIOGRAPHIC_TYPES = {"attachment", "note", "annotation"}


@dataclass(frozen=True)
class ApiResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class ApiTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout: float = 10.0,
    ) -> ApiResponse: ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout: float = 10.0,
    ) -> ApiResponse:
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return ApiResponse(
                    int(response.status), dict(response.headers.items()), response.read()
                )
        except urllib.error.HTTPError as exc:
            with exc:
                return ApiResponse(int(exc.code), dict(exc.headers.items()), exc.read())


def _header(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return str(value)
    return None


def _library_version(response: ApiResponse) -> int:
    raw = _header(response.headers, "Last-Modified-Version")
    if raw is None:
        raise RuntimeError("Zotero response omitted Last-Modified-Version")
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError("Zotero returned an invalid library version") from exc


def _compact_space(value: object) -> str:
    return " ".join(str(value or "").split())


def _normalize_doi(value: object) -> str:
    doi = _compact_space(value).lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.rstrip(". ")


def _title_key(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", _compact_space(value)).casefold()
    return " ".join(re.findall(r"[\w]+", normalized, flags=re.UNICODE))


def _normalize_creator(creator: object) -> dict[str, str]:
    if not isinstance(creator, dict):
        raise ValueError("each creator must be an object")
    creator_type = _compact_space(creator.get("creatorType")) or "author"
    if creator.get("name"):
        name = _compact_space(creator["name"])
        if not name:
            raise ValueError("creator name cannot be empty")
        return {"creatorType": creator_type, "name": name}
    first = _compact_space(creator.get("firstName"))
    last = _compact_space(creator.get("lastName"))
    if not first and not last:
        raise ValueError("creator must include a name")
    return {"creatorType": creator_type, "firstName": first, "lastName": last}


def _normalize_metadata(metadata: dict[str, object]) -> dict[str, object]:
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    item_type = _compact_space(metadata.get("itemType")) or "journalArticle"
    if item_type in _NON_BIBLIOGRAPHIC_TYPES:
        raise ValueError("only bibliographic item types are allowed")
    title = _compact_space(metadata.get("title"))
    if not title:
        raise ValueError("title is required")
    item: dict[str, object] = {"itemType": item_type, "title": title}
    creators = metadata.get("creators", [])
    if not isinstance(creators, list):
        raise ValueError("creators must be a list")
    item["creators"] = [_normalize_creator(creator) for creator in creators]
    doi = _normalize_doi(metadata.get("DOI"))
    if doi:
        item["DOI"] = doi
    for field in _TEXT_FIELDS:
        value = _compact_space(metadata.get(field))
        if value:
            item[field] = value
    tags = metadata.get("tags", [])
    if tags:
        if not isinstance(tags, list):
            raise ValueError("tags must be a list")
        normalized_tags = []
        for tag in tags:
            value = _compact_space(tag.get("tag") if isinstance(tag, dict) else tag)
            if value:
                normalized_tags.append({"tag": value})
        item["tags"] = normalized_tags
    collections = metadata.get("collections", [])
    if collections:
        if not isinstance(collections, list):
            raise ValueError("collections must be a list")
        item["collections"] = [_compact_space(value) for value in collections if _compact_space(value)]
    return item


def _normalize_result(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Zotero item result must be an object")
    data = value.get("data", value)
    if not isinstance(data, dict):
        raise ValueError("Zotero item data must be an object")
    creators = []
    for creator in data.get("creators", []):
        if not isinstance(creator, dict):
            continue
        if creator.get("name"):
            name = _compact_space(creator.get("name"))
        else:
            name = _compact_space(
                f"{creator.get('firstName', '')} {creator.get('lastName', '')}"
            )
        if name:
            creators.append(name)
    return {
        "key": _compact_space(value.get("key") or data.get("key")),
        "version": value.get("version", data.get("version")),
        "item_type": _compact_space(data.get("itemType")),
        "title": _compact_space(data.get("title")),
        "creators": creators,
        "date": _compact_space(data.get("date")),
        "publication_title": _compact_space(data.get("publicationTitle")),
        "doi": _normalize_doi(data.get("DOI")),
        "url": _compact_space(data.get("url")),
    }


class ZoteroClient:
    def __init__(
        self,
        *,
        library_id: str | None | object = _UNSET,
        api_key: str | None | object = _UNSET,
        library_type: str | object = _UNSET,
        transport: ApiTransport | None = None,
        timeout: float = 10.0,
    ):
        if library_id is _UNSET:
            library_id = os.environ.get("ZOTERO_LIBRARY_ID")
        if api_key is _UNSET:
            api_key = os.environ.get("ZOTERO_API_KEY")
        if library_type is _UNSET:
            library_type = os.environ.get("ZOTERO_LIBRARY_TYPE", "users")
        self.library_id = _compact_space(library_id) or None
        self.api_key = str(api_key) if api_key else None
        self.library_type = str(library_type)
        if self.library_type not in {"users", "groups"}:
            raise ValueError("library_type must be users or groups")
        self.transport = transport or UrllibTransport()
        self.timeout = timeout

    def _headers(self, *, web: bool, write: bool = False) -> dict[str, str]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Zotero-API-Version": API_VERSION,
        }
        if web:
            if not self.api_key:
                raise PermissionError("Zotero Web API key is not configured")
            headers["Zotero-API-Key"] = self.api_key
        if write:
            headers["Content-Type"] = "application/json"
        return headers

    def _clean_error(self, error: Exception) -> str:
        message = str(redact_secrets(str(error)))
        if self.api_key:
            message = message.replace(self.api_key, "[REDACTED]")
        return message

    def _base(self, mode: str) -> str:
        if mode == "local":
            return f"{LOCAL_BASE}/users/0"
        if not self.library_id:
            raise RuntimeError("Zotero library ID is not configured")
        return f"{WEB_BASE}/{self.library_type}/{urllib.parse.quote(self.library_id, safe='')}"

    def _items(
        self, mode: str, *, query: str | None, limit: int
    ) -> tuple[list[dict[str, object]], int]:
        parameters: list[tuple[str, str]] = []
        if query is not None:
            parameters.extend((('q', query), ('qmode', 'everything'), ('itemType', '-attachment')))
        parameters.extend((('limit', str(limit)), ('format', 'json')))
        url = f"{self._base(mode)}/items?{urllib.parse.urlencode(parameters)}"
        response = self.transport.request(
            "GET",
            url,
            self._headers(web=mode == "web"),
            timeout=self.timeout,
        )
        if response.status != 200:
            raise RuntimeError(f"Zotero {mode} read returned HTTP {response.status}")
        try:
            body = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Zotero returned invalid JSON") from exc
        if not isinstance(body, list):
            raise RuntimeError("Zotero item response is not a list")
        return [_normalize_result(item) for item in body], _library_version(response)

    def status(self) -> dict[str, object]:
        errors: dict[str, str] = {}
        try:
            items, version = self._items("local", query=None, limit=1)
            return {
                "mode": "local",
                "readable": True,
                "writable": False,
                "library_version": version,
                "sample_count": len(items),
            }
        except Exception as exc:
            errors["local"] = "unreachable" if isinstance(exc, OSError) else self._clean_error(exc)
        if self.library_id and self.api_key:
            try:
                items, version = self._items("web", query=None, limit=1)
                return {
                    "mode": "web",
                    "readable": True,
                    "writable": True,
                    "library_version": version,
                    "sample_count": len(items),
                }
            except Exception as exc:
                errors["web"] = self._clean_error(exc)
        else:
            errors["web"] = "not configured"
        return {
            "mode": "unavailable",
            "readable": False,
            "writable": False,
            "library_version": None,
            "errors": errors,
        }

    def search(self, query: str, *, limit: int = 25) -> list[dict[str, object]]:
        query = _compact_space(query)
        if not query:
            raise ValueError("search query is required")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            items, _ = self._items("local", query=query, limit=limit)
            return items
        except Exception as local_error:
            if not (self.library_id and self.api_key):
                raise RuntimeError(self._clean_error(local_error)) from local_error
        try:
            items, _ = self._items("web", query=query, limit=limit)
            return items
        except Exception as web_error:
            raise RuntimeError(self._clean_error(web_error)) from web_error

    def _duplicate_snapshot(
        self, item: dict[str, object], *, mode: str
    ) -> tuple[list[str], int]:
        queries = []
        doi = _normalize_doi(item.get("DOI"))
        if doi:
            queries.append(doi)
        queries.append(str(item["title"]))
        versions: list[int] = []
        candidates: dict[str, dict[str, object]] = {}
        for query in queries:
            results, version = self._items(mode, query=query, limit=100)
            versions.append(version)
            for result in results:
                key = str(result.get("key") or canonical_json(result).decode("utf-8"))
                candidates[key] = result
        if len(set(versions)) != 1:
            raise RuntimeError("Zotero library changed during duplicate checking")
        title = _title_key(item.get("title"))
        duplicates = []
        for key, candidate in candidates.items():
            same_doi = bool(doi and candidate.get("doi") == doi)
            same_title = bool(title and _title_key(candidate.get("title")) == title)
            if same_doi or same_title:
                duplicates.append(key)
        return sorted(duplicates), versions[0]

    @staticmethod
    def _digest(plan: dict[str, object]) -> str:
        unsigned = {key: value for key, value in plan.items() if key != "digest"}
        return hashlib.sha256(canonical_json(unsigned)).hexdigest()

    def plan_item(self, metadata: dict[str, object]) -> dict[str, object]:
        item = _normalize_metadata(metadata)
        mode = "web" if self.library_id and self.api_key else "local"
        duplicates, library_version = self._duplicate_snapshot(item, mode=mode)
        plan: dict[str, object] = {
            "kind": "zotero_bibliographic_item_v0.1",
            "library_mode": mode,
            "library_type": self.library_type if mode == "web" else "users",
            "library_id": self.library_id if mode == "web" else "0",
            "library_version": library_version,
            "item": item,
            "duplicates": duplicates,
            "can_apply": mode == "web" and not duplicates,
        }
        plan["digest"] = self._digest(plan)
        return plan

    def apply_item(
        self,
        plan: dict[str, object],
        *,
        digest: str,
        confirm_apply: bool,
    ) -> dict[str, object]:
        if not confirm_apply:
            raise PermissionError("explicit apply confirmation is required")
        expected = str(plan.get("digest") or "")
        if not expected or digest != expected or self._digest(plan) != expected:
            raise ValueError("Zotero plan digest does not match")
        if not (self.library_id and self.api_key):
            raise PermissionError("Zotero Web API credentials are not configured")
        if plan.get("library_mode") != "web":
            raise PermissionError("the plan was not created against the Web API library")
        if plan.get("library_type") != self.library_type or str(plan.get("library_id")) != self.library_id:
            raise ValueError("the plan targets a different Zotero library")
        if plan.get("duplicates") or not plan.get("can_apply"):
            raise FileExistsError("the plan contains an exact duplicate")
        item = plan.get("item")
        if not isinstance(item, dict):
            raise ValueError("plan item is invalid")

        duplicates, current_version = self._duplicate_snapshot(item, mode="web")
        if current_version != plan.get("library_version"):
            raise RuntimeError("Zotero library version changed; create a new plan")
        if duplicates:
            raise FileExistsError("an exact duplicate appeared after the plan was created")

        headers = self._headers(web=True, write=True)
        headers["If-Unmodified-Since-Version"] = str(current_version)
        url = f"{self._base('web')}/items"
        response = self.transport.request(
            "POST",
            url,
            headers,
            body=canonical_json([item]),
            timeout=self.timeout,
        )
        if response.status != 200:
            raise RuntimeError(f"Zotero item creation returned HTTP {response.status}")
        try:
            result = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Zotero returned invalid JSON after creation") from exc
        if not isinstance(result, dict) or result.get("failed"):
            raise RuntimeError("Zotero did not confirm item creation")
        successful = result.get("successful") or result.get("success")
        if not isinstance(successful, dict) or set(successful) != {"0"}:
            raise RuntimeError("Zotero did not create exactly one item")
        created = successful["0"]
        if isinstance(created, dict):
            created_key = _compact_space(created.get("key"))
        else:
            created_key = _compact_space(created)
        return {
            "created_key": created_key,
            "library_version": _library_version(response),
            "item_count": 1,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Check read availability")
    search = subparsers.add_parser("search", help="Search bibliographic items")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=25)
    plan = subparsers.add_parser("plan", help="Prepare one immutable item plan")
    plan.add_argument("metadata", type=Path)
    apply = subparsers.add_parser("apply", help="Create the one planned item")
    apply.add_argument("plan", type=Path)
    apply.add_argument("--digest", required=True)
    apply.add_argument("--confirm-apply", action="store_true")
    return parser


def _main() -> int:
    arguments = build_parser().parse_args()
    client = ZoteroClient()
    try:
        if arguments.command == "status":
            result = client.status()
        elif arguments.command == "search":
            result = client.search(arguments.query, limit=arguments.limit)
        elif arguments.command == "plan":
            metadata = json.loads(arguments.metadata.read_text(encoding="utf-8"))
            result = client.plan_item(metadata)
        else:
            plan = json.loads(arguments.plan.read_text(encoding="utf-8"))
            result = client.apply_item(
                plan,
                digest=arguments.digest,
                confirm_apply=arguments.confirm_apply,
            )
        print(canonical_json(redact_secrets(result)).decode("utf-8"))
        return 0
    except Exception as exc:
        print(canonical_json({"ok": False, "error": client._clean_error(exc)}).decode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
