from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, TypeAlias

from src.core import cache, tracker
from src.core.groups import load_group_users
from src.oj.base import ContestKey, TargetContestSelection
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
    warning_contests: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable event payload without unused fields."""
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(slots=True)
class ContestWarningSummary:
    """Describe one warning-only same-round match for a contest result."""

    user_id: str
    warning_contests: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable warning summary."""
        return asdict(self)


@dataclass(slots=True)
class ContestCheckSummary:
    """Summarize which users matched one expanded contest."""

    contest_id: str
    matched_users: list[str]
    warnings: list[ContestWarningSummary]
    status: str = "checked"
    contest_type: str | None = None
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable contest summary."""
        return {
            "contest_id": self.contest_id,
            "matched_users": list(self.matched_users),
            "warnings": [warning.to_dict() for warning in self.warnings],
            "status": self.status,
            "contest_type": self.contest_type,
            "skip_reason": self.skip_reason,
        }


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


def _select_target_contests(
    target_contests: list[ContestKey],
    adapter: Any,
    contest_types: list[str] | None,
) -> list[TargetContestSelection]:
    """Return the checked-or-skipped contest selections for one run."""
    select_target_contests = getattr(adapter, "select_target_contests", None)
    if select_target_contests is None:
        return [TargetContestSelection(contest=contest) for contest in target_contests]
    return select_target_contests(target_contests, selected_contest_types=contest_types)


def run_check(
    oj: str,
    group: str,
    contest_tokens: list[str],
    refresh_cache: bool,
    *,
    contest_types: list[str] | None = None,
    reporter: EventReporter | None = None,
) -> CheckRunResult:
    """Run one structured check so CLI and web can share the same workflow."""
    adapter = get_adapter(oj)
    target_contests = _expand_target_contests(contest_tokens, adapter)
    users = load_group_users(group, oj)
    events: list[CheckEvent] = []
    contest_summaries: list[ContestCheckSummary] = []
    user_caches: dict[str, dict[str, Any]] = {}
    total_users = len(users)

    def emit(event: CheckEvent) -> None:
        """Record an event locally and forward it to an optional reporter."""
        events.append(event)
        if reporter is not None:
            reporter(event)

    def on_prepare_status(kind: str, message: str) -> None:
        """Translate adapter-level preparation status callbacks into structured events."""
        emit(CheckEvent(kind=kind, message=message))

    cache.ensure_cache_dir_exists(adapter.name)
    adapter.prepare_run(refresh_cache, status_callback=on_prepare_status)
    contest_selections = _select_target_contests(target_contests, adapter, contest_types)
    checked_target_contests = [
        selection.contest for selection in contest_selections if selection.status == "checked"
    ]

    if checked_target_contests:
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

    for contest_selection in contest_selections:
        contest_label = str(contest_selection.contest)
        if contest_selection.status == "skipped":
            skip_reason = contest_selection.skip_reason or "contest was skipped"
            emit(
                CheckEvent(
                    kind="contest_skipped",
                    message=f"skip {contest_label}: {skip_reason}",
                    contest_id=contest_label,
                )
            )
            contest_summaries.append(
                ContestCheckSummary(
                    contest_id=contest_label,
                    matched_users=[],
                    warnings=[],
                    status="skipped",
                    contest_type=contest_selection.contest_type,
                    skip_reason=skip_reason,
                )
            )
            continue

        matched_users: list[str] = []
        warning_summaries: list[ContestWarningSummary] = []

        for user_id in users:
            submissions = user_caches[user_id]["submissions"]
            if tracker.cache_has_done_contest(adapter, submissions, contest_selection.contest):
                matched_users.append(user_id)
                emit(
                    CheckEvent(
                        kind="contest_hit",
                        message=f"{user_id} done {contest_label}",
                        user_id=user_id,
                        contest_id=contest_label,
                    )
                )
                continue

            warning_contests = [
                str(contest)
                for contest in adapter.find_warning_matches(submissions, contest_selection.contest)
            ]
            if not warning_contests:
                continue

            warning_summaries.append(
                ContestWarningSummary(
                    user_id=user_id,
                    warning_contests=warning_contests,
                )
            )

        if not matched_users:
            emit(
                CheckEvent(
                    kind="contest_miss",
                    message=f"no users have done {contest_label}",
                    contest_id=contest_label,
                )
            )

        for warning_summary in warning_summaries:
            warning_label = ", ".join(warning_summary.warning_contests)
            contest_noun = "contest" if len(warning_summary.warning_contests) == 1 else "contests"
            emit(
                CheckEvent(
                    kind="contest_warning",
                    message=(
                        f"warning: {warning_summary.user_id} may have done {contest_label} "
                        f"via same-round {contest_noun} {warning_label}"
                    ),
                    user_id=warning_summary.user_id,
                    contest_id=contest_label,
                    warning_contests=list(warning_summary.warning_contests),
                )
            )

        contest_summaries.append(
            ContestCheckSummary(
                contest_id=contest_label,
                matched_users=matched_users,
                warnings=warning_summaries,
                contest_type=contest_selection.contest_type,
            )
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
