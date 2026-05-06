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
        self.check_calls: list[dict[str, object]] = []

        def fake_check_runner(
            oj,
            group,
            contest_tokens,
            refresh_cache,
            *,
            contest_types=None,
            group_users_by_oj=None,
            reporter=None,
        ):
            self.check_calls.append(
                {
                    "oj": oj,
                    "group": group,
                    "group_users_by_oj": group_users_by_oj,
                    "contest_tokens": list(contest_tokens),
                    "refresh_cache": refresh_cache,
                    "contest_types": contest_types,
                }
            )
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

    def test_removed_group_endpoints_now_return_not_found(self) -> None:
        """Verify the web API no longer exposes server-side group listing routes."""
        payload = self._get_json("/api/groups")

        self.assertEqual(payload["error"]["message"], "route not found")

    def test_check_endpoint_runs_in_background_and_can_be_polled(self) -> None:
        """Verify a started run transitions to a completed polling snapshot."""
        created = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example-local",
                    "group_users": {
                        "atcoder": ["alice"],
                        "cf": ["tourist", "Petr"],
                    },
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
        self.assertEqual(snapshot["request"]["group"], "example-local")
        self.assertEqual(snapshot["request"]["group_users"]["atcoder"], ["alice"])
        self.assertEqual(snapshot["result"]["contest_summaries"][0]["matched_users"], ["alice"])
        self.assertEqual(
            snapshot["result"]["contest_summaries"][0]["warnings"][0]["warning_contests"],
            ["abc404"],
        )
        self.assertEqual(snapshot["events"][0]["kind"], "updating_contest_catalog")
        self.assertEqual(snapshot["events"][1]["kind"], "checking_user")
        self.assertEqual(snapshot["events"][2]["contest_id"], "abc403")
        self.assertEqual(self.check_calls[0]["group"], "example-local")
        self.assertEqual(
            self.check_calls[0]["group_users_by_oj"],
            {"atcoder": ["alice"], "cf": ["tourist", "Petr"]},
        )
        self.assertEqual(self.check_calls[0]["contest_types"], None)

    def test_check_endpoint_accepts_cf_contest_type_filters(self) -> None:
        """Verify the web API forwards normalized Codeforces contest-type filters to the runner."""
        created = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "cf",
                    "group": "example-local",
                    "group_users": {
                        "atcoder": ["alice"],
                        "cf": ["tourist", "Petr"],
                    },
                    "contest_tokens": ["2065"],
                    "contest_types": ["div1", "DIV2", "div1"],
                    "refresh_cache": False,
                },
            )
        )

        deadline = time.time() + 3
        snapshot = None
        while time.time() < deadline:
            snapshot = self._json_response_from_request(self._get_request(f"/api/runs/{created['run_id']}"))
            if snapshot["status"] == "completed":
                break
            time.sleep(0.05)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(self.check_calls[-1]["oj"], "cf")
        self.assertEqual(self.check_calls[-1]["contest_types"], ["div1", "div2"])

    def test_check_endpoint_rejects_missing_group_users_payload(self) -> None:
        """Verify the API requires explicit local-group users in every check request."""
        payload = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example-local",
                    "contest_tokens": ["abc403"],
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(
            payload["error"]["message"],
            "invalid request payload: 'group_users' must be an object",
        )

    def test_check_endpoint_rejects_legacy_contest_field_payload(self) -> None:
        """Verify the API only accepts the documented contest_tokens request field."""
        payload = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example-local",
                    "group_users": {
                        "atcoder": ["alice"],
                        "cf": ["tourist", "Petr"],
                    },
                    "contest": "abc403 abc404",
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(
            payload["error"]["message"],
            "invalid request payload: 'contest_tokens' must be a non-empty string list",
        )

    def test_check_endpoint_rejects_empty_contest_type_list(self) -> None:
        """Verify the API rejects a Codeforces request with no selected contest types."""
        payload = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "cf",
                    "group": "example-local",
                    "group_users": {
                        "atcoder": ["alice"],
                        "cf": ["tourist", "Petr"],
                    },
                    "contest_tokens": ["2065"],
                    "contest_types": [],
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(
            payload["error"]["message"],
            "invalid request payload: 'contest_types' must be a non-empty string list",
        )

    def test_check_endpoint_rejects_non_cf_specific_contest_type_filters(self) -> None:
        """Verify contest-type filtering cannot be requested for non-Codeforces runs."""
        payload = self._json_response_from_request(
            self._post_request(
                "/api/check",
                {
                    "oj": "atcoder",
                    "group": "example-local",
                    "group_users": {
                        "atcoder": ["alice"],
                        "cf": ["tourist", "Petr"],
                    },
                    "contest_tokens": ["abc403"],
                    "contest_types": ["div1"],
                    "refresh_cache": False,
                },
            )
        )

        self.assertEqual(
            payload["error"]["message"],
            "contest type filtering is only supported for --oj cf",
        )

    def test_index_page_uses_three_panel_layout_and_group_modal(self) -> None:
        """Verify the HTML layout exposes Input, Log, Result, and the group modal."""
        html = self._text_response_from_request(self._get_request("/"))

        self.assertIn("<h1>OJ Problem Tracker</h1>", html)
        self.assertIn('class="title-repo-link"', html)
        self.assertIn('href="https://github.com/pigstd/oj-problem-tracker"', html)
        self.assertIn('aria-label="View source on GitHub"', html)
        self.assertIn('class="title-repo-icon"', html)
        self.assertIn('class="language-switch"', html)
        self.assertIn('data-language="en"', html)
        self.assertIn('data-language="zh-CN"', html)
        self.assertIn('aria-pressed="true"', html)
        self.assertIn('data-i18n-aria-label="language.switchLabel"', html)
        self.assertIn('id="theme-select"', html)
        self.assertIn('value="classic"', html)
        self.assertIn('value="ocean"', html)
        self.assertIn('value="light"', html)
        self.assertIn('value="rainbow"', html)
        self.assertIn('data-i18n="theme.label"', html)
        self.assertIn('data-i18n="theme.classic"', html)
        self.assertIn('data-i18n="theme.rainbow"', html)
        self.assertNotIn("github.com/pigstd/oj-problem-tracker</a>", html)
        self.assertIn('data-i18n="panel.input">Input</h2>', html)
        self.assertIn('data-i18n="panel.log">Log</h2>', html)
        self.assertIn('data-i18n="panel.result">Result</h2>', html)
        self.assertIn('id="submit-button"', html)
        self.assertIn('form="check-form"', html)
        self.assertIn('id="group-view-button"', html)
        self.assertIn('id="group-edit-button"', html)
        self.assertIn('id="group-new-button"', html)
        self.assertIn('id="group-import-button"', html)
        self.assertIn('id="group-delete-button"', html)
        self.assertIn('id="group-import-input"', html)
        self.assertIn('id="group-modal"', html)
        self.assertIn('id="cf-contest-type-fieldset"', html)
        self.assertIn('id="contest-type-toggle"', html)
        self.assertIn('id="contest-type-panel"', html)
        self.assertIn('id="contest-type-select-all"', html)
        self.assertIn('id="contest-type-clear-all"', html)
        self.assertIn("Choose contest type (6 selected)", html)
        self.assertNotIn("Stored in this browser only.", html)
        self.assertNotIn("User Cache Status", html)

    def test_static_assets_limit_logs_and_keep_page_fixed(self) -> None:
        """Verify CSS and JS encode the fixed-page layout and 3-entry log rule."""
        styles = self._text_response_from_request(self._get_request("/static/styles.css"))
        script = self._text_response_from_request(self._get_request("/static/app.js"))

        self.assertIn("body {", styles)
        self.assertIn("[hidden] {", styles)
        self.assertIn("overflow: hidden;", styles)
        self.assertIn(".title-repo-link {", styles)
        self.assertIn(".title-repo-icon {", styles)
        self.assertIn(".language-switch,\n.theme-switch {", styles)
        self.assertIn(".language-option.active,", styles)
        self.assertIn(".theme-switch {", styles)
        self.assertIn("white-space: nowrap;", styles)
        self.assertIn(".theme-select {", styles)
        self.assertIn("width: 88px;", styles)
        self.assertIn("height: 26px;", styles)
        self.assertIn("appearance: none;", styles)
        self.assertIn(".theme-switch::after {", styles)
        self.assertIn(':root[data-theme="ocean"] {', styles)
        self.assertIn(':root[data-theme="light"] {', styles)
        self.assertIn(':root[data-theme="rainbow"] {', styles)
        self.assertIn("--page-background", styles)
        self.assertIn("--chrome-active-bg", styles)
        self.assertIn("--surface-input", styles)
        self.assertIn("--submit-button-bg", styles)
        self.assertIn(".content-grid {", styles)
        self.assertIn(".input-panel {", styles)
        self.assertIn(".panel-submit-button {", styles)
        self.assertIn(".result-list {", styles)
        self.assertIn("overflow-y: auto;", styles)
        self.assertIn("slice(-3).reverse()", script)
        self.assertIn(".contest-type-toggle {", styles)
        self.assertIn(".contest-type-panel {", styles)
        self.assertIn(".contest-type-grid-shell {", styles)
        self.assertIn(".contest-type-grid {", styles)
        self.assertIn(".group-actions {", styles)
        self.assertIn(".editor-grid {", styles)
        self.assertIn(".badge.hit {\n  color: var(--danger);", styles)
        self.assertIn(".badge.miss {\n  color: var(--success);", styles)
        self.assertIn(".badge.skipped {", styles)
        self.assertIn("contest_warning", styles)
        self.assertIn("contest_skipped", styles)
        self.assertIn("updating_contest_catalog", styles)
        self.assertIn("contest_catalog_warning", styles)
        self.assertIn("isContestTypeExpanded", script)
        self.assertIn("LANGUAGE_STORAGE_KEY", script)
        self.assertIn("oj-problem-tracker.language.v1", script)
        self.assertIn("THEME_STORAGE_KEY", script)
        self.assertIn("oj-problem-tracker.theme.v1", script)
        self.assertIn('SUPPORTED_THEMES = ["classic", "ocean", "light", "rainbow"]', script)
        self.assertIn("translations", script)
        self.assertIn("applyLanguage", script)
        self.assertIn("setLanguage", script)
        self.assertIn("applyTheme", script)
        self.assertIn("setTheme", script)
        self.assertIn("theme.classic", script)
        self.assertIn("theme.ocean", script)
        self.assertIn("theme.light", script)
        self.assertIn("theme.rainbow", script)
        self.assertIn("Theme", script)
        self.assertIn("主题", script)
        self.assertIn("Classic", script)
        self.assertIn("Ocean", script)
        self.assertIn("Light", script)
        self.assertIn("Rainbow", script)
        self.assertIn("彩虹", script)
        self.assertIn("formError: null", script)
        self.assertIn("renderStoredFormError();", script)
        self.assertIn("function renderFormErrorKey(key, params = {})", script)
        self.assertIn("function renderFormErrorFromError(error)", script)
        self.assertIn('renderFormErrorKey("error.noContestToken")', script)
        self.assertIn("语言", script)
        self.assertIn("开始检查", script)
        self.assertIn("选择比赛类型", script)
        self.assertIn("输入", script)
        self.assertIn("日志", script)
        self.assertIn("结果", script)
        self.assertIn('aria-expanded", String(isExpanded)', script)
        self.assertIn("Choose contest type (", script)
        self.assertIn("contestTypePanel.hidden = !isExpanded", script)
        self.assertIn("Possible same-round matches", script)
        self.assertIn("Select at least one Codeforces contest type", script)
        self.assertIn("getSelectedContestTypes()", script)
        self.assertIn("localStorage", script)
        self.assertIn("group_users", script)
        self.assertNotIn('"/api/groups"', script)
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
