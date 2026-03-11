from __future__ import annotations

from typing import TextIO

ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_BLUE = "\033[34m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Wrap a text line with an ANSI color code and trailing reset sequence."""
    return f"{color}{text}{ANSI_RESET}"


def print_colored(text: str, color: str, *, file: TextIO | None = None) -> None:
    """Print a single colored line to stdout or a provided stream."""
    print(colorize(text, color), file=file, flush=True)
