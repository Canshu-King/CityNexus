"""ORD-0465 lane stack - prove the front on :4931 is serving THIS lane's bytes and nothing else.

A port answering 200 proves somebody has a server; it does not prove it is mine. Three witnesses are
taken here, each named for what it can actually show:

  1. the entry script named by my own `dist/index.html`, read off disk and then fetched by name;
  2. sha1 over the served bytes equal to sha1 over the bytes on my disk, for the shell and for the
     entry script;
  3. the proxy's own access log, which this front writes (unlike `vite preview`, where that witness
     does not exist and has to be reported as unobtainable).

The process command line is read too, because it is what ties port 4931 to this lane's dist directory.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
DIST = LANE / "dist_004816"
FRONT = "http://127.0.0.1:4931"
LOG = LANE / "run" / "front_4931.log"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def get(path):
    with OPENER.open(FRONT + path, timeout=30) as answer:
        return answer.status, answer.read(), answer.headers.get("Content-Type", "")


def main():
    report = {"front": FRONT, "dist": DIST.as_posix()}
    shell_on_disk = (DIST / "index.html").read_bytes()
    report["witness_1_entry_name_from_my_index"] = bool(
        re.search(rb'assets/index-[A-Za-z0-9_-]+\.js', shell_on_disk)
    )
    entry = re.search(rb'src="(?:\./)?(/assets/index-[A-Za-z0-9_-]+\.js)"', shell_on_disk)
    entry_path = entry.group(1).decode() if entry else None
    report["entry_asset"] = entry_path
    report["entry_exists_on_disk"] = bool(entry_path) and (DIST / entry_path.lstrip("/")).is_file()

    status, served_shell, ctype_shell = get("/")
    disk_entry = (DIST / entry_path.lstrip("/")).read_bytes() if entry_path else b""
    status_entry, served_entry, ctype_entry = get(entry_path or "/__none__")

    report["witness_2_served_matches_disk"] = {
        "index_html": {"served_sha1": sha1(served_shell), "disk_sha1": sha1(shell_on_disk),
                       "equal": sha1(served_shell) == sha1(shell_on_disk),
                       "served_bytes": len(served_shell), "disk_bytes": len(shell_on_disk),
                       "http_status": status, "content_type": ctype_shell},
        "entry_js": {"served_sha1": sha1(served_entry), "disk_sha1": sha1(disk_entry),
                     "equal": sha1(served_entry) == sha1(disk_entry),
                     "served_bytes": len(served_entry), "http_status": status_entry,
                     "content_type": ctype_entry,
                     "served_as_javascript": "javascript" in ctype_entry.lower()},
    }

    # Witness 3: the front's own access log, which this proxy writes when started with --log.
    before = LOG.stat().st_size if LOG.exists() else 0
    get("/v8/shared/ownership-probe-witness-three")
    with io.open(LOG, encoding="utf-8") as handle:
        handle.seek(before)
        tail = handle.read()
    report["witness_3_access_log"] = {
        "log_file": LOG.as_posix(),
        "recorded_my_request": "/v8/shared/ownership-probe-witness-three" in tail,
        "records_added": len([line for line in tail.splitlines() if line.strip()]),
    }

    # Which process holds the port, and does its own command line name this dist and this api port.
    pid = None
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if ":4931" in line and "LISTENING" in line:
            pid = line.split()[-1]
            break
    command = ""
    if pid:
        ps = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True,
        )
        command = (ps.stdout or "").strip()
    report["witness_4_command_line"] = {
        "pid_holding_4931": pid,
        "names_this_dist": DIST.as_posix() in command.replace("\\", "/"),
        "names_api_8731": "--api 8731" in command or "--api" in command and "8731" in command,
        "command_line_len": len(command),
    }

    # The share screen's copy is only on this generation, so a stale front cannot pass for mine.
    marker_zh = "读取成功了，而这一版方案里没有一站".encode("utf-8")
    marker_en = b"The read succeeded and this plan has no stops"
    report["witness_5_generation_marker"] = {
        "in_served_entry_js": marker_zh in served_entry and marker_en in served_entry,
        "note": "both languages of an ORD-0465 sentence, read out of the bytes the port served",
    }

    out_path = LANE / "run" / "ownership_witnesses_r1.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = (
        report["witness_2_served_matches_disk"]["index_html"]["equal"]
        and report["witness_2_served_matches_disk"]["entry_js"]["equal"]
        and report["witness_3_access_log"]["recorded_my_request"]
        and report["witness_4_command_line"]["names_this_dist"]
        and report["witness_5_generation_marker"]["in_served_entry_js"]
    )
    print("WITNESSES_ALL_OK", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
