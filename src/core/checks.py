from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, TypeAlias

from src.core import cache, tracker
from src.core.groups import load_group_users
from src.oj.base import ContestKey
from src.oj.registry import get_adapter


EventReporter: TypeAlias = Callable[["CheckEvent"], None]


@dataclass(slots=True)
class CheckEvent:
    """Describe one user-facing event emitted while a check is running."""

    kind: str
    message: str
    user_id: str | None = None
    contest_id: str | None = None
    index: int | None = None
    total: int | None = None
    matched_users: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable event payload without unused fields."""
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(slots=True)
class ContestCheckSummary:
    """Summarize which users matched one expanded contest."""

    contest_id: str
    matched_users: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable contest summary."""
        return asdict(self)


@dataclass(slots=True)
class CheckRunResult:
    """Capture the full structured result of one check run."""

    oj: str
    group: str
    refresh_cache: bool
    contest_tokens: list[str]
    expanded_contests: list[str]
    users: list[str]
    contest_summaries: list[ContestCheckSummary]
    events: list[CheckEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result payload for the web API."""
        return {
            "oj": self.oj,
            "group": self.group,
            "refresh_cache": self.refresh_cache,
            "contest_tokens": list(self.contest_tokens),
            "expanded_contests": list(self.expanded_contests),
            "users": list(self.users),
            "contest_summaries": [summary.to_dict() for summary in self.contest_summaries],
            "events": [event.to_dict() for event in self.events],
        }


def _expand_target_contests(contest_tokens: list[str], adapter: Any) -> list[ContestKey]:
    """Expand raw contest tokens into a flat ordered contest list."""
    target_contests: list[ContestKey] = []
    for token in contest_tokens:
        target_contests.extend(adapter.expand_contest_token(token))
    return target_contests


def run_check(
    oj: str,
    group: str,
    contest_tokens: list[str],
    refresh_cache: bool,
    *,
    reporter: EventReporter | None = None,
) -> CheckRunResult:
    """Run one structured check so CLI and web can share the same workflow."""
    adapter = get_adapter(oj)
    target_contests = _expand_target_contests(contest_tokens, adapter)
    users = load_group_users(group, oj)
    cache.ensure_cache_dir_exists(adapter.name)

    events: list[CheckEvent] = []
    contest_summaries: list[ContestCheckSummary] = []
    user_caches: dict[str, dict[str, Any]] = {}
    total_users = len(users)

    def emit(event: CheckEvent) -> None:
        """Record an event locally and forward it to an optional reporter."""
        events.append(event)
        if reporter is not None:
            reporter(event)

    for index, user_id in enumerate(users, start=1):
        emit(
            CheckEvent(
                kind="checking_user",
                message=f"checking user {user_id} ...",
                user_id=user_id,
                index=index,
                total=total_users,
            )
        )

        def on_cache_status(kind: str, message: str) -> None:
            """Translate tracker cache status callbacks into structured events."""
            emit(
                CheckEvent(
                    kind=kind,
                    message=message,
                    user_id=user_id,
                    index=index,
                    total=total_users,
                )
            )

        user_cache = tracker.update_user_cache(
            adapter,
            user_id,
            refresh_cache,
            status_callback=on_cache_status,
            emit_output=False,
        )
        user_caches[user_id] = user_cache

    for target_contest in target_contests:
        contest_label = str(target_contest)
        matched_users: list[str] = []

        for user_id in users:
            if tracker.cache_has_done_contest(adapter, user_caches[user_id]["submissions"], target_contest):
                matched_users.append(user_id)
                emit(
                    CheckEvent(
                        kind="contest_hit",
                        message=f"{user_id} done {contest_label}",
                        user_id=user_id,
                        contest_id=contest_label,
                    )
                )

        if not matched_users:
            emit(
                CheckEvent(
                    kind="contest_miss",
                    message=f"no users have done {contest_label}",
                    contest_id=contest_label,
                    matched_users=[],
                )
            )

        contest_summaries.append(
            ContestCheckSummary(contest_id=contest_label, matched_users=matched_users)
        )

    return CheckRunResult(
        oj=oj,
        group=group,
        refresh_cache=refresh_cache,
        contest_tokens=list(contest_tokens),
        expanded_contests=[str(contest) for contest in target_contests],
        users=list(users),
        contest_summaries=contest_summaries,
        events=events,
    )
