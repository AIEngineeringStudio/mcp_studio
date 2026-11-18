"""Start the calendar auth lab and verify discovery, visibility, and denial."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastmcp import Client


HOST = "127.0.0.1"
PORT = 8780
MCP_URL = f"http://{HOST}:{PORT}/mcp"
METADATA_URL = (
    f"http://{HOST}:{PORT}/.well-known/oauth-protected-resource/mcp"
)


def assert_port_free() -> None:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        if probe.connect_ex((HOST, PORT)) == 0:
            raise RuntimeError(f"Port {PORT} is already in use; refusing to stop it")


def wait_for_metadata(process: subprocess.Popen[str]) -> dict:
    for _ in range(80):
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(
                f"Calendar auth server exited before startup:\n{stderr}"
            )
        try:
            with urlopen(METADATA_URL, timeout=0.25) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("Calendar auth server did not become ready")


def verify_unauthenticated_challenge() -> None:
    request = Request(
        MCP_URL,
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urlopen(request, timeout=2)
    except HTTPError as error:
        assert error.code == 401, error.code
        challenge = error.headers.get("WWW-Authenticate", "")
        assert "resource_metadata=" in challenge, challenge
        return
    raise AssertionError("Unauthenticated MCP request unexpectedly succeeded")


async def tool_names(token: str) -> set[str]:
    async with Client(MCP_URL, auth=token, mode="2026-07-28") as client:
        return {tool.name for tool in await client.list_tools()}


def unpack_structured_data(data: Any) -> Any:
    """Turn SDK-generated output models back into ordinary Python values."""

    if hasattr(data, "result"):
        return data.result
    if hasattr(data, "root"):
        return data.root
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data


async def verify_scoped_catalog_and_calls() -> None:
    reader_tools = await tool_names("mcp-alice-read")
    assert reader_tools == {"list_calendar_events"}, reader_tools

    writer_tools = await tool_names("mcp-alice-write")
    assert writer_tools == {
        "list_calendar_events",
        "create_calendar_event",
    }, writer_tools

    async with Client(
        MCP_URL,
        auth="mcp-bob-read",
        mode="2026-07-28",
    ) as bob:
        bob_result = await bob.call_tool("list_calendar_events")
        bob_events = unpack_structured_data(bob_result.data)
        assert {event["id"] for event in bob_events} == {"E-200"}, bob_events

    async with Client(
        MCP_URL,
        auth="mcp-alice-read",
        mode="2026-07-28",
    ) as reader:
        result = await reader.call_tool("list_calendar_events")
        events = unpack_structured_data(result.data)
        assert events[0]["id"] == "E-100", events

        denied = await reader.call_tool(
            "create_calendar_event",
            {
                "title": "Unauthorized write",
                "start": "2026-11-21T09:00:00-07:00",
            },
            raise_on_error=False,
        )
        assert denied.is_error
        assert "Unknown tool" in denied.content[0].text

    async with Client(
        MCP_URL,
        auth="mcp-alice-write",
        mode="2026-07-28",
    ) as writer:
        created = await writer.call_tool(
            "create_calendar_event",
            {
                "title": "Design review",
                "start": "2026-11-21T09:00:00-07:00",
            },
        )
        created_event = unpack_structured_data(created.data)
        assert created_event["title"] == "Design review", created_event


def main() -> None:
    assert_port_free()
    server_path = Path(__file__).with_name("auth_calendar_server.py")
    process = subprocess.Popen(
        [sys.executable, str(server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        metadata = wait_for_metadata(process)
        assert metadata["resource"] == MCP_URL, metadata
        assert metadata["authorization_servers"] == [
            "https://login.example.test"
        ], metadata
        assert metadata["scopes_supported"] == ["calendar:read"], metadata
        verify_unauthenticated_challenge()
        asyncio.run(verify_scoped_catalog_and_calls())
        print(
            "calendar auth: discovery, private tool visibility, direct-call "
            "denial, user isolation, and mock downstream delegation passed"
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
