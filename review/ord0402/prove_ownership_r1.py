"""ORD-0402 -- patch the stack receipt so the ownership proof names the parent, not just the port.

Why: `.venv/Scripts/python.exe` is a redirector into the uv-managed CPython, so the pid this script
starts is the *parent* of the pid that holds the port. `pid == netstat pid` is therefore the wrong
equality for this launcher; the true statement is "the listener's parent is the handle I started",
which is what this records. Both are printed, because a proof that quietly changed shape is worse than
a proof that shows the old one failing.
"""
import json
import subprocess
import sys
from pathlib import Path

LANE = Path("D:/moodle/_qoder_q_ord0402")
RECEIPT = LANE / "stack_receipt_r1.json"
PIDFILE = LANE / "uvicorn_8714.pid"
PORT = 8714


def ps(script: str) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout.strip()


def listener_pid() -> str | None:
    raw = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in raw.splitlines():
        if f"127.0.0.1:{PORT}" in line and "LISTENING" in line:
            return line.split()[-1]
    return None


def field(pid: str, name: str) -> str:
    return ps("(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(int(pid)) + "\")." + name)


def main() -> int:
    started = PIDFILE.read_text(encoding="utf-8").strip() if PIDFILE.exists() else None
    on_port = listener_pid()
    if not on_port:
        print("no listener on", PORT)
        return 1
    parent = field(on_port, "ParentProcessId")
    d = json.loads(RECEIPT.read_text(encoding="utf-8"))
    d["ownership_proof"] = {
        "started_by_this_script_pid": started,
        "netstat_pid_on_port": on_port,
        "listener_equals_started_pid": started == on_port,
        "parent_of_listener": parent,
        "parent_of_listener_equals_started_pid": parent == started,
        "listener_command_line": field(on_port, "CommandLine")[:200],
        "why_the_two_differ": ".venv/Scripts/python.exe is a redirector into the uv-managed CPython, "
                              "so the started pid is the parent of the listening pid.",
        "db_file": d.get("db_file"),
        "db_file_bytes": d.get("db_file_bytes"),
    }
    d["ownership_proof"]["accepted_proof"] = (
        d["ownership_proof"]["parent_of_listener_equals_started_pid"]
        and "trash_door_assembly_r1" in d["ownership_proof"]["listener_command_line"]
    )
    RECEIPT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(d["ownership_proof"], ensure_ascii=False, indent=2))
    return 0 if d["ownership_proof"]["accepted_proof"] else 1


if __name__ == "__main__":
    sys.exit(main())
