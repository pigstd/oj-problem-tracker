from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.errors import TrackerError
from src.oj.registry import available_oj_names


GROUP_ROOT = Path("usergroup")


def _validate_group_users(data: Any, group_file: Path) -> dict[str, list[str]]:
    """Validate the per-OJ user lists loaded from a group JSON file."""
    if not isinstance(data, dict):
        raise TrackerError(f"invalid group format in {group_file}: root must be an object")

    users_by_oj: dict[str, list[str]] = {}
    for oj in available_oj_names():
        users = data.get(oj)
        if users is None:
            raise TrackerError(f"invalid group format in {group_file}: missing '{oj}' field")
        if not isinstance(users, list):
            raise TrackerError(f"invalid group format in {group_file}: '{oj}' must be a list")
        if not all(isinstance(user, str) and user.strip() for user in users):
            raise TrackerError(
                f"invalid group format in {group_file}: every '{oj}' user must be a non-empty string"
            )
        users_by_oj[oj] = users

    return users_by_oj


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

    return _validate_group_users(data, group_file)


def load_group_users(group_name: str, oj: str) -> list[str]:
    """Load and validate the selected OJ user list from a group file."""
    users_by_oj = load_group(group_name)
    users = users_by_oj[oj]
    if not users:
        raise TrackerError(
            f"invalid group format in {get_group_file_path(group_name)}: '{oj}' must not be empty"
        )
    return users


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
