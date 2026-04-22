from __future__ import annotations

import argparse
import json
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from src.core.checks import CheckEvent, CheckRunResult, run_check
from src.core.errors import TrackerError
from src.core.groups import get_group_detail, list_group_summaries
from src.oj.cf import normalize_selected_contest_types
from src.oj.registry import available_oj_names


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
STATIC_ROOT = Path(__file__).with_name("static")
MAX_STORED_RUNS = 20


def _utc_now_iso8601() -> str:
    """Return an ISO 8601 timestamp in UTC for API metadata."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    """Write a JSON response body with the provided HTTP status."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_request(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    """Parse a small JSON request body for API endpoints."""
    content_length = handler.headers.get("Content-Length")
    if content_length is None:
        raise TrackerError("missing Content-Length header")

    try:
        length = int(content_length)
    except ValueError as exc:
        raise TrackerError("invalid Content-Length header") from exc

    raw_body = handler.rfile.read(length)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrackerError(f"invalid JSON request body: {exc}") from exc

    if not isinstance(payload, dict):
        raise TrackerError("invalid JSON request body: root must be an object")
    return payload


def _normalize_check_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a web check request payload."""
    oj = payload.get("oj")
    group = payload.get("group")
    contest_tokens = payload.get("contest_tokens")
    contest_types = payload.get("contest_types")
    refresh_cache = payload.get("refresh_cache", False)

    if not isinstance(oj, str) or oj not in available_oj_names():
        raise TrackerError(f"invalid request payload: 'oj' must be one of {available_oj_names()}")
    if not isinstance(group, str) or not group.strip():
        raise TrackerError("invalid request payload: 'group' must be a non-empty string")

    if not isinstance(contest_tokens, list) or not contest_tokens:
        raise TrackerError("invalid request payload: 'contest_tokens' must be a non-empty string list")
    if not all(isinstance(token, str) and token.strip() for token in contest_tokens):
        raise TrackerError("invalid request payload: every contest token must be a non-empty string")
    if contest_types is not None and not isinstance(contest_types, list):
        raise TrackerError("invalid request payload: 'contest_types' must be a string list")
    if contest_types is not None and not contest_types:
        raise TrackerError("invalid request payload: 'contest_types' must be a non-empty string list")
    if contest_types is not None and not all(
        isinstance(contest_type, str) and contest_type.strip() for contest_type in contest_types
    ):
        raise TrackerError("invalid request payload: every contest type must be a non-empty string")
    if not isinstance(refresh_cache, bool):
        raise TrackerError("invalid request payload: 'refresh_cache' must be a boolean")

    return {
        "oj": oj,
        "group": group.strip(),
        "contest_tokens": [token.strip() for token in contest_tokens],
        "contest_types": normalize_selected_contest_types(oj, contest_types),
        "refresh_cache": refresh_cache,
    }


def _error_status_for_group_error(exc: TrackerError) -> int:
    """Map group-loading failures to the most appropriate HTTP status."""
    if str(exc).startswith("group file not found:"):
        return HTTPStatus.NOT_FOUND
    return HTTPStatus.BAD_REQUEST


class RunManager:
    """Track one active localhost run at a time and expose polling snapshots."""

    def __init__(
        self,
        *,
        check_runner: Callable[..., CheckRunResult] = run_check,
    ) -> None:
        """Store run metadata in memory for the polling API."""
        self._check_runner = check_runner
        self._lock = threading.Lock()
        self._runs: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._active_run_id: str | None = None

    def start_run(self, request_payload: dict[str, Any]) -> tuple[str | None, str | None]:
        """Start a new background run or return the currently active run ID."""
        with self._lock:
            if self._active_run_id is not None:
                active_run = self._runs.get(self._active_run_id)
                if active_run is not None and active_run["status"] == "running":
                    return None, self._active_run_id

            run_id = uuid.uuid4().hex[:12]
            self._runs[run_id] = {
                "run_id": run_id,
                "status": "running",
                "request": dict(request_payload),
                "events": [],
                "result": None,
                "error": None,
                "started_at": _utc_now_iso8601(),
                "finished_at": None,
            }
            self._active_run_id = run_id
            self._prune_completed_runs_locked()

        worker = threading.Thread(
            target=self._run_in_background,
            args=(run_id, request_payload),
            daemon=True,
        )
        worker.start()
        return run_id, None

    def get_run_snapshot(self, run_id: str) -> dict[str, Any] | None:
        """Return a copy of one run snapshot for the polling API."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            return {
                "run_id": run["run_id"],
                "status": run["status"],
                "request": dict(run["request"]),
                "events": [dict(event) for event in run["events"]],
                "result": dict(run["result"]) if run["result"] is not None else None,
                "error": dict(run["error"]) if run["error"] is not None else None,
                "started_at": run["started_at"],
                "finished_at": run["finished_at"],
            }

    def _run_in_background(self, run_id: str, request_payload: dict[str, Any]) -> None:
        """Execute one check run and persist its final status in memory."""
        try:
            result = self._check_runner(
                request_payload["oj"],
                request_payload["group"],
                request_payload["contest_tokens"],
                request_payload["refresh_cache"],
                contest_types=request_payload["contest_types"],
                reporter=lambda event: self._append_event(run_id, event),
            )
        except TrackerError as exc:
            self._finish_run(run_id, status="failed", error={"message": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            self._finish_run(
                run_id,
                status="failed",
                error={"message": f"internal server error: {exc.__class__.__name__}"},
            )
            return

        self._finish_run(run_id, status="completed", result=result.to_dict())

    def _append_event(self, run_id: str, event: CheckEvent) -> None:
        """Append one structured event to a running snapshot."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run["events"].append(event.to_dict())

    def _finish_run(
        self,
        run_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Finalize a run snapshot and release the active-run slot."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run["status"] = status
            run["result"] = result
            run["error"] = error
            run["finished_at"] = _utc_now_iso8601()
            if self._active_run_id == run_id:
                self._active_run_id = None

    def _prune_completed_runs_locked(self) -> None:
        """Cap stored history so localhost sessions do not grow without bound."""
        while len(self._runs) > MAX_STORED_RUNS:
            oldest_run_id, oldest_run = next(iter(self._runs.items()))
            if oldest_run["status"] == "running":
                break
            self._runs.pop(oldest_run_id)


class TrackerWebServer(ThreadingHTTPServer):
    """HTTP server that exposes the run manager to request handlers."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        run_manager: RunManager | None = None,
    ) -> None:
        """Attach a run manager instance to the HTTP server."""
        super().__init__(server_address, handler_class)
        self.run_manager = run_manager or RunManager()


class TrackerRequestHandler(BaseHTTPRequestHandler):
    """Serve the localhost frontend and its JSON API."""

    server_version = "OJProblemTrackerWeb/1.0"

    @property
    def run_manager(self) -> RunManager:
        """Return the run manager attached to the HTTP server."""
        return self.server.run_manager

    def do_GET(self) -> None:  # noqa: N802
        """Handle static asset and JSON polling requests."""
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static_file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            static_name = parsed.path.removeprefix("/static/")
            self._serve_static_asset(static_name)
            return
        if parsed.path == "/api/groups":
            groups, errors = list_group_summaries()
            _json_response(self, HTTPStatus.OK, {"groups": groups, "errors": errors})
            return
        if parsed.path.startswith("/api/groups/"):
            group_name = unquote(parsed.path.removeprefix("/api/groups/"))
            try:
                detail = get_group_detail(group_name)
            except TrackerError as exc:
                _json_response(
                    self,
                    _error_status_for_group_error(exc),
                    {"error": {"message": str(exc)}},
                )
                return
            _json_response(self, HTTPStatus.OK, {"group": detail})
            return
        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path.removeprefix("/api/runs/")
            snapshot = self.run_manager.get_run_snapshot(run_id)
            if snapshot is None:
                _json_response(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"error": {"message": f"run not found: {run_id}"}},
                )
                return
            _json_response(self, HTTPStatus.OK, snapshot)
            return

        _json_response(self, HTTPStatus.NOT_FOUND, {"error": {"message": "route not found"}})

    def do_POST(self) -> None:  # noqa: N802
        """Handle JSON API mutations for launching checks."""
        parsed = urlparse(self.path)
        if parsed.path != "/api/check":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": {"message": "route not found"}})
            return

        try:
            request_payload = _normalize_check_request(_read_json_request(self))
        except TrackerError as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": {"message": str(exc)}})
            return

        run_id, active_run_id = self.run_manager.start_run(request_payload)
        if active_run_id is not None:
            _json_response(
                self,
                HTTPStatus.CONFLICT,
                {
                    "error": {
                        "message": "a check is already running",
                        "run_id": active_run_id,
                    }
                },
            )
            return

        _json_response(
            self,
            HTTPStatus.ACCEPTED,
            {
                "run_id": run_id,
                "status": "running",
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Silence default request logging for the localhost tool UI."""
        del format
        del args

    def _serve_static_asset(self, name: str) -> None:
        """Serve one static asset with a conservative content type."""
        if name == "styles.css":
            self._serve_static_file(name, "text/css; charset=utf-8")
            return
        if name == "app.js":
            self._serve_static_file(name, "application/javascript; charset=utf-8")
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": {"message": "asset not found"}})

    def _serve_static_file(self, name: str, content_type: str) -> None:
        """Serve one file from the static directory."""
        file_path = STATIC_ROOT / name
        if not file_path.exists():
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": {"message": "asset not found"}})
            return

        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Start the localhost web server and block until interrupted."""
    server = TrackerWebServer((host, port), TrackerRequestHandler)
    print(f"Serving oj-problem-tracker web UI at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse host and port flags for the localhost web server."""
    parser = argparse.ArgumentParser(description="Run the oj-problem-tracker localhost web UI.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the localhost web server process."""
    args = parse_args(argv)
    run_server(args.host, args.port)
    return 0
