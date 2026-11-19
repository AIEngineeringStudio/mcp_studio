import json

from mcp_lab.wire.recorder import JsonlWireRecorder
from mcp_lab.wire.redaction import REDACTED, redact


def test_redact_nested_secrets():
    value = {"authorization": "Bearer secret", "nested": {"api_key": "abc", "safe": 7}}
    assert redact(value) == {
        "authorization": REDACTED,
        "nested": {"api_key": REDACTED, "safe": 7},
    }


def test_recorder_writes_one_redacted_json_object_per_line(tmp_path):
    path = tmp_path / "wire.jsonl"
    recorder = JsonlWireRecorder(path)
    recorder.record(
        direction="client_to_server",
        vantage_point="test",
        transport="stdio",
        payload={"jsonrpc": "2.0", "params": {"password": "do-not-log"}},
    )

    lines = path.read_text().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["payload"]["params"]["password"] == REDACTED
