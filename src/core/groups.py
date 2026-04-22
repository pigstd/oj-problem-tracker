from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeAlias

from src.core.errors import TrackerError
from src.oj.registry import available_oj_names


GROUP_ROOT = Path("usergroup")
GroupUsersByOJ: TypeAlias = dict[str, list[str]]


def _format_group_source(source: str | Path) -> str:
    """Return a readable source label for group validation errors."""
    return str(source)


def validate_group_users_payload(
    data: Any,
    *,
    source: str | Path = "group payload",
) -> GroupUsersByOJ:
    """Validate one group payload regardless of whether it came from disk or memory."""
    source_label = _format_group_source(source)
    if not isinstance(data, dict):
        raise TrackerError(f"invalid group format in {source_label}: root must be an object")

    users_by_oj: GroupUsersByOJ = {}
    for oj in available_oj_names():
        users = data.get(oj)
        if users is None:
            raise TrackerError(f"invalid group format in {source_label}: missing '{oj}' field")
        if not isinstance(users, list):
            raise TrackerError(f"invalid group format in {source_label}: '{oj}' must be a list")

        normalized_users: list[str] = []
        for user in users:
            if not isinstance(user, str) or not user.strip():
                raise TrackerError(
                    f"invalid group format in {source_label}: every '{oj}' user must be a non-empty string"
                )
            normalized_users.append(user.strip())
        users_by_oj[oj] = normalized_users

    return users_by_oj


def _require_non_empty_oj_users(
    users_by_oj: GroupUsersByOJ,
    oj: str,
    *,
    source: str | Path,
) -> list[str]:
    """Return one OJ's users and reject empty lists for the selected OJ."""
    users = users_by_oj[oj]
    if not users:
        raise TrackerError(
            f"invalid group format in {_format_group_source(source)}: '{oj}' must not be empty"
        )
    return list(users)


def get_group_file_path(group_name: str) -> Path:
    """Return the JSON file path for a named user group."""
    return GROUP_ROOT / f"{group_name}.json"


def load_group(group_name: str) -> dict[str, list[str]]:
    """Load and validate a full group definition from disk."""
    group_file = get_group_file_path(group_name)
    if not group_file.exists():
        raise TrackerError(f"group file not found: {group_file}")

    try:
        with group_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise TrackerError(f"invalid JSON in group file {group_file}: {exc}") from exc
    except OSError as exc:
        raise TrackerError(f"cannot read group file {group_file}: {exc}") from exc

    return validate_group_users_payload(data, source=group_file)


def get_group_users_for_oj(
    group_users_by_oj: GroupUsersByOJ,
    oj: str,
    *,
    source: str | Path = "group payload",
) -> list[str]:
    """Validate one in-memory group payload and return the selected OJ users."""
    users_by_oj = validate_group_users_payload(group_users_by_oj, source=source)
    return _require_non_empty_oj_users(users_by_oj, oj, source=source)


def load_group_users(group_name: str, oj: str) -> list[str]:
    """Load and validate the selected OJ user list from a group file."""
    users_by_oj = load_group(group_name)
    return _require_non_empty_oj_users(users_by_oj, oj, source=get_group_file_path(group_name))


def get_group_detail(group_name: str) -> dict[str, Any]:
    """Return one group's full user lists plus per-OJ counts for the web UI."""
    users_by_oj = load_group(group_name)
    return {
        "name": group_name,
        "users": {oj: list(users_by_oj[oj]) for oj in available_oj_names()},
        "counts": {oj: len(users_by_oj[oj]) for oj in available_oj_names()},
    }


def list_group_summaries() -> tuple[list[dict[str, Any]], list[str]]:
    """Return valid group summaries plus validation errors for invalid group files."""
    summaries: list[dict[str, Any]] = []
    errors: list[str] = []

    if not GROUP_ROOT.exists():
        return summaries, errors

    for group_file in sorted(GROUP_ROOT.glob("*.json")):
        group_name = group_file.stem
        try:
            detail = get_group_detail(group_name)
        except TrackerError as exc:
            errors.append(str(exc))
            continue

        summaries.append(
            {
                "name": detail["name"],
                "counts": dict(detail["counts"]),
            }
        )

    return summaries, errors
