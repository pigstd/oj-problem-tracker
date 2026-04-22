import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.core.checks import CheckEvent, CheckRunResult, ContestCheckSummary, ContestWarningSummary
from src.web.server import RunManager, TrackerRequestHandler


class _NonClosingBytesIO(io.BytesIO):
    """Keep in-memory response buffers readable after handler cleanup."""

    def close(self) -> None:
        """Leave the buffer readable for assertions after request handling."""


class _FakeSocket:
    """Provide in-memory read and write streams for HTTP handler tests."""

    def __init__(self, request_bytes: bytes) -> None:
        """Store one raw HTTP request for the handler under test."""
        self._rfile = _NonClosingBytesIO(request_bytes)
        self._wfile = _NonClosingBytesIO()

    def makefile(self, mode: str, *args, **kwargs):  # noqa: ANN001
        """Return the matching in-memory stream requested by BaseHTTPRequestHandler."""
        del args
        del kwargs
        if "r" in mode:
            return self._rfile
        if "w" in mode:
            return self._wfile
        raise ValueError(f"unsupported mode: {mode}")

    def sendall(self, data: bytes) -> None:
        """Capture response bytes written by the handler."""
        self._wfile.write(data)

    def close(self) -> None:
        """Keep the fake socket compatible with BaseHTTPRequestHandler cleanup."""

    @property
    def response_bytes(self) -> bytes:
        """Expose the captured raw HTTP response."""
        return self._wfile.getvalue()


class WebApiTest(unittest.TestCase):
    """Verify localhost web endpoints expose group and run state correctly."""

    def setUp(self) -> None:
        """Create an isolated workspace and start a temporary localhost server."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = Path.cwd()
        os.chdir(self.tmpdir.name)
        Path("usergroup").mkdir(parents=True, exist_ok=True)
        Path("usergroup/example.json").write_text(
            json.dumps({"atcoder": ["alice"], "cf": ["tourist", "Petr"]}),
            encoding="utf-8",
        )

        def fake_check_runner(oj, group, contest_tokens, refresh_cache, *, reporter=None):
            reporter(
                CheckEvent(
                    kind="updating_contest_catalog",
                    message="updating contest catalog for cf ...",
                )
            )
            reporter(
                CheckEvent(
                    kind="checking_user",
                    message="checking user alice ...",
                    user_id="alice",
                    index=1,
                    total=1,
                )
            )
            reporter(
                CheckEvent(
                    kind="contest_hit",
                    message="alice done abc403",
                    user_id="alice",
                    contest_id="abc403",
                )
            )
            reporter(
                CheckEvent(
                    kind="contest_warning",
                    message="warning: alice may have done abc403 via same-round contest abc404",
                    user_id="alice",
                    contest_id="abc403",
                    warning_contests=["abc404"],
                )
            )
            return CheckRunResult(
                oj=oj,
                group=group,
                refresh_cache=refresh_cache,
                contest_tokens=list(contest_tokens),
                expanded_contests=["abc403"],
                users=["alice"],
                contest_summaries=[
                    ContestCheckSummary(
                        contest_id="abc403",
                        matched_users=["alice"],
                        warnings=[
                            ContestWarningSummary(
                                user_id="alice",
                                warning_contests=["abc404"],
                            )
                        ],
                    )
                ],
                events=[],
            )

        self.server = SimpleNamespace(
            run_manager=RunManager(check_runner=fake_check_runner),
            server_name="localhost",
            server_port=8000,
        )

    def tearDown(self) -> None:
        """Restore the working directory and clean up temporary files."""
        os.chdir(self.original_cwd)
        self.tmpdir.cleanup()

    def test_groups_endpoint_lists_valid_group_counts(self) -> None:
        """Verify the group listing endpoint exposes names and per-OJ counts."""
        payload = self._get_json("/api/groups")

        self.assertEqual(payload["groups"][0]["name"], "example")
        self.assertEqual(payload["groups"][0]["counts"]["atcoder"], 1)
        self.assertEqual(payload["groups"][0]["counts"]["cf"], 2)
        self.assertEqual(payload["errors"], [])

    def test_group_detail_endpoint_returns_full_group_members(self) -> None:
        """Verify the group-detail endpoint returns both OJ user lists for the modal."""
        payload = self._get_json("/api/groups/example")

        self.assertEqual(payload["group"]["name"], "example")
        self.assertEqual(payload["group"]["users"]["atcoder"], ["alice"])
        self.assertEqual(payload["group"]["users"]["cf"], ["tourist", "Petr"])

    def test_check_endpoint_runs_in_background_and_can_be_polled(self) -> None:
        """Verify a started run transitions to a completed polling snapshot."""
        created = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example",
                    "contest_tokens": ["abc403"],
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(created["status"], "running")
        run_id = created["run_id"]

        deadline = time.time() + 3
        snapshot = None
        while time.time() < deadline:
            snapshot = self._json_response_from_request(self._get_request(f"/api/runs/{run_id}"))
            if snapshot["status"] == "completed":
                break
            time.sleep(0.05)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["result"]["contest_summaries"][0]["matched_users"], ["alice"])
        self.assertEqual(
            snapshot["result"]["contest_summaries"][0]["warnings"][0]["warning_contests"],
            ["abc404"],
        )
        self.assertEqual(snapshot["events"][0]["kind"], "updating_contest_catalog")
        self.assertEqual(snapshot["events"][1]["kind"], "checking_user")
        self.assertEqual(snapshot["events"][2]["contest_id"], "abc403")

    def test_check_endpoint_rejects_legacy_contest_field_payload(self) -> None:
        """Verify the API only accepts the documented contest_tokens request field."""
        payload = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example",
                    "contest": "abc403 abc404",
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(
            payload["error"]["message"],
            "invalid request payload: 'contest_tokens' must be a non-empty string list",
        )

    def test_index_page_uses_three_panel_layout_and_group_modal(self) -> None:
        """Verify the HTML layout exposes Input, Log, Result, and the group modal."""
        html = self._text_response_from_request(self._get_request("/"))

        self.assertIn("<h1>OJ Problem Tracker</h1>", html)
        self.assertIn("<h2>Input</h2>", html)
        self.assertIn("<h2>Log</h2>", html)
        self.assertIn("<h2>Result</h2>", html)
        self.assertIn('id="group-view-button"', html)
        self.assertIn('id="group-modal"', html)
        self.assertNotIn("User Cache Status", html)

    def test_static_assets_limit_logs_and_keep_page_fixed(self) -> None:
        """Verify CSS and JS encode the fixed-page layout and 3-entry log rule."""
        styles = self._text_response_from_request(self._get_request("/static/styles.css"))
        script = self._text_response_from_request(self._get_request("/static/app.js"))

        self.assertIn("body {", styles)
        self.assertIn("overflow: hidden;", styles)
        self.assertIn(".content-grid {", styles)
        self.assertIn(".result-list {", styles)
        self.assertIn("overflow-y: auto;", styles)
        self.assertIn("slice(-3).reverse()", script)
        self.assertIn("contest_warning", styles)
        self.assertIn("updating_contest_catalog", styles)
        self.assertIn("contest_catalog_warning", styles)
        self.assertIn("Possible same-round matches", script)
        self.assertNotIn('"Starting"', script)
        self.assertNotIn("userResults", script)

    def _get_request(self, path: str) -> bytes:
        """Build one raw GET request for the handler under test."""
        return f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8")

    def _post_request(self, path: str, payload: dict) -> bytes:
        """Build one raw POST request with a JSON body."""
        body = json.dumps(payload).encode("utf-8")
        headers = [
            f"POST {path} HTTP/1.1",
            "Host: localhost",
            "Content-Type: application/json",
            f"Content-Length: {len(body)}",
            "",
            "",
        ]
        return "\r\n".join(headers).encode("utf-8") + body

    def _json_response_from_request(self, request_bytes: bytes) -> dict:
        """Run the handler once and decode the JSON response body."""
        raw_response = self._raw_response_from_request(request_bytes)
        _, body = raw_response.split("\r\n\r\n", maxsplit=1)
        return json.loads(body)

    def _text_response_from_request(self, request_bytes: bytes) -> str:
        """Run the handler once and decode the response body as UTF-8 text."""
        raw_response = self._raw_response_from_request(request_bytes)
        _, body = raw_response.split("\r\n\r\n", maxsplit=1)
        return body

    def _raw_response_from_request(self, request_bytes: bytes) -> str:
        """Run the handler once and return the raw HTTP response text."""
        socket = _FakeSocket(request_bytes)
        TrackerRequestHandler(socket, ("127.0.0.1", 8000), self.server)
        return socket.response_bytes.decode("utf-8")

    def _get_json(self, path: str) -> dict:
        """Run one in-memory GET request and decode the JSON response."""
        return self._json_response_from_request(self._get_request(path))
