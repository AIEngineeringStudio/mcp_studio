"""Run one of the MCP Apps lesson servers."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Sequence

from mcp_apps_learning.registry import (
    LESSONS,
    load_server,
    project_root,
    server_file,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or inspect an MCP server from one of the lessons.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser(
        "run",
        help="Run a lesson server.",
    )
    run_parser.add_argument(
        "lesson",
        nargs="?",
        default="hello",
        choices=LESSONS,
        help="Lesson server to run (default: hello).",
    )
    run_parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="streamable-http",
        help="MCP transport to use (default: streamable-http).",
    )

    dev_parser = commands.add_parser(
        "dev",
        help="Open a lesson server in MCP Inspector.",
    )
    dev_parser.add_argument(
        "lesson",
        nargs="?",
        default="hello",
        choices=LESSONS,
        help="Lesson server to inspect (default: hello).",
    )
    return parser.parse_args(argv)


def run_dev(lesson: str) -> None:
    """Launch MCP Inspector for a registered lesson."""
    mcp_command = shutil.which("mcp")
    if mcp_command is None:
        raise RuntimeError("The MCP CLI is not installed in this environment.")

    result = subprocess.run(
        [
            mcp_command,
            "dev",
            str(server_file(lesson)),
            "--with-editable",
            str(project_root(lesson)),
        ],
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "dev":
        run_dev(args.lesson)
        return

    load_server(args.lesson).run(transport=args.transport)
