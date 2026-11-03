from __future__ import annotations

import os
import re
from pathlib import Path

from .dsh_sdk import resolve_dsh_command


def redact(value: str) -> str:
    value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redacted]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[redacted]", value)
    value = re.sub(r"(?i)(api[_-]?key|access[_-]?token|secret|password)(\s*[:=]\s*)[^\s,;]+", r"\1\2[redacted]", value)
    value = re.sub(r"(?i)([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)[A-Z0-9_]*)(\s*=\s*)(?:\"[^\"]*\"|'[^']*'|[^\s;,]+)", r"\1\2[redacted]", value)
    value = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", value)
    return value


def dsh_runtime(checkout: Path, task_dir: Path) -> tuple[list[str], dict[str, str]]:
    """Use DSH's credential seam; never copy credential values into argv or files."""
    runtime = task_dir / "runtime"
    runtime.mkdir(mode=0o700, exist_ok=True)
    patch = runtime / "profile.yml"
    patch.write_text("""- id: session-telemetry-otel
  disabled: true
- id: tool-web
  disabled: true
- id: tool-subagent-fork
  disabled: true
- id: tool-ralph
  disabled: true
- id: sandbox-policy
  config:
    mode: workspace-write
    workspaceRoot: !!js process.env.CITYNEXUS_DSH_WORKSPACE_ROOT
- id: session-persistence-jsonl
  config:
    root: !!js process.env.CITYNEXUS_DSH_SESSION_ROOT
- id: storage-json
  config:
    root: !!js process.env.CITYNEXUS_DSH_STORAGE_ROOT
- id: shell-env
  config:
    dshHome: !!js process.env.CITYNEXUS_DSH_SHELL_HOME
""", encoding="utf-8")
    empty_git_config = runtime / "empty.gitconfig"
    empty_git_config.touch(mode=0o600, exist_ok=True)
    names = {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA",
        "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "PROGRAMFILES", "PROGRAMFILES(X86)",
        "COMSPEC", "PATHEXT",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in names}
    env.update({
        "DSH_HOME": str(Path(os.environ.get("DSH_HOME", str(Path.home() / ".dsh"))).resolve()),
        "DSH_PERMISSION_MODE": "workspace-write",
        "DSH_TELEMETRY_DISABLED": "1",
        "DSH_MAX_TOKENS_AS_SUCCESS": "false",
        "PYTHONUTF8": "1",
        "CITYNEXUS_DSH_WORKSPACE_ROOT": str(task_dir),
        "CITYNEXUS_DSH_SESSION_ROOT": str(runtime / "sessions"),
        "CITYNEXUS_DSH_STORAGE_ROOT": str(runtime / "storage"),
        "CITYNEXUS_DSH_SHELL_HOME": str(checkout / ".developer-companion" / "shell-home"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(empty_git_config),
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "Never",
    })
    return resolve_dsh_command() + ["--patch", str(patch)], env
