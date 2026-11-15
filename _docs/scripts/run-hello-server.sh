#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"

exec uv run --project "$PROJECT_DIR" --locked python \
    "$PROJECT_DIR/register_tool_MCP_App_resource/server.py" "$@"
