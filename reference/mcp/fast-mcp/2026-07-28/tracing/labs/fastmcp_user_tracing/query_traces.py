"""Query the client/server JSONL files by session, connection, exchange, RPC ID.

A JSON-RPC ID is unique only within its relevant request scope. Use a session
and exchange/connection filter when identical IDs can occur in multiple runs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def matching_records(directory: Path, *, session: str | None = None,
                     exchange: str | None = None,
                     connection: str | None = None,
                     rpc: str | None = None) -> list[dict[str, Any]]:
    found = []
    for path in directory.glob("*.jsonl"):
        with path.open(encoding="utf-8") as source:
            for line in source:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue  # ignore incomplete final line from abrupt termination
                if not isinstance(item, dict):
                    continue
                if session and item.get("trace_session_id") != session:
                    continue
                if exchange and item.get("http_exchange_id") != exchange:
                    continue
                if connection and item.get("stdio_connection_id") != connection:
                    continue
                if rpc is not None and str(item.get("rpc_id")) != rpc:
                    continue
                found.append(item)
    return sorted(found, key=lambda item: item.get("timestamp", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("trace-logs"))
    parser.add_argument("--session")
    parser.add_argument("--exchange", help="HTTP exchange ID")
    parser.add_argument("--connection", help="STDIO subprocess connection ID")
    parser.add_argument("--rpc-id", help="JSON-RPC ID (scope using --session)")
    parser.add_argument("--json", action="store_true", help="print complete records")
    args = parser.parse_args()
    rows = matching_records(args.directory, session=args.session,
                            exchange=args.exchange, connection=args.connection,
                            rpc=args.rpc_id)
    # Responses omit `method`. Resolve using all request records first; this
    # works even when clocks differ slightly between client/server processes.
    methods: dict[tuple, str] = {}
    for item in rows:
        if item.get("rpc_method"):
            key = (item.get("trace_session_id"), item.get("http_exchange_id"),
                   item.get("stdio_connection_id"), item.get("rpc_id"))
            methods[key] = str(item["rpc_method"])
    for item in rows:
        if args.json:
            print(json.dumps(item, ensure_ascii=False, default=str))
            continue
        key = (item.get("trace_session_id"), item.get("http_exchange_id"),
               item.get("stdio_connection_id"), item.get("rpc_id"))
        method = item.get("rpc_method") or methods.get(key, "-")
        print(f"{item.get('timestamp', '-')} "
              f"{item.get('side', '-'):6} {item.get('direction', '-'):5} "
              f"{item.get('transport', '-'):8} "
              f"id={str(item.get('rpc_id')):5} "
              f"{str(method):24} {item.get('event', '-'):<17} "
              f"session={item.get('trace_session_id')} "
              f"exchange={item.get('http_exchange_id')} "
              f"connection={item.get('stdio_connection_id')}")
    if not rows:
        print("No matching trace records")


if __name__ == "__main__":
    main()
