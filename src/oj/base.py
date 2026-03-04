from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeAlias


ContestKey: TypeAlias = str | int


class OJAdapter(ABC):
    """Base interface for each OJ adapter."""

    name: str

    @abstractmethod
    def validate_contest(self, contest: str) -> ContestKey:
        """Validate contest argument and normalize its type."""

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
