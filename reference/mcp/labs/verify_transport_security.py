"""Verify allowed and rejected Host/Origin combinations over loopback HTTP."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = 8781
URL = f"http://{HOST}:{PORT}/mcp"
BODY = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "server/discover",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    }
).encode()


def listening() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex((HOST, PORT)) == 0


def send(host: str, origin: str | None) -> int:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": host,
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "server/discover",
    }
    if origin is not None:
        headers["Origin"] = origin
    request = Request(URL, data=BODY, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=3) as response:
            response.read()
            return response.status
    except HTTPError as error:
        error.read()
        return error.code


def main() -> None:
    if listening():
        raise SystemExit(f"Port {PORT} is already in use; stop that service first")
    server = Path(__file__).with_name("transport_security_server.py")
    process = subprocess.Popen(
        [sys.executable, str(server)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 20
        while not listening():
            if process.poll() is not None:
                raise RuntimeError(process.stderr.read())
            if time.monotonic() > deadline:
                raise TimeoutError("Security server did not start in 20 seconds")
            time.sleep(0.1)

        assert send(f"{HOST}:{PORT}", "https://trusted.example") == 200
        assert send("attacker.example", "https://trusted.example") == 421
        assert send(f"{HOST}:{PORT}", "https://evil.example") == 403
        assert send(f"{HOST}:{PORT}", None) == 200
        print("allowed Host + trusted Origin -> 200")
        print("untrusted Host -> 421")
        print("untrusted Origin -> 403")
        print("allowed Host + absent Origin -> 200 (not authentication)")
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


if __name__ == "__main__":
    main()
