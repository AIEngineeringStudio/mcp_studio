#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"

exec uv run --project "$PROJECT_DIR" --locked python \
    "$PROJECT_DIR/structured_data_from_tool/customer_server.py" "$@"
