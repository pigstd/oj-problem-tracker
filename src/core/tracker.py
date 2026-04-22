from __future__ import annotations

from typing import Callable
from typing import Any

from src.core import cache
from src.oj.base import ContestKey, OJAdapter
from src.output import ANSI_YELLOW, print_colored


CacheStatusCallback = Callable[[str, str], None]


def update_user_cache(
    adapter: OJAdapter,
    user_id: str,
    refresh_cache: bool,
    *,
    status_callback: CacheStatusCallback | None = None,
    emit_output: bool = True,
) -> dict[str, Any]:
    """Load, refresh, and persist one user's cache according to refresh policy."""
    existing_cache = cache.load_user_cache(adapter.name, user_id, adapter)

    if (
        not refresh_cache
        and existing_cache is not None
        and cache.should_skip_cache_update(existing_cache["last_updated_at"])
    ):
        message = f"cache hit, skip update for {user_id}"
        if emit_output:
            print_colored(message, ANSI_YELLOW)
        if status_callback is not None:
            status_callback("cache_hit", message)
        return existing_cache

    message = f"updating cache for {user_id} ..."
    if emit_output:
        print_colored(message, ANSI_YELLOW)
    if status_callback is not None:
        status_callback("updating_cache", message)
    update_payload = adapter.update_submissions(user_id, existing_cache, refresh_cache)

    updated_cache = {
        "version": cache.CACHE_VERSION,
        "oj": adapter.name,
        "user_id": user_id,
        "last_updated_at": cache.now_utc_iso8601(),
    }
    updated_cache.update(update_payload)

    cache.write_user_cache(adapter.name, user_id, updated_cache)
    return updated_cache


def cache_has_done_contest(
    adapter: OJAdapter,
    submissions: list[Any],
    target_contest: ContestKey,
) -> bool:
    """Return whether any cached submission belongs to the target contest."""
    return any(
        adapter.submission_matches_contest(submission, target_contest) for submission in submissions
    )
