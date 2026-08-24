import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from zotero import ApiResponse, ZoteroClient, build_parser  # noqa: E402


def response(status=200, body=None, *, version="42", headers=None):
    result_headers = {"Last-Modified-Version": version}
    result_headers.update(headers or {})
    return ApiResponse(status, result_headers, json.dumps(body or []).encode("utf-8"))


class FakeTransport:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def request(self, method, url, headers, body=None, timeout=10.0):
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers), "body": body}
        )
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ZoteroReadTests(unittest.TestCase):
    def test_status_prefers_local_read_and_reports_library_version(self):
        transport = FakeTransport(response(body=[], version="17"))
        client = ZoteroClient(transport=transport)
        result = client.status()
        self.assertEqual(result["mode"], "local")
        self.assertEqual(result["library_version"], 17)
        self.assertTrue(result["readable"])
        self.assertFalse(result["writable"])
        self.assertEqual(transport.calls[0]["url"], "http://127.0.0.1:23119/api/users/0/items?limit=1&format=json")
        self.assertEqual(transport.calls[0]["headers"]["Zotero-API-Version"], "3")

    def test_search_falls_back_to_web_and_normalizes_items_without_key_in_url(self):
        item = {
            "key": "ABCD2345",
            "version": 8,
            "data": {
                "itemType": "journalArticle",
                "title": " Example Paper ",
                "creators": [
                    {"creatorType": "author", "firstName": "Ada", "lastName": "Smith"}
                ],
                "date": "2024",
                "publicationTitle": "Economics Journal",
                "DOI": "https://doi.org/10.1000/ABC",
                "url": "https://example.org/paper",
            },
        }
        transport = FakeTransport(response(403, {"error": "disabled"}), response(body=[item]))
        client = ZoteroClient(
            library_id="123",
            api_key="TEST_PRIVATE_VALUE",
            transport=transport,
        )
        results = client.search("example paper", limit=25)
        self.assertEqual(results[0]["doi"], "10.1000/abc")
        self.assertEqual(results[0]["title"], "Example Paper")
        self.assertEqual(results[0]["creators"], ["Ada Smith"])
        web_call = transport.calls[1]
        self.assertEqual(urlsplit(web_call["url"]).netloc, "api.zotero.org")
        self.assertNotIn("TEST_PRIVATE_VALUE", web_call["url"])
        self.assertEqual(web_call["headers"]["Zotero-API-Key"], "TEST_PRIVATE_VALUE")
        self.assertEqual(web_call["headers"]["Zotero-API-Version"], "3")
        self.assertEqual(parse_qs(urlsplit(web_call["url"]).query)["limit"], ["25"])

    def test_search_rejects_unbounded_limit(self):
        client = ZoteroClient(transport=FakeTransport())
        with self.assertRaises(ValueError):
            client.search("query", limit=101)

    def test_status_redacts_configured_key_from_errors(self):
        key = "TEST_PRIVATE_VALUE"
        transport = FakeTransport(OSError("local unavailable"), RuntimeError(f"denied {key}"))
        client = ZoteroClient(library_id="123", api_key=key, transport=transport)
        rendered = json.dumps(client.status())
        self.assertNotIn(key, rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_status_classifies_local_connection_failure_without_os_message(self):
        client = ZoteroClient(
            library_id=None,
            api_key=None,
            transport=FakeTransport(OSError("localized operating-system detail")),
        )
        result = client.status()
        self.assertEqual(result["errors"]["local"], "unreachable")
        self.assertNotIn("localized", json.dumps(result))


class ZoteroWriteTests(unittest.TestCase):
    def _metadata(self):
        return {
            "itemType": "journalArticle",
            "title": "  Test   Article  ",
            "DOI": "https://doi.org/10.1000/ABC ",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": " Ada ",
                    "lastName": " Smith ",
                }
            ],
            "date": "2025",
            "publicationTitle": "Journal of Tests",
        }

    def _client(self, *results, api_key="TEST_PRIVATE_VALUE"):
        transport = FakeTransport(*results)
        return (
            ZoteroClient(
                library_id="123",
                api_key=api_key,
                library_type="users",
                transport=transport,
            ),
            transport,
        )

    def test_plan_normalizes_metadata_and_has_deterministic_digest(self):
        client_one, _ = self._client(
            response(body=[], version="42"), response(body=[], version="42")
        )
        client_two, _ = self._client(
            response(body=[], version="42"), response(body=[], version="42")
        )
        plan_one = client_one.plan_item(self._metadata())
        plan_two = client_two.plan_item(self._metadata())
        self.assertEqual(plan_one["item"]["title"], "Test Article")
        self.assertEqual(plan_one["item"]["DOI"], "10.1000/abc")
        self.assertEqual(plan_one["item"]["creators"][0]["firstName"], "Ada")
        self.assertEqual(plan_one["library_version"], 42)
        self.assertTrue(plan_one["can_apply"])
        self.assertEqual(plan_one["digest"], plan_two["digest"])

    def test_plan_blocks_exact_doi_or_normalized_title_duplicate(self):
        doi_duplicate = {
            "key": "ABCD2345",
            "version": 3,
            "data": {
                "itemType": "journalArticle",
                "title": "Different title",
                "DOI": "10.1000/abc",
                "creators": [],
            },
        }
        title_duplicate = {
            "key": "EFGH6789",
            "version": 4,
            "data": {
                "itemType": "journalArticle",
                "title": "test article",
                "DOI": "",
                "creators": [],
            },
        }
        doi_client, _ = self._client(
            response(body=[doi_duplicate], version="42"),
            response(body=[], version="42"),
        )
        title_client, _ = self._client(
            response(body=[], version="42"),
            response(body=[title_duplicate], version="42"),
        )
        doi_plan = doi_client.plan_item(self._metadata())
        title_plan = title_client.plan_item(self._metadata())
        self.assertEqual(doi_plan["duplicates"], ["ABCD2345"])
        self.assertEqual(title_plan["duplicates"], ["EFGH6789"])
        self.assertFalse(doi_plan["can_apply"])
        self.assertFalse(title_plan["can_apply"])

    def test_apply_requires_confirmation_exact_digest_and_credentials(self):
        client, transport = self._client(
            response(body=[], version="42"), response(body=[], version="42")
        )
        plan = client.plan_item(self._metadata())
        calls_after_plan = len(transport.calls)
        with self.assertRaises(PermissionError):
            client.apply_item(plan, digest=plan["digest"], confirm_apply=False)
        with self.assertRaises(ValueError):
            client.apply_item(plan, digest="0" * 64, confirm_apply=True)
        self.assertEqual(len(transport.calls), calls_after_plan)

        missing, _ = self._client(
            response(body=[], version="42"), response(body=[], version="42"), api_key=None
        )
        local_plan = missing.plan_item(self._metadata())
        with self.assertRaises(PermissionError):
            missing.apply_item(local_plan, digest=local_plan["digest"], confirm_apply=True)

    def test_apply_rechecks_staleness_and_new_duplicates(self):
        stale, _ = self._client(
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=[], version="43"),
            response(body=[], version="43"),
        )
        stale_plan = stale.plan_item(self._metadata())
        with self.assertRaises(RuntimeError):
            stale.apply_item(stale_plan, digest=stale_plan["digest"], confirm_apply=True)

        duplicate = {
            "key": "NEWER234",
            "version": 43,
            "data": {"itemType": "journalArticle", "title": "Test Article", "DOI": ""},
        }
        changed, _ = self._client(
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=[duplicate], version="42"),
        )
        changed_plan = changed.plan_item(self._metadata())
        with self.assertRaises(FileExistsError):
            changed.apply_item(changed_plan, digest=changed_plan["digest"], confirm_apply=True)

    def test_apply_creates_exactly_one_item_with_version_precondition(self):
        created = {
            "successful": {"0": {"key": "WXYZ6789", "version": 43}},
            "unchanged": {},
            "failed": {},
        }
        client, transport = self._client(
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=[], version="42"),
            response(body=created, version="43"),
        )
        plan = client.plan_item(self._metadata())
        result = client.apply_item(plan, digest=plan["digest"], confirm_apply=True)
        call = transport.calls[4]
        payload = json.loads(call["body"].decode("utf-8"))
        self.assertEqual(call["method"], "POST")
        self.assertEqual(len(payload), 1)
        self.assertEqual(call["headers"]["If-Unmodified-Since-Version"], "42")
        self.assertEqual(result["created_key"], "WXYZ6789")
        self.assertEqual(result["library_version"], 43)

    def test_client_and_cli_expose_no_destructive_or_bulk_operations(self):
        client, _ = self._client()
        forbidden = ("attach", "update", "delete", "trash", "purge", "bulk", "arbitrary")
        for name in forbidden:
            self.assertFalse(hasattr(client, name))
        help_text = build_parser().format_help().lower()
        for name in forbidden:
            self.assertNotIn(name, help_text)


if __name__ == "__main__":
    unittest.main()
