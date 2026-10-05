"""Identify which process actually burns CPU when a burner is started through the venv python.

Why: `flip_load_proof_r12.py` sampled CPU seconds for the PIDs `subprocess.Popen` returned and got
0.03 s total for six "busy" loops, while the pytest run under them did not slow down at all.  Two
candidate explanations, and they are different facts:
  (a) the venv `python.exe` is a launcher stub, so the Popen PID is not the process doing the work
      (its child is), which would also mean my `kill()` only killed stubs;
  (b) six burners on this machine are simply not load.
Both are read here: process table by PID/parent/command-line, the core count, and a lingering-orbit
sweep for my own burner command line.  Nothing is killed unless its command line contains the exact
burner body this lane wrote.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

MARKER = "sum(range(200000))"
PS = (
    "$rows = @(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
    "Where-Object { $_.CommandLine -like '*range(200000)*' }); "
    "Write-Output ('count=' + $rows.Count); "
    "$rows | ForEach-Object { Write-Output ('pid={0}|ppid={1}|age_s={2}' -f $_.ProcessId, "
    "$_.ParentProcessId, ((Get-Date) - $_.CreationDate).TotalSeconds) }"
)


def main() -> int:
    cores = os.cpu_count()
    print(f"os.cpu_count()={cores}")
    real = subprocess.run([os.sys.executable, "-c",
                           "import sys;print(sys.version.split()[0]);print(sys.executable)"],
                          capture_output=True, text=True).stdout.strip().splitlines()
    print(f"interpreter running this probe: {real}")

    out = subprocess.run(["powershell", "-NoProfile", "-Command", PS],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout.strip().splitlines()
    print(f"lingering burner processes right now: {out}")

    probe = subprocess.Popen([os.sys.executable, "-c",
                              "import time\nt0=time.time()\nwhile time.time()-t0 < 40:\n    " + MARKER])
    stub_pid = probe.pid
    import time
    time.sleep(3.0)
    kids = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"$k = @(Get-CimInstance Win32_Process -Filter 'ParentProcessId={stub_pid}'); "
         "Write-Output ('children_of_stub=' + $k.Count); "
         "$k | ForEach-Object { Write-Output ('pid={0}|name={1}' -f $_.ProcessId, $_.Name) }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip().splitlines()
    print(f"stub pid={stub_pid} -> {kids}")

    cpu = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$rows = @(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -like '*range(200000)*' }); "
         "Write-Output ('n=' + $rows.Count); "
         "$rows | ForEach-Object { $p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
         "if ($p) { Write-Output ('pid={0}|cpu={1:N2}' -f $_.ProcessId, $p.CPU) } }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip().splitlines()
    print(f"CPU seconds per burning pid: {cpu}")

    report = {"cpu_count": cores, "probe_python": real, "stub_pid": stub_pid,
              "children_of_stub": kids, "cpu_by_pid": cpu, "lingering_before": out}
    for line in cpu:
        pid = line.split("|")[0].replace("pid=", "")
        if pid.isdigit():
            try:
                os.kill(int(pid), 9)
            except OSError:
                pass
    if probe.poll() is None:
        probe.kill()
    time.sleep(1.0)
    after = subprocess.run(["powershell", "-NoProfile", "-Command", PS],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace").stdout.strip().splitlines()
    report["lingering_after_cleanup"] = after
    print(f"after cleanup: {after}")
    pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/burner_identity_r13.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("wrote burner_identity_r13.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
