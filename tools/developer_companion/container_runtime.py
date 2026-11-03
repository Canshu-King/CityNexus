"""Networkless, non-root DSH worker; its only model transport is a file mailbox.

The host broker owns the upstream credential. Neither Docker argv, container env,
mounts, nor SDK notifications contain it. Images must be built explicitly first.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.parse
import uuid
from dataclasses import dataclass
from pathlib import Path

from .dsh_sdk import DshSdkProcess

MAX_REQUEST = 8 * 1024 * 1024
MAX_RESPONSE = 24 * 1024 * 1024


class IsolationUnavailable(RuntimeError):
    """Only a stable error code is safe for progress output."""


@dataclass(frozen=True)
class ContainerConfig:
    image: str
    endpoint: str
    key_file: Path
    model: str

    def validate(self, checkout: Path) -> None:
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", self.image):
            raise IsolationUnavailable("CONTAINER_IMAGE_DIGEST_REQUIRED")
        url = urllib.parse.urlsplit(self.endpoint)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise IsolationUnavailable("BROKER_ENDPOINT_INVALID")
        if url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise IsolationUnavailable("BROKER_LOOPBACK_ENDPOINT_REQUIRED")
        if url.path.rstrip("/") != "/v1":
            raise IsolationUnavailable("BROKER_ENDPOINT_V1_REQUIRED")
        if self.model != "cn:deepseek-v4.1-flash":
            raise IsolationUnavailable("CONTAINER_IMAGE_MODEL_UNSUPPORTED")
        key = self.key_file.resolve(strict=True)
        if key.is_relative_to(checkout.resolve()):
            raise IsolationUnavailable("BROKER_KEY_INSIDE_WORKSPACE")


def _docker(*args: str, timeout: float = 15) -> str:
    binary = shutil.which("docker")
    if not binary:
        raise IsolationUnavailable("CONTAINER_ENGINE_MISSING")
    try:
        result = subprocess.run([binary, *args], capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        raise IsolationUnavailable("CONTAINER_ENGINE_UNAVAILABLE") from None
    if result.returncode:
        raise IsolationUnavailable("CONTAINER_ENGINE_UNAVAILABLE")
    return result.stdout.decode("utf-8", errors="replace").strip()


def worker_command(image: str, checkout: Path, mailbox: Path, name: str, *command: str, writable: bool = True) -> list[str]:
    """Fixed boundary, no shell interpolation or caller-supplied Docker options."""
    metadata = checkout.parent / "repository.git"
    for path in (checkout, mailbox, metadata):
        if "," in str(path) or path.is_symlink():
            raise IsolationUnavailable("CONTAINER_MOUNT_INVALID")
    return [shutil.which("docker") or "docker", "run", "--rm", "--interactive", "--name", name,
            "--pull=never", "--network=none", "--read-only", "--user", "10001:10001",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=256",
            "--memory=2g", "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m,uid=10001,gid=10001",
            "--mount", f"type=bind,source={checkout},target=/workspace" + ("" if writable else ",readonly"),
            "--mount", f"type=bind,source={checkout / '.git'},target=/workspace/.git,readonly",
            "--mount", f"type=bind,source={metadata},target=/taskgit,readonly",
            "--mount", f"type=bind,source={mailbox},target=/mailbox",
            "--workdir", "/workspace", image, *command]


def _read_plain_file(path: Path, limit: int) -> bytes:
    """Open a flat mailbox entry without following a container-created symlink."""
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        # OPEN_REPARSE_POINT: inspect the opened object, never its target.
        handle = kernel.CreateFileW(str(path), 0x80000000, 1 | 2 | 4, None, 3, 0x00200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise OSError("Mailbox entry unavailable")
        class AttributeTag(ctypes.Structure):
            _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]
        attr = AttributeTag()
        if not kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(attr), ctypes.sizeof(attr)) or attr.attributes & (0x400 | 0x10):
            kernel.CloseHandle(handle)
            raise OSError("Mailbox reparse point refused")
        descriptor = msvcrt.open_osfhandle(int(handle), os.O_RDONLY | os.O_BINARY)
    else:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        import stat
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise OSError("Mailbox entry is not a regular file")
    with os.fdopen(descriptor, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Mailbox entry too large")
    return data


class ModelMailboxBroker:
    """One task's fixed-model Chat Completions capability; no arbitrary URLs."""
    def __init__(self, directory: Path, config: ContainerConfig):
        if importlib.util.find_spec("httpx") is None:
            raise IsolationUnavailable("BROKER_HTTPX_REQUIRED")
        self.directory, self.config = directory, config
        self.directory.mkdir(mode=0o700, exist_ok=True)
        # The real key is held only by this trusted host process.
        key = _read_plain_file(config.key_file.resolve(strict=True), 16384).decode("utf-8").strip()
        if not key or any(c.isspace() for c in key):
            raise IsolationUnavailable("BROKER_RAW_KEY_FILE_REQUIRED")
        self._key = key
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._seen: set[str] = set()
        self.requests = self.failures = 0
        self._request_loop = None
        self._request_future = None
        self._request_lock = threading.Lock()

    def start(self):
        self._thread.start()

    def dispatch(self, value: dict) -> dict:
        if not isinstance(value, dict) or set(value) != {"method", "path", "body"} or value["method"] != "POST" or value["path"] != "/v1/chat/completions":
            raise ValueError("BROKER_ROUTE_DENIED")
        body = value["body"]
        if not isinstance(body, dict) or body.get("model") != self.config.model or not isinstance(body.get("messages"), list):
            raise ValueError("BROKER_MODEL_DENIED")
        fields = {"model", "messages", "tools", "tool_choice", "parallel_tool_calls", "stream", "stream_options",
                  "max_tokens", "max_completion_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty",
                  "stop", "seed", "reasoning_effort", "thinking", "response_format", "reasoning", "metadata", "store"}
        if set(body) - fields:
            raise ValueError("BROKER_FIELDS_DENIED")
        # Never accept client headers, credentials, a URL or a routed redirect.
        payload = json.dumps(body).encode("utf-8")
        if len(payload) > MAX_REQUEST:
            raise ValueError("BROKER_REQUEST_TOO_LARGE")
        loop = asyncio.new_event_loop()
        request = loop.create_task(self._forward(payload))
        with self._request_lock:
            if self._stop.is_set():
                request.cancel()
            self._request_loop, self._request_future = loop, request
        self.requests += 1
        try:
            return loop.run_until_complete(request)
        except asyncio.CancelledError:
            self.failures += 1
            return self._failure("BROKER_CANCELLED")
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            with self._request_lock:
                self._request_loop = self._request_future = None
            loop.close()

    @staticmethod
    def _failure(code):
        return {"status": 502, "content_type": "application/json", "body_base64": base64.b64encode(json.dumps({"error":{"code":code}}).encode()).decode()}

    async def _forward(self, payload):
        # Cancellation closes the live HTTP operation, including a streaming
        # response whose body has not arrived. The host requires its existing
        # CityNexus httpx dependency; no worker-side upstream credential exists.
        import httpx
        try:
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=30) as client:
                async with client.stream("POST", self.config.endpoint.rstrip("/") + "/chat/completions", content=payload,
                                         headers={"Authorization":"Bearer " + self._key,"Content-Type":"application/json"}) as response:
                    if not 200 <= response.status_code < 300:
                        raise ValueError("BROKER_UPSTREAM_STATUS")
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE:
                            raise ValueError("BROKER_RESPONSE_TOO_LARGE")
                        chunks.append(chunk)
                    return {"status":response.status_code,"content_type":response.headers.get("Content-Type","application/json"),
                            "body_base64":base64.b64encode(b"".join(chunks)).decode()}
        except (httpx.HTTPError, OSError, ValueError):
            self.failures += 1
            return self._failure("BROKER_UPSTREAM_UNAVAILABLE")

    def _serve(self):
        while not self._stop.wait(0.04):
            for path in self.directory.glob("req-*.json"):
                if not re.fullmatch(r"req-[a-f0-9]{32}\.json", path.name) or path.name in self._seen:
                    continue
                self._seen.add(path.name)
                try:
                    result = self.dispatch(json.loads(_read_plain_file(path, MAX_REQUEST)))
                except (OSError, ValueError, TypeError):
                    self.failures += 1
                    result = {"status": 400, "content_type": "application/json", "body_base64": base64.b64encode(b'{"error":{"code":"BROKER_REQUEST_DENIED"}}').decode()}
                target = self.directory / path.name.replace("req-", "res-", 1)
                if self._stop.is_set():
                    return
                temporary = self.directory / (uuid.uuid4().hex + ".tmp")
                with temporary.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream)
                os.replace(temporary, target)

    def close(self):
        self._stop.set()
        with self._request_lock:
            loop, request = self._request_loop, self._request_future
        if loop is not None and request is not None:
            try:
                loop.call_soon_threadsafe(request.cancel)
            except RuntimeError:
                pass  # the request completed concurrently
        if self._thread.is_alive():
            self._thread.join(timeout=31)
        self._key = ""


def prepare_container(checkout: Path, task_dir: Path, config: ContainerConfig) -> dict:
    if checkout.resolve().parent != task_dir.resolve():
        raise IsolationUnavailable("CONTAINER_CHECKOUT_NOT_TASK_OWNED")
    config.validate(checkout)
    _docker("info", "--format", "{{.ServerVersion}}")
    try:
        metadata = json.loads(_docker("image", "inspect", config.image))[0]
    except (ValueError, IndexError):
        raise IsolationUnavailable("CONTAINER_IMAGE_INVALID") from None
    if metadata.get("Config", {}).get("User") != "10001:10001":
        raise IsolationUnavailable("CONTAINER_IMAGE_USER_INVALID")
    for parent, directories, files in os.walk(checkout, followlinks=False):
        for path in [Path(parent), *(Path(parent) / name for name in directories + files)]:
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                raise IsolationUnavailable("CONTAINER_SOURCE_REPARSE_POINT_REFUSED")
            if os.name != "nt":
                # Only this disposable tree, beneath the private task directory.
                # UID 10001 must write it without elevating the container user.
                path.chmod(path.stat().st_mode | 0o022)
    mailbox = task_dir / "container-mailbox"
    mailbox.mkdir(mode=0o700, exist_ok=True)
    os.chmod(mailbox, 0o777)  # non-root container owns only this disposable capability directory
    # Host-only sentinel is deliberately outside both mounted directories.
    sentinel = task_dir / ("host-read-canary-" + uuid.uuid4().hex)
    sentinel.write_bytes(os.urandom(32))
    host_relative = str(sentinel.resolve()).replace("\\", "/")
    drive = host_relative[:1].lower()
    tail = host_relative[2:] if host_relative[1:3] == ":/" else host_relative
    forbidden_paths = ["/var/run/docker.sock", "/root/.ssh/id_rsa", str(sentinel.resolve()),
                       "/run/desktop/mnt/host/" + drive + tail, "/mnt/" + drive + tail]
    probe = """import json,os,sys,socket
paths=json.loads(sys.argv[1])
results={}
for p in paths:
 try:
  with open(p,'rb') as f: f.read(1)
  results[p]='READABLE'
 except (OSError,ValueError): results[p]='DENIED_OR_ABSENT'
try:
 open('/outside-task-write','w').write('escape'); writable=True
except OSError: writable=False
s=socket.socket(); s.settimeout(1)
try: connected=s.connect_ex(('192.0.2.1',443))==0
except OSError: connected=False
finally: s.close()
print(json.dumps({'uid':os.getuid(),'forbidden_reads':results,'root_write_succeeded':writable,'external_network_connected':connected}))
"""
    probe_name = "cn51-probe-" + uuid.uuid4().hex[:12]
    command = worker_command(config.image, checkout, mailbox, probe_name, "python3", "-c", probe, json.dumps(forbidden_paths), writable=False)
    try:
        result = subprocess.run(command, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        observed = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        try:
            _docker("container", "stop", "--time", "3", probe_name, timeout=10)
        except IsolationUnavailable:
            pass
        raise IsolationUnavailable("CONTAINER_BOUNDARY_PROBE_FAILED") from None
    if result.returncode or observed.get("uid") != 10001 or observed.get("root_write_succeeded") is not False or observed.get("external_network_connected") is not False or any(v != "DENIED_OR_ABSENT" for v in observed.get("forbidden_reads", {}).values()) or len(observed.get("forbidden_reads", {})) != 5:
        raise IsolationUnavailable("CONTAINER_BOUNDARY_PROBE_FAILED")
    return {"evidence": "CONTAINER_PROCESS_READ_PROBE", "image": config.image, "observed": observed,
            "mounts": ["task checkout", "task .git pointer read-only", "private task Git read-only", "credential-free mailbox"], "network": "none",
            "host_canary_sha256": hashlib.sha256(sentinel.read_bytes()).hexdigest()}


class ContainerDshSdkProcess(DshSdkProcess):
    def __init__(self, *, cwd, task_dir, config, notification_sink):
        self.container_name = "cn51-dsh-" + uuid.uuid4().hex[:16]
        self.cleanup_error = None
        self._container_stopped = False
        self._container_lock = threading.Lock()
        self.broker = ModelMailboxBroker(task_dir / "container-mailbox", config)
        self.broker.start()
        env_names = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "USERPROFILE", "COMSPEC", "PATHEXT"}
        host_env = {key: value for key, value in os.environ.items() if key.upper() in env_names}
        command = worker_command(config.image, cwd, task_dir / "container-mailbox", self.container_name, "node", "/opt/companion/container_entry.mjs")
        try:
            super().__init__(cwd=cwd, env=host_env, command=command, notification_sink=notification_sink, protocol_cwd="/workspace")
        except Exception:
            self.broker.close()
            raise

    def initialize(self, *, provider, **kwargs):
        return super().initialize(provider="companion-broker", **kwargs)

    def cancel(self):
        try:
            self._stop_container()
        finally:
            super().cancel()

    def _stop_container(self):
        with self._container_lock:
            if self._container_stopped:
                return
            try:
                _docker("container", "stop", "--time", "3", self.container_name, timeout=10)
            except IsolationUnavailable:
                pass  # --rm may already have removed a normally exited worker
            try:
                state = _docker("container", "ls", "--all", "--filter", "name=^/" + self.container_name + "$", "--format", "{{.State}}", timeout=5)
                self._container_stopped = not state or state == "exited"
            except IsolationUnavailable:
                self._container_stopped = False
            self.cleanup_error = None if self._container_stopped else "CONTAINER_STOP_NOT_CONFIRMED"

    def close(self):
        if not self._closed:
            try:
                super().close()
            finally:
                self._stop_container()
                self.broker.close()
