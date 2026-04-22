from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeAlias


ContestKey: TypeAlias = str | int
StatusReporter: TypeAlias = Callable[[str, str], None]


@dataclass(slots=True)
class TargetContestSelection:
    """Describe whether one expanded contest should be checked or skipped."""

    contest: ContestKey
    status: str = "checked"
    contest_type: str | None = None
    skip_reason: str | None = None


class OJAdapter(ABC):
    """Base interface for each OJ adapter."""

    name: str

    def prepare_run(
        self,
        refresh_cache: bool,
        *,
        status_callback: StatusReporter | None = None,
    ) -> None:
        """Prepare adapter-level state once before a check run starts."""
        del refresh_cache
        del status_callback

    @abstractmethod
    def validate_contest(self, contest: str) -> ContestKey:
        """Validate a single contest ID and normalize its type."""

    @abstractmethod
    def expand_contest_token(self, token: str) -> list[ContestKey]:
        """Expand one CLI contest token into normalized contest IDs."""

    @abstractmethod
    def validate_cache_fields(self, cache_data: dict[str, Any], cache_file: Path) -> None:
        """Validate OJ-specific fields in cache data."""

    @abstractmethod
    def update_submissions(
        self,
        user_id: str,
        existing_cache: dict[str, Any] | None,
        refresh_cache: bool,
    ) -> dict[str, Any]:
        """Return updated submission payload for cache writing."""

    @abstractmethod
    def submission_matches_contest(self, submission: Any, contest: ContestKey) -> bool:
        """Check whether a submission belongs to target contest."""

    def find_warning_matches(self, submissions: list[Any], contest: ContestKey) -> list[ContestKey]:
        """Return alternative contest IDs that should produce warning-only matches."""
        del submissions
        del contest
        return []

    def select_target_contests(
        self,
        contests: list[ContestKey],
        *,
        selected_contest_types: list[str] | None = None,
    ) -> list[TargetContestSelection]:
        """Return checked-or-skipped selections for the expanded target contest list."""
        del selected_contest_types
        return [TargetContestSelection(contest=contest) for contest in contests]
