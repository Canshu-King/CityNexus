from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

from tools.developer_companion.dsh_sdk import DshSdkProcess, SERVER_NAME


SERVER = r"""
import json
import sys
for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        result = {"serverInfo": {"name": "deepseek-harness-sdk-runtime", "version": "0.0.1"}}
        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
    elif method == "session/prompt":
        session_id = request["params"]["sessionId"]
        print(json.dumps({"jsonrpc": "2.0", "method": "session.status", "params": {"sessionId": session_id, "status": "running"}}), flush=True)
        print(json.dumps({"jsonrpc": "2.0", "method": "session.event", "params": {"sessionId": session_id, "event": {"type": "assistant/message"}}}), flush=True)
        print(json.dumps({"jsonrpc": "2.0", "method": "session.status", "params": {"sessionId": session_id, "status": "idle"}}), flush=True)
        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": {"messageId": "msg-1"}}), flush=True)
    elif method == "shutdown":
        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": {}}), flush=True)
        break
"""


class DshSdkProcessTests(unittest.TestCase):
    def make_process(self, events: list[tuple[str, dict]]) -> DshSdkProcess:
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONUTF8": "1"}
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
        return DshSdkProcess(
            cwd=Path.cwd(),
            env=env,
            command=[sys.executable, "-u", "-c", SERVER],
            notification_sink=lambda method, params: events.append((method, params)),
        )

    def test_handshake_prompt_events_and_shutdown(self) -> None:
        events: list[tuple[str, dict]] = []
        with self.make_process(events) as client:
            server = client.initialize(provider="deepseek-official", model="deepseek-v4-flash")
            self.assertEqual(server["name"], SERVER_NAME)
            receipt = client.run_turn(session_id="task-1", prompt="Inspect the failing test.", timeout_seconds=2)
            self.assertEqual(receipt, {"messageId": "msg-1", "status": "idle"})
        self.assertEqual(
            [method for method, _params in events],
            ["session.status", "session.event", "session.status"],
        )

    def test_prompt_requires_initialization(self) -> None:
        events: list[tuple[str, dict]] = []
        with self.make_process(events) as client:
            with self.assertRaisesRegex(RuntimeError, "Initialize DSH"):
                client.run_turn(session_id="task-1", prompt="run", timeout_seconds=1)


if __name__ == "__main__":
    unittest.main()
