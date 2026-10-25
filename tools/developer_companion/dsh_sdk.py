from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .process_scope import ProcessScope


MAX_FRAME_BYTES = 8 * 1024 * 1024
SERVER_NAME = "deepseek-harness-sdk-runtime"


class DshSdkError(RuntimeError):
    """A bounded, non-secret-bearing DSH SDK transport error."""


class DshSdkProcess:
    """Drive one DSH SDK process over its newline-delimited JSON-RPC protocol."""

    def __init__(
        self,
        *,
        cwd: Path,
        env: Mapping[str, str],
        command: list[str] | None = None,
        notification_sink: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.cwd = cwd.resolve(strict=True)
        if not self.cwd.is_dir():
            raise ValueError("DSH SDK cwd must be a directory")
        if not env:
            raise ValueError("Pass an explicit DSH process environment")
        self.env = dict(env)
        self.command = command or resolve_dsh_command()
        self.notification_sink = notification_sink or (lambda _method, _params: None)
        self._messages: queue.Queue[dict[str, Any] | BaseException | None] = queue.Queue()
        self._write_lock = threading.Lock()
        self._request_id = 0
        self._closed = False
        self._initialized = False
        self._status = "idle"
        self._status_generation = 0
        self._running_generation = 0
        self._idle_generation = 0

        popen_options: dict[str, Any] = {
            "cwd": str(self.cwd),
            "env": self.env,
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "bufsize": 0,
        }
        if os.name == "nt":
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_options["start_new_session"] = True
        self._process = subprocess.Popen(self.command, **popen_options)
        try:
            self._scope = ProcessScope(self._process)
        except OSError as exc:
            self._process.kill()
            self._process.wait(timeout=3)
            raise DshSdkError("Cannot contain DSH executor descendants") from exc
        self._reader = threading.Thread(
            target=self._read_stdout, name="dsh-sdk-stdout", daemon=True
        )
        self._reader.start()

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def status(self) -> str:
        return self._status

    def initialize(
        self,
        *,
        provider: str,
        model: str,
        reasoning_effort: str | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float = 30,
    ) -> dict[str, Any]:
        if self._initialized:
            raise DshSdkError("This DSH process has already been initialized")
        params: dict[str, Any] = {
            "cwd": str(self.cwd),
            "provider": provider,
            "model": model,
        }
        if reasoning_effort:
            params["reasoningEffort"] = reasoning_effort
        if max_tokens is not None:
            if max_tokens < 1:
                raise ValueError("max_tokens must be positive")
            params["maxTokens"] = max_tokens
        result = self._request("initialize", params, timeout_seconds)
        server = result.get("serverInfo") if isinstance(result, dict) else None
        if not isinstance(server, dict) or server.get("name") != SERVER_NAME:
            raise DshSdkError("Unexpected DSH SDK server identity")
        self._initialized = True
        return server

    def run_turn(
        self,
        *,
        session_id: str,
        prompt: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if not self._initialized:
            raise DshSdkError("Initialize DSH before submitting a task")
        if not session_id.strip() or not prompt.strip():
            raise ValueError("session_id and prompt are required")
        baseline_generation = self._status_generation
        deadline = time.monotonic() + timeout_seconds
        receipt = self._request(
            "session/prompt",
            {
                "sessionId": session_id,
                "contentBlocks": [{"type": "text", "text": prompt}],
            },
            min(timeout_seconds, 30),
        )
        message_id = receipt.get("messageId") if isinstance(receipt, dict) else None
        if not isinstance(message_id, str) or not message_id:
            raise DshSdkError("DSH returned no prompt receipt")
        self._wait_for_idle(baseline_generation, max(0.001, deadline - time.monotonic()))
        return {"messageId": message_id, "status": self._status}

    def close(self, *, timeout_seconds: float = 3) -> None:
        if self._closed:
            return
        if self._process.poll() is None and self._initialized:
            try:
                self._request("shutdown", None, timeout_seconds)
            except (DshSdkError, TimeoutError, BrokenPipeError):
                self._terminate_tree()
        elif self._process.poll() is None:
            self._terminate_tree()
        self._closed = True
        try:
            self._process.wait(timeout=max(timeout_seconds, 0.1))
        except subprocess.TimeoutExpired:
            self._terminate_tree()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        if self._process.poll() is None:
            self._terminate_tree()

        self._scope.close()

        for stream in (self._process.stdin, self._process.stdout):
            if stream is not None and not stream.closed:
                stream.close()
        self._reader.join(timeout=1)

    def cancel(self) -> None:
        """Stop this DSH process and its child tools; the protocol has no turn-cancel method."""
        self._terminate_tree()

    def __enter__(self) -> "DshSdkProcess":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request(
        self, method: str, params: dict[str, Any] | None, timeout_seconds: float
    ) -> dict[str, Any]:
        if self._closed or self._process.poll() is not None:
            raise DshSdkError("DSH process is not running")
        self._request_id += 1
        request_id = self._request_id
        frame: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            frame["params"] = params
        payload = (json.dumps(frame, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self._write_lock:
                assert self._process.stdin is not None
                self._process.stdin.write(payload)
                self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise DshSdkError("DSH SDK input closed") from exc

        deadline = time.monotonic() + timeout_seconds
        while True:
            message = self._next_message(deadline)
            if message.get("id") != request_id:
                self._dispatch(message)
                continue
            if "error" in message:
                error = message.get("error")
                code = error.get("code") if isinstance(error, dict) else None
                raise DshSdkError(f"DSH SDK request failed (code {code})")
            result = message.get("result")
            if not isinstance(result, dict):
                raise DshSdkError("DSH SDK returned an invalid result")
            return result

    def _wait_for_idle(self, baseline_generation: int, timeout_seconds: float) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            if (
                self._running_generation > baseline_generation
                and self._idle_generation > self._running_generation
            ):
                return
            self._dispatch(self._next_message(deadline))

    def _next_message(self, deadline: float) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("DSH SDK operation timed out")
        try:
            item = self._messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError("DSH SDK operation timed out") from exc
        if isinstance(item, BaseException):
            raise DshSdkError("DSH SDK output stream failed") from item
        if item is None:
            raise DshSdkError("DSH SDK process exited")
        return item

    def _dispatch(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params")
        if not isinstance(method, str) or not isinstance(params, dict):
            return
        if method == "session.status":
            self._status = params.get("status", self._status)
            self._status_generation += 1
            if self._status == "running":
                self._running_generation = self._status_generation
            elif self._status == "idle":
                self._idle_generation = self._status_generation
        self.notification_sink(method, params)

    def _read_stdout(self) -> None:
        try:
            assert self._process.stdout is not None
            while True:
                raw = self._process.stdout.readline(MAX_FRAME_BYTES + 1)
                if not raw:
                    self._messages.put(None)
                    return
                if len(raw) > MAX_FRAME_BYTES:
                    self._messages.put(DshSdkError("DSH SDK frame exceeded the size limit"))
                    self._terminate_tree()
                    return
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(message, dict):
                    self._messages.put(message)
        except BaseException as exc:
            self._messages.put(exc)

    def _terminate_tree(self) -> None:
        self._scope.kill()

def resolve_dsh_command() -> list[str]:
    """Resolve the installed DSH launcher without embedding a user-specific path."""
    override = os.environ.get("CITYNEXUS_DSH_BIN")
    if override:
        path = Path(override).expanduser()
        if path.suffix.lower() in {".js", ".mjs", ".cjs"}:
            node = shutil.which("node")
            if not node:
                raise DshSdkError("Node.js is required to launch the configured DSH bundle")
            return [node, str(path.resolve(strict=True)), "--profile", "sdk"]
        return [str(path.resolve(strict=True)), "--profile", "sdk"]

    launcher = shutil.which("dsh") or shutil.which("dsh.cmd")
    if launcher:
        return [launcher, "--profile", "sdk"]

    node = shutil.which("node")
    package_bin = (
        Path.home()
        / ".dsh"
        / "profiles"
        / "node_modules"
        / "@deepseek-ai"
        / "dsh"
        / "lib"
        / "bin.js"
    )
    if node and package_bin.is_file():
        return [node, str(package_bin), "--profile", "sdk"]
    raise DshSdkError(
        "DSH is not installed on PATH; set CITYNEXUS_DSH_BIN to the installed launcher"
    )
