from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from src.core import cache as cache_store
from src.core.errors import TrackerError
from src.oj.base import ContestKey, OJAdapter, StatusReporter


API_BASE = "https://codeforces.com/api/user.status"
CONTEST_LIST_API_BASE = "https://codeforces.com/api/contest.list"
CONTEST_CATALOG_CACHE_VERSION = 1
MAX_CONSECUTIVE_FAILURES = 5
REQUEST_INTERVAL_SECONDS = 2
PAGE_SIZE = 1000
USER_AGENT = "oj-problem-tracker/1.0 (+https://github.com/)"
CONTEST_RANGE_PATTERN = re.compile(r"^(?P<start>\d+)-(?P<end>\d+)$")


class CodeforcesAdapter(OJAdapter):
    """Adapter for Codeforces submission fetching, caching, and contest matching."""
    name = "cf"

    def __init__(self) -> None:
        """Track the per-run contest start-time catalog used for warning detection."""
        self._contest_start_times: dict[int, int] = {}

    def prepare_run(
        self,
        refresh_cache: bool,
        *,
        status_callback: StatusReporter | None = None,
    ) -> None:
        """Load the contest catalog cache once so warning checks stay per-run scoped."""
        self._contest_start_times = self._load_or_refresh_contest_catalog(
            refresh_cache,
            status_callback=status_callback,
        )

    def validate_contest(self, contest: str) -> ContestKey:
        """Validate that a Codeforces contest ID is numeric and normalize it to int."""
        if not contest.isdigit():
            raise TrackerError("for --oj cf, --contest must be a pure numeric contestId")
        return int(contest)

    def expand_contest_token(self, token: str) -> list[ContestKey]:
        """Expand a Codeforces contest token into one or more numeric contest IDs."""
        if "-" not in token:
            return [self.validate_contest(token)]

        match = CONTEST_RANGE_PATTERN.fullmatch(token)
        if match is None:
            raise TrackerError(
                f"invalid cf contest token: {token}; expected a numeric contestId or range like 2065-2070"
            )

        start = int(match.group("start"))
        end = int(match.group("end"))
        if start > end:
            raise TrackerError(f"invalid cf contest range: {token}; range start must not exceed end")

        return list(range(start, end + 1))

    def validate_cache_fields(self, cache_data: dict[str, Any], cache_file: Path) -> None:
        """Accept current Codeforces caches and guard legacy next_from_second values if present."""
        if "next_from_second" not in cache_data:
            return

        next_from_second = cache_data["next_from_second"]
        if not isinstance(next_from_second, int) or next_from_second < 0:
            raise TrackerError(
                f"invalid cache format in {cache_file}: "
                "'next_from_second' must be a non-negative integer"
            )

    def update_submissions(
        self,
        user_id: str,
        existing_cache: dict[str, Any] | None,
        refresh_cache: bool,
    ) -> dict[str, Any]:
        """Rebuild the Codeforces submission payload from a fresh full fetch."""
        del existing_cache
        del refresh_cache
        return {"submissions": self._fetch_full_submissions(user_id)}

    def submission_matches_contest(self, submission: Any, contest: ContestKey) -> bool:
        """Return whether a submission belongs to the requested Codeforces contest."""
        if not isinstance(contest, int):
            raise TrackerError("internal error: cf target contest must be int")

        return (
            isinstance(submission, dict)
            and isinstance(submission.get("contestId"), int)
            and submission["contestId"] == contest
        )

    def find_warning_matches(self, submissions: list[Any], contest: ContestKey) -> list[ContestKey]:
        """Return same-round sibling contests that should trigger a warning for a target."""
        if not isinstance(contest, int):
            raise TrackerError("internal error: cf target contest must be int")

        target_start_time = self._contest_start_times.get(contest)
        if target_start_time is None:
            return []

        warning_matches: list[int] = []
        for sibling_contest in (contest - 1, contest + 1):
            if self._contest_start_times.get(sibling_contest) != target_start_time:
                continue
            if any(self.submission_matches_contest(submission, sibling_contest) for submission in submissions):
                warning_matches.append(sibling_contest)

        return warning_matches

    def _fetch_full_submissions(self, handle: str) -> list[Any]:
        """Fetch every submission page for a handle and deduplicate by submission ID."""
        all_submissions: list[Any] = []
        known_submission_ids: set[int] = set()
        from_index = 1

        while True:
            submissions = self._fetch_status_page_with_retry(handle, from_index, PAGE_SIZE)
            if not submissions:
                break

            for submission in submissions:
                if not isinstance(submission, dict):
                    continue
                submission_id = submission.get("id")
                if isinstance(submission_id, int):
                    if submission_id in known_submission_ids:
                        continue
                    known_submission_ids.add(submission_id)
                all_submissions.append(submission)

            if len(submissions) < PAGE_SIZE:
                break

            from_index += PAGE_SIZE

        return all_submissions

    def _fetch_status_page_with_retry(
        self,
        handle: str,
        from_index: int,
        count: int,
    ) -> list[dict[str, Any]]:
        """Retry a paged Codeforces request until success or the failure limit is reached."""
        consecutive_failures = 0
        last_error: str | None = None

        while consecutive_failures < MAX_CONSECUTIVE_FAILURES:
            try:
                result = self._fetch_status_page_once(handle, from_index, count)
                if not isinstance(result, list):
                    raise TrackerError(
                        f"unexpected Codeforces response for handle {handle} from={from_index}: "
                        "result is not a list"
                    )
                return result
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                ValueError,
                TrackerError,
            ) as exc:
                consecutive_failures += 1
                last_error = str(exc)

        raise TrackerError(
            f"Codeforces API request failed {MAX_CONSECUTIVE_FAILURES} times consecutively for "
            f"handle {handle}, from={from_index}, count={count}: {last_error}"
        )

    def _fetch_status_page_once(self, handle: str, from_index: int, count: int) -> list[dict[str, Any]]:
        """Fetch and validate a single Codeforces status page."""
        params = urllib.parse.urlencode(
            {
                "handle": handle,
                "from": str(from_index),
                "count": str(count),
            }
        )
        url = f"{API_BASE}?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        with urllib.request.urlopen(request, timeout=30) as resp:
            payload = resp.read()
        time.sleep(REQUEST_INTERVAL_SECONDS)

        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Codeforces API response root is not an object")

        status = parsed.get("status")
        if status != "OK":
            comment = parsed.get("comment")
            raise ValueError(f"Codeforces API status is not OK: status={status}, comment={comment}")

        result = parsed.get("result")
        if not isinstance(result, list):
            raise ValueError("Codeforces API result is not a submission list")

        return result

    def _load_or_refresh_contest_catalog(
        self,
        refresh_cache: bool,
        *,
        status_callback: StatusReporter | None = None,
    ) -> dict[int, int]:
        """Load the contest catalog cache and refresh it when the cache policy requires."""
        existing_cache = self._load_contest_catalog_cache()

        if (
            not refresh_cache
            and existing_cache is not None
            and cache_store.should_skip_cache_update(existing_cache["last_updated_at"])
        ):
            return self._contest_start_times_from_cache(existing_cache)

        if status_callback is not None:
            status_callback("updating_contest_catalog", "updating contest catalog for cf ...")

        try:
            contests = self._fetch_contests_with_retry()
        except TrackerError:
            if existing_cache is not None:
                return self._contest_start_times_from_cache(existing_cache)
            return {}

        contest_cache = {
            "version": CONTEST_CATALOG_CACHE_VERSION,
            "oj": self.name,
            "last_updated_at": cache_store.now_utc_iso8601(),
            "contests": [
                {
                    "id": contest["id"],
                    "startTimeSeconds": contest["startTimeSeconds"],
                }
                for contest in contests
            ],
        }
        self._write_contest_catalog_cache(contest_cache)
        return self._contest_start_times_from_cache(contest_cache)

    def _get_contest_catalog_cache_file_path(self) -> Path:
        """Return the shared contest catalog cache path for Codeforces."""
        return cache_store.CACHE_ROOT / self.name / "contests.json"

    def _load_contest_catalog_cache(self) -> dict[str, Any] | None:
        """Load and validate the shared contest catalog cache if it exists."""
        cache_file = self._get_contest_catalog_cache_file_path()
        if not cache_file.exists():
            return None

        try:
            with cache_file.open("r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except json.JSONDecodeError:
            return None
        except OSError:
            return None

        if not isinstance(cache_data, dict):
            return None
        if cache_data.get("version") != CONTEST_CATALOG_CACHE_VERSION:
            return None
        if cache_data.get("oj") != self.name:
            return None

        last_updated_at = cache_data.get("last_updated_at")
        contests = cache_data.get("contests")
        if not isinstance(last_updated_at, str) or not isinstance(contests, list):
            return None

        try:
            cache_store.parse_utc_iso8601_to_epoch(last_updated_at)
        except ValueError:
            return None

        for contest in contests:
            if not isinstance(contest, dict):
                return None
            if not isinstance(contest.get("id"), int):
                return None
            if not isinstance(contest.get("startTimeSeconds"), int):
                return None

        return cache_data

    def _write_contest_catalog_cache(self, cache_data: dict[str, Any]) -> None:
        """Persist the shared contest catalog cache atomically."""
        cache_file = self._get_contest_catalog_cache_file_path()
        tmp_file = cache_file.with_suffix(f"{cache_file.suffix}.tmp")

        try:
            with tmp_file.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, cache_file)
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def _contest_start_times_from_cache(self, cache_data: dict[str, Any]) -> dict[int, int]:
        """Convert cached contest metadata into an ID-to-start-time lookup table."""
        return {
            contest["id"]: contest["startTimeSeconds"]
            for contest in cache_data["contests"]
            if isinstance(contest, dict)
            and isinstance(contest.get("id"), int)
            and isinstance(contest.get("startTimeSeconds"), int)
        }

    def _fetch_contests_with_retry(self) -> list[dict[str, Any]]:
        """Retry contest.list until a valid contest array is returned or retries are exhausted."""
        consecutive_failures = 0
        last_error: str | None = None

        while consecutive_failures < MAX_CONSECUTIVE_FAILURES:
            try:
                result = self._fetch_contests_once()
                if not isinstance(result, list):
                    raise TrackerError("unexpected Codeforces contest.list response: result is not a list")
                return result
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                ValueError,
                TrackerError,
            ) as exc:
                consecutive_failures += 1
                last_error = str(exc)

        raise TrackerError(
            f"Codeforces contest.list request failed {MAX_CONSECUTIVE_FAILURES} times consecutively: "
            f"{last_error}"
        )

    def _fetch_contests_once(self) -> list[dict[str, Any]]:
        """Fetch the regular Codeforces contest list used for same-round warnings."""
        params = urllib.parse.urlencode({"gym": "false"})
        url = f"{CONTEST_LIST_API_BASE}?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        with urllib.request.urlopen(request, timeout=30) as resp:
            payload = resp.read()
        time.sleep(REQUEST_INTERVAL_SECONDS)

        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Codeforces contest.list response root is not an object")

        status = parsed.get("status")
        if status != "OK":
            comment = parsed.get("comment")
            raise ValueError(f"Codeforces contest.list status is not OK: status={status}, comment={comment}")

        result = parsed.get("result")
        if not isinstance(result, list):
            raise ValueError("Codeforces contest.list result is not a contest list")

        contests: list[dict[str, Any]] = []
        for contest in result:
            if (
                isinstance(contest, dict)
                and isinstance(contest.get("id"), int)
                and isinstance(contest.get("startTimeSeconds"), int)
            ):
                contests.append(contest)
        return contests
