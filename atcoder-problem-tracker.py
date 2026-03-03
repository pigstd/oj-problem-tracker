#!/usr/bin/env python3

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions"
API_PROXY_PREFIX = "https://r.jina.ai/http://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions"
MAX_CONSECUTIVE_FAILURES = 5
DIRECT_API_BLOCKED = False


class TrackerError(Exception):
    """Domain-specific error for this script."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether users in a group have submissions in a target contest."
    )
    parser.add_argument(
        "-c",
        "--contest",
        required=True,
        help="Contest ID to check, for example: abc403",
    )
    parser.add_argument(
        "-g",
        "--group",
        required=True,
        help="Group file name in usergroup/ without .json suffix, for example: example",
    )
    return parser.parse_args()


def load_group_users(group_name: str) -> list[str]:
    group_file = Path("usergroup") / f"{group_name}.json"
    if not group_file.exists():
        raise TrackerError(f"group file not found: {group_file}")

    try:
        with group_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise TrackerError(f"invalid JSON in group file {group_file}: {exc}") from exc
    except OSError as exc:
        raise TrackerError(f"cannot read group file {group_file}: {exc}") from exc

    if not isinstance(data, dict):
        raise TrackerError(f"invalid group format in {group_file}: root must be an object")

    users = data.get("users")
    if users is None:
        raise TrackerError(f"invalid group format in {group_file}: missing 'users' field")
    if not isinstance(users, list):
        raise TrackerError(f"invalid group format in {group_file}: 'users' must be a list")
    if not users:
        raise TrackerError(f"invalid group format in {group_file}: 'users' must not be empty")
    if not all(isinstance(user, str) and user.strip() for user in users):
        raise TrackerError(
            f"invalid group format in {group_file}: every user must be a non-empty string"
        )

    return users


def fetch_submissions_with_retry(user_id: str, from_second: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"user": user_id, "from_second": str(from_second)})
    direct_url = f"{API_BASE}?{params}"
    proxy_url = f"{API_PROXY_PREFIX}?{params}"

    consecutive_failures = 0
    last_error: str | None = None
    while consecutive_failures < MAX_CONSECUTIVE_FAILURES:
        try:
            result = _fetch_submissions_once(direct_url, proxy_url)
            if not isinstance(result, list):
                raise TrackerError(
                    f"unexpected API response for user {user_id} from_second={from_second}: "
                    "response is not a list"
                )

            return result
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            TrackerError,
        ) as exc:
            consecutive_failures += 1
            last_error = str(exc)

    raise TrackerError(
        f"API request failed 5 times consecutively for user {user_id}, "
        f"from_second={from_second}: {last_error}"
    )


def _fetch_submissions_once(direct_url: str, proxy_url: str) -> list[dict[str, Any]]:
    global DIRECT_API_BLOCKED

    headers = {"User-Agent": "atcoder-problem-tracker/1.0 (+https://github.com/)"}

    # 首先尝试直连 API；如果直连 403，则自动尝试只读代理回退。
    if not DIRECT_API_BLOCKED:
        direct_request = urllib.request.Request(direct_url, headers=headers)
        try:
            with urllib.request.urlopen(direct_request, timeout=30) as resp:
                payload = resp.read()
            time.sleep(1)
            return _parse_submissions_payload(payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            time.sleep(1)
            if exc.code != 403:
                raise
            DIRECT_API_BLOCKED = True

    proxy_request = urllib.request.Request(proxy_url, headers=headers)
    with urllib.request.urlopen(proxy_request, timeout=30) as resp:
        payload = resp.read()
    time.sleep(1)
    return _parse_submissions_payload(payload.decode("utf-8"))


def _parse_submissions_payload(text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        marker = "Markdown Content:"
        if marker not in text:
            raise
        _, markdown = text.split(marker, maxsplit=1)
        parsed = json.loads(markdown.strip())

    if not isinstance(parsed, list):
        raise TrackerError("API response is not a submission list")
    return parsed


def user_has_done_contest(user_id: str, target_contest: str) -> bool:
    target_lower = target_contest.lower()
    from_second = 0

    while True:
        submissions = fetch_submissions_with_retry(user_id, from_second)
        if not submissions:
            return False

        for submission in submissions:
            if (
                isinstance(submission, dict)
                and isinstance(submission.get("contest_id"), str)
                and submission["contest_id"].lower() == target_lower
            ):
                return True

        epoch_seconds = [
            s.get("epoch_second")
            for s in submissions
            if isinstance(s, dict) and isinstance(s.get("epoch_second"), int)
        ]
        if not epoch_seconds:
            raise TrackerError(
                f"unexpected API response for user {user_id}: no valid epoch_second field found"
            )

        from_second = max(epoch_seconds) + 1


def main() -> int:
    args = parse_args()
    users = load_group_users(args.group)

    found_any = False
    for user_id in users:
        print(f"checking user {user_id} ...", flush=True)
        if user_has_done_contest(user_id, args.contest):
            print(f"{user_id} done {args.contest}")
            found_any = True

    if not found_any:
        print(f"no users have done {args.contest}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except TrackerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
