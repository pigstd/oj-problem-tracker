from __future__ import annotations

import datetime
import json
import os
import time
from pathlib import Path
from typing import Any

from src.core.errors import TrackerError
from src.oj.base import OJAdapter


CACHE_ROOT = Path("cache")
CACHE_VERSION = 2
CACHE_MIN_UPDATE_INTERVAL_SECONDS = 86400


def get_cache_dir(oj: str) -> Path:
    return CACHE_ROOT / oj / "users"


def ensure_cache_dir_exists(oj: str) -> None:
    cache_dir = get_cache_dir(oj)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TrackerError(f"cannot create cache directory {cache_dir}: {exc}") from exc


def get_cache_file_path(oj: str, user_id: str) -> Path:
    return get_cache_dir(oj) / f"{user_id}.json"


def now_utc_iso8601() -> str:
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def parse_utc_iso8601_to_epoch(value: str) -> float:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        raise ValueError("timezone info is required")
    return dt.timestamp()


def _validate_user_cache(
    cache_data: Any,
    oj: str,
    user_id: str,
    cache_file: Path,
    adapter: OJAdapter,
) -> dict[str, Any]:
    if not isinstance(cache_data, dict):
        raise TrackerError(f"invalid cache format in {cache_file}: root must be an object")

    version = cache_data.get("version")
    if not isinstance(version, int):
        raise TrackerError(f"invalid cache format in {cache_file}: 'version' must be an integer")
    if version != CACHE_VERSION:
        raise TrackerError(
            f"unsupported cache version in {cache_file}: expected {CACHE_VERSION}, got {version}"
        )

    cache_oj = cache_data.get("oj")
    if not isinstance(cache_oj, str) or cache_oj != oj:
        raise TrackerError(
            f"invalid cache format in {cache_file}: 'oj' must be '{oj}', got {cache_oj}"
        )

    cached_user_id = cache_data.get("user_id")
    if not isinstance(cached_user_id, str) or not cached_user_id:
        raise TrackerError(f"invalid cache format in {cache_file}: 'user_id' must be a string")
    if cached_user_id != user_id:
        raise TrackerError(
            f"invalid cache format in {cache_file}: user_id mismatch "
            f"(expected {user_id}, got {cached_user_id})"
        )

    last_updated_at = cache_data.get("last_updated_at")
    if not isinstance(last_updated_at, str) or not last_updated_at:
        raise TrackerError(
            f"invalid cache format in {cache_file}: 'last_updated_at' must be a non-empty string"
        )
    try:
        parse_utc_iso8601_to_epoch(last_updated_at)
    except ValueError as exc:
        raise TrackerError(
            f"invalid cache format in {cache_file}: invalid 'last_updated_at': {last_updated_at}"
        ) from exc

    submissions = cache_data.get("submissions")
    if not isinstance(submissions, list):
        raise TrackerError(f"invalid cache format in {cache_file}: 'submissions' must be a list")

    adapter.validate_cache_fields(cache_data, cache_file)
    return cache_data


def load_user_cache(oj: str, user_id: str, adapter: OJAdapter) -> dict[str, Any] | None:
    cache_file = get_cache_file_path(oj, user_id)
    if not cache_file.exists():
        return None

    try:
        with cache_file.open("r", encoding="utf-8") as f:
            cache_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise TrackerError(f"invalid JSON in cache file {cache_file}: {exc}") from exc
    except OSError as exc:
        raise TrackerError(f"cannot read cache file {cache_file}: {exc}") from exc

    return _validate_user_cache(cache_data, oj, user_id, cache_file, adapter)


def write_user_cache(oj: str, user_id: str, cache_data: dict[str, Any]) -> None:
    cache_file = get_cache_file_path(oj, user_id)
    tmp_file = cache_file.with_suffix(f"{cache_file.suffix}.tmp")

    try:
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, cache_file)
    except OSError as exc:
        raise TrackerError(f"cannot write cache file {cache_file}: {exc}") from exc
    finally:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass


def collect_submission_ids(submissions: list[Any]) -> set[int]:
    known_ids: set[int] = set()
    for submission in submissions:
        if not isinstance(submission, dict):
            continue
        submission_id = submission.get("id")
        if isinstance(submission_id, int):
            known_ids.add(submission_id)
    return known_ids


def should_skip_cache_update(last_updated_at: str, now_epoch_second: float | None = None) -> bool:
    if now_epoch_second is None:
        now_epoch_second = time.time()
    updated_at_epoch = parse_utc_iso8601_to_epoch(last_updated_at)
    return now_epoch_second - updated_at_epoch < CACHE_MIN_UPDATE_INTERVAL_SECONDS
