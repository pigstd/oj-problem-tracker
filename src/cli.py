from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.checks import CheckEvent, run_check
from src.core.errors import TrackerError
from src.core.groups import GroupUsersByOJ, validate_group_users_payload
from src.oj.cf import normalize_selected_contest_types
from src.oj.registry import available_oj_names
from src.output import ANSI_GREEN, ANSI_RED, ANSI_RESET, ANSI_YELLOW, print_colored


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for OJ, contests, group, and cache refresh behavior."""
    parser = argparse.ArgumentParser(
        description="Check whether users in a group have submissions in one or more target contests."
    )
    parser.add_argument(
        "--oj",
        required=True,
        choices=available_oj_names(),
        help="Online judge to query",
    )
    parser.add_argument(
        "-c",
        "--contest",
        required=True,
        nargs="+",
        help="One or more contest IDs or inclusive contest ranges to check",
    )
    parser.add_argument(
        "-g",
        "--group",
        help="Group file name in usergroup/ without .json suffix, for example: example",
    )
    parser.add_argument(
        "--group-json-file",
        help="Read group users from an arbitrary JSON file instead of usergroup/",
    )
    parser.add_argument(
        "--group-json",
        help="Read group users from an inline JSON string",
    )
    parser.add_argument(
        "--group-name",
        help="Display label for inline group inputs; defaults to inline or the JSON file stem",
    )
    parser.add_argument(
        "--atcoder-user",
        nargs="+",
        help="AtCoder users for inline group input",
    )
    parser.add_argument(
        "--cf-user",
        nargs="+",
        help="Codeforces users for inline group input",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Force refresh cache, ignoring update interval.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="CF contest types to check: all, div1, div2, div1+2, div3, div4, others",
    )
    return parser.parse_args(argv)


_EVENT_COLORS = {
    "checking_user": ANSI_YELLOW,
    "cache_hit": ANSI_YELLOW,
    "updating_cache": ANSI_YELLOW,
    "updating_contest_catalog": ANSI_YELLOW,
    "contest_catalog_warning": ANSI_YELLOW,
    "contest_skipped": ANSI_YELLOW,
    "contest_hit": ANSI_RED,
    "contest_miss": ANSI_GREEN,
    "contest_warning": ANSI_YELLOW,
}


def _print_cli_event(event: CheckEvent) -> None:
    """Render one structured event using the CLI's historical colors."""
    color = _EVENT_COLORS.get(event.kind, ANSI_YELLOW)
    print_colored(event.message, color)


def _has_inline_user_args(args: argparse.Namespace) -> bool:
    """Return whether the CLI request uses explicit per-OJ user arguments."""
    return args.atcoder_user is not None or args.cf_user is not None


def _load_group_json_source(raw_json: str, *, source: str | Path) -> GroupUsersByOJ:
    """Parse and validate one JSON-backed group payload."""
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise TrackerError(f"invalid JSON in {source}: {exc}") from exc
    return validate_group_users_payload(payload, source=source)


def _resolve_inline_group_name(args: argparse.Namespace) -> str:
    """Return the display label used for non-file-backed group inputs."""
    if args.group_name is not None and args.group_name.strip():
        return args.group_name.strip()
    if args.group_json_file:
        file_path = Path(args.group_json_file)
        return file_path.stem or "inline"
    return "inline"


def _resolve_group_input(args: argparse.Namespace) -> tuple[str, GroupUsersByOJ | None]:
    """Choose exactly one group input source and normalize its payload when needed."""
    using_inline_users = _has_inline_user_args(args)
    selected_sources = sum(
        bool(source)
        for source in (
            args.group,
            args.group_json_file,
            args.group_json,
            using_inline_users,
        )
    )
    if selected_sources != 1:
        raise TrackerError(
            "choose exactly one group input mode: --group, --group-json-file, --group-json, "
            "or inline --atcoder-user/--cf-user arguments"
        )

    if args.group is not None:
        return args.group, None

    if args.group_json_file is not None:
        group_file = Path(args.group_json_file)
        try:
            raw_json = group_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise TrackerError(f"cannot read group JSON file {group_file}: {exc}") from exc
        return _resolve_inline_group_name(args), _load_group_json_source(
            raw_json,
            source=group_file,
        )

    if args.group_json is not None:
        return _resolve_inline_group_name(args), _load_group_json_source(
            args.group_json,
            source="--group-json",
        )

    group_users = {
        "atcoder": list(args.atcoder_user or []),
        "cf": list(args.cf_user or []),
    }
    return _resolve_inline_group_name(args), validate_group_users_payload(
        group_users,
        source="CLI user arguments",
    )


def run(argv: list[str] | None = None) -> int:
    """Run the CLI workflow by refreshing caches once and checking each requested contest."""
    args = parse_args(argv)
    contest_types = normalize_selected_contest_types(args.oj, args.only)
    group_name, group_users_by_oj = _resolve_group_input(args)
    run_kwargs = {
        "contest_types": contest_types,
        "reporter": _print_cli_event,
    }
    if group_users_by_oj is not None:
        run_kwargs["group_users_by_oj"] = group_users_by_oj
    run_check(
        args.oj,
        group_name,
        args.contest,
        args.refresh_cache,
        **run_kwargs,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and translate domain errors into a colored non-zero exit."""
    try:
        return run(argv)
    except TrackerError as exc:
        print_colored(f"error: {exc}", ANSI_RED, file=sys.stderr)
        return 1
