from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, TypeAlias


ContestKey: TypeAlias = str | int
StatusReporter: TypeAlias = Callable[[str, str], None]


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
