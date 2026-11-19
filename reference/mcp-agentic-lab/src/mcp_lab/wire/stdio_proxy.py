"""Transparent stdio subprocess proxy that records raw JSON-RPC lines."""

import argparse
import asyncio
import contextlib
import os
import signal
import sys
from pathlib import Path

from mcp_lab.wire.recorder import JsonlWireRecorder


async def _forward(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    recorder: JsonlWireRecorder,
    direction: str,
    max_bytes: int,
    close_writer: bool,
) -> None:
    while line := await reader.readline():
        recorder.record_json_line(
            line,
            direction=direction,
            vantage_point="stdio_proxy",
            transport="stdio",
            max_bytes=max_bytes,
        )
        writer.write(line)
        await writer.drain()
    if close_writer:
        with contextlib.suppress(BrokenPipeError, ConnectionResetError, NotImplementedError):
            writer.close()
            await writer.wait_closed()


async def run_proxy(command: list[str], output: Path, max_bytes: int) -> int:
    if not command:
        raise ValueError("A child command is required after --")
    recorder = JsonlWireRecorder(output)
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
        start_new_session=os.name != "nt",
    )
    assert process.stdin is not None
    assert process.stdout is not None
    loop = asyncio.get_running_loop()
    client_reader = asyncio.StreamReader()
    await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(client_reader), sys.stdin.buffer
    )
    stdout_transport, stdout_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout.buffer
    )
    client_writer = asyncio.StreamWriter(stdout_transport, stdout_protocol, None, loop)

    try:
        await asyncio.gather(
            _forward(
                client_reader,
                process.stdin,
                recorder=recorder,
                direction="client_to_server",
                max_bytes=max_bytes,
                close_writer=True,
            ),
            _forward(
                process.stdout,
                client_writer,
                recorder=recorder,
                direction="server_to_client",
                max_bytes=max_bytes,
                close_writer=False,
            ),
        )
        return await process.wait()
    finally:
        if process.returncode is None:
            if os.name != "nt":
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("var/wire.jsonl"))
    parser.add_argument("--max-bytes", type=int, default=65_536)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    raise SystemExit(asyncio.run(run_proxy(command, args.output, args.max_bytes)))


if __name__ == "__main__":
    main()
