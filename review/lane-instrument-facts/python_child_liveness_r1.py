"""A liveness ruler that reads the process actually doing the work.

Why this exists (measured this session, not assumed): starting a component through
`D:/moodle/CityNexus/.venv/Scripts/python.exe` gives `Popen` a PID that is a **launcher stub**. In the
reading behind this file the stub held 0.00 CPU-seconds while its child -- also `python.exe` -- held
4.48. So any keeper/watchdog that judges liveness or kills by the PID `Popen` returned is talking to the
shell, not the worker: it can report "running" when the worker died, and report "stopped" while the
worker keeps burning.

Four legs, because a one-sided ruler is itself an instrument defect:
  L1 positive  -- start a component through the venv python: the ruler must find a child, and its CPU
                  seconds must grow between two samples while the launched PID stays at zero.
  L2 the kill  -- kill the launched (stub) PID: measured three-for-three here, the worker goes down
                  WITH it.  That refuted this lane's earlier claim that a stub kill leaves the worker
                  running, so this leg is kept as the counter-reading, not as a passing test.
  L3 non-blind -- after the worker is gone the ruler must read it gone.
  L4 the trap  -- kill ONLY the worker (what a command-line sweep does): if the stub stays in the table
                  and `Popen.poll()` still answers "running", a poll()-based keeper is blind to it.

Read-only against the repository; it starts and stops only the processes this file itself started.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time

VENV_PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BURN = ("import time\n"
        "t0=time.time()\n"
        "while time.time()-t0 < 40:\n"
        "    sum(range(120000))\n")
OUT = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/python_child_liveness_r1.json")


def ps(command: str) -> str:
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"powershell rc={proc.returncode}: {proc.stderr[:200]}")
    return proc.stdout.strip()


def children(pid: int) -> list[int]:
    out = ps("$c = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=" + str(pid) + "\"); "
             "foreach ($x in $c) { Write-Output $x.ProcessId }")
    return [int(l) for l in out.splitlines() if l.strip().isdigit()]


def process_state(pid: int) -> str:
    """Tri-state: SEEN (still in the table), GONE (never was / already reaped), or ERROR."""
    out = ps("$p = @(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(pid) + "\"); "
             "Write-Output $p.Count").strip()
    return "SEEN" if out == "1" else ("GONE" if out == "0" else "UNEXPECTED:" + out)


def cpu_seconds(pid: int) -> float:
    out = ps("$p = Get-Process -Id " + str(pid) + " -ErrorAction SilentlyContinue; "
             "if ($null -eq $p) { Write-Output 'absent' } else { Write-Output $p.CPU }").strip()
    if not out or out == "absent":
        return 0.0
    return float(out.splitlines()[-1])


def command_line(pid: int) -> str:
    """The recorded command line, flattened and with the account segment elided here rather than in a
    later transcript: a `-c` payload carries real newlines, and the interpreter path under AppData
    contains the machine account name, which no reader needs while the version and payload do."""
    out = ps("$p = @(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(pid) + "\"); "
             "if ($p.Count -eq 0) { Write-Output 'absent' } else { Write-Output $p[0].CommandLine }")
    flat = " ".join(out.split())
    return re.sub(r"Users[\\/]+[^\\/]+", "Users/<账号段省略>", flat)[:150]


def resolve(pid: int) -> dict:
    """The worker behind a venv launch: the child if there is one, otherwise the PID itself."""
    kids = children(pid)
    worker = kids[0] if kids else pid
    return {"launched_pid": pid, "launched_state": process_state(pid),
            "children": kids, "worker": worker,
            "worker_is_child": bool(kids),
            "launched_command_line": command_line(pid)[:90],
            "worker_command_line": command_line(worker)[:90]}


def sample(pid: int, wait: float = 2.0) -> dict:
    r = resolve(pid)
    worker = r["worker"]
    cpu_a = cpu_seconds(worker)
    stub_a = cpu_seconds(r["launched_pid"])
    time.sleep(wait)
    cpu_b = cpu_seconds(worker)
    stub_b = cpu_seconds(r["launched_pid"])
    r.update({"worker_cpu_first": cpu_a, "worker_cpu_second": cpu_b,
              "worker_cpu_grew": round(cpu_b - cpu_a, 2),
              "stub_cpu_first": stub_a, "stub_cpu_second": stub_b,
              "stub_cpu_grew": round(stub_b - stub_a, 2),
              "worker_state": process_state(worker)})
    return r


def kill(pid: int) -> None:
    try:
        os.kill(pid, 9)
    except OSError as exc:
        print(f"  (kill {pid}: {exc})")


def main() -> int:
    report: dict = {"venv_python": VENV_PY, "legs": {}}

    proc = subprocess.Popen([VENV_PY, "-c", BURN])
    stub = proc.pid
    print(f"L1 start worker through the venv python: stub pid={stub}")
    time.sleep(1.5)
    l1 = sample(stub)
    l1_ok = l1["worker_is_child"] and l1["worker_cpu_grew"] > 0.0 and l1["worker_state"] == "SEEN"
    report["legs"]["L1_positive"] = {"ok": l1_ok, **l1}
    print(f"   resolve: worker={l1['worker']} (child of stub: {l1['worker_is_child']}) "
          f"worker_cpu_grew={l1['worker_cpu_grew']}s stub_cpu_grew={l1['stub_cpu_grew']}s "
          f"=> {'OK' if l1_ok else 'NOT_OK'}")
    print(f"   launched command line: {l1['launched_command_line']}")
    print(f"   worker   command line: {l1['worker_command_line']}")

    print("\nL2 kill ONLY the stub (what a PID-based keeper believes is a stop)")
    kill(stub)
    time.sleep(1.5)
    stub_now = process_state(stub)
    worker_pid = l1["worker"]
    state = process_state(worker_pid)
    grew = cpu_seconds(worker_pid)
    time.sleep(1.5)
    grew2 = cpu_seconds(worker_pid)
    l2_ok = state == "SEEN" and grew2 - grew > 0.0
    report["legs"]["L2_stub_killed_worker_alive"] = {
        "ok": l2_ok, "stub_state_after_kill": stub_now, "worker_state": state,
        "worker_cpu_before": round(grew, 2), "worker_cpu_after": round(grew2, 2),
        "worker_cpu_grew": round(grew2 - grew, 2)}
    print(f"   stub state={stub_now}; worker pid={worker_pid} state={state} cpu {grew:.2f} -> {grew2:.2f} "
          f"=> {'ALIVE AND WORKING (the trap is real)' if l2_ok else 'NOT_REPRODUCED'}")

    print("\nL3 now kill the worker too, and the ruler must read it gone")
    kill(worker_pid)
    time.sleep(1.5)
    final = process_state(worker_pid)
    l3_ok = final == "GONE"
    report["legs"]["L3_worker_killed_reads_gone"] = {"ok": l3_ok, "worker_state": final}
    print(f"   worker state={final} => {'OK' if l3_ok else 'NOT_OK (one-sided ruler)'}")

    # L4 is the leg that actually bites a poll()-based keeper: the worker dies, the shell stays up.
    print("\nL4 fresh component, kill ONLY the worker (what a command-line sweep does)")
    proc2 = subprocess.Popen([VENV_PY, "-c", BURN])
    time.sleep(1.5)
    s4 = resolve(proc2.pid)
    worker4 = s4["worker"]
    kill(worker4)
    time.sleep(1.5)
    stub4_state = process_state(proc2.pid)
    worker4_state = process_state(worker4)
    poll_val = proc2.poll()
    l4_trap = stub4_state == "SEEN" and worker4_state == "GONE"
    report["legs"]["L4_worker_dead_stub_alive"] = {
        "trap_real": l4_trap, "stub_state": stub4_state, "worker_state": worker4_state,
        "popen_poll": poll_val, "stub_pid": proc2.pid, "worker_pid": worker4}
    print(f"   stub pid={proc2.pid} state={stub4_state}; worker pid={worker4} state={worker4_state}; "
          f"Popen.poll()={poll_val}")
    print(f"   => {'TRAP: the launcher still answers poll() as running while the worker is gone' if l4_trap else 'no trap on this leg'}")
    if proc2.poll() is None:
        proc2.kill()

    if proc.poll() is None:
        proc.kill()
    vocab = {"SEEN", "GONE"}
    states = [l1["worker_state"], final, stub4_state, worker4_state]
    readings = {"L1": l1_ok, "L2_worker_died_with_stub": not l2_ok, "L3": l3_ok, "L4_trap": l4_trap}
    report["readings"] = readings
    report["states_seen"] = states
    all_read = all(s in vocab for s in states) and l1["worker"] is not None
    print("\nreadings:", json.dumps(readings, ensure_ascii=False), "| states:", states)
    print("VERDICT", "ALL_FOUR_LEGS_READ" if all_read else "SOME_LEG_UNREAD")
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    return 0 if all_read else 1


if __name__ == "__main__":
    raise SystemExit(main())
