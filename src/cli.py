from __future__ import annotations

import argparse
import sys

from src.core.checks import CheckEvent, run_check
from src.core.errors import TrackerError
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
        required=True,
        help="Group file name in usergroup/ without .json suffix, for example: example",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Force refresh cache, ignoring update interval.",
    )
    return parser.parse_args(argv)


_EVENT_COLORS = {
    "checking_user": ANSI_YELLOW,
    "cache_hit": ANSI_YELLOW,
    "updating_cache": ANSI_YELLOW,
    "updating_contest_catalog": ANSI_YELLOW,
    "contest_hit": ANSI_RED,
    "contest_miss": ANSI_GREEN,
    "contest_warning": ANSI_YELLOW,
}


def _print_cli_event(event: CheckEvent) -> None:
    """Render one structured event using the CLI's historical colors."""
    color = _EVENT_COLORS.get(event.kind, ANSI_YELLOW)
    print_colored(event.message, color)


def run(argv: list[str] | None = None) -> int:
    """Run the CLI workflow by refreshing caches once and checking each requested contest."""
    args = parse_args(argv)
    run_check(
        args.oj,
        args.group,
        args.contest,
        args.refresh_cache,
        reporter=_print_cli_event,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and translate domain errors into a colored non-zero exit."""
    try:
        return run(argv)
    except TrackerError as exc:
        print_colored(f"error: {exc}", ANSI_RED, file=sys.stderr)
        return 1
