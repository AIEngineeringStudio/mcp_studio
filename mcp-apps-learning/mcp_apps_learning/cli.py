"""Run one of the MCP Apps lesson servers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mcp_apps_learning.registry import LESSONS, load_server


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an MCP server from one of the lessons.",
    )
    parser.add_argument(
        "lesson",
        nargs="?",
        default="hello",
        choices=LESSONS,
        help="Lesson server to run (default: hello).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="streamable-http",
        help="MCP transport to use (default: streamable-http).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    load_server(args.lesson).run(transport=args.transport)
