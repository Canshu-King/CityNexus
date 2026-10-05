"""Prove the load leg of shape D with a direct reading, not with wall-clock inference.

Last generation (head `4d43f8bc`) the paired numbers happened to show a slowdown, and I wrote that the
burner leg "was not vacuous" because of it.  This generation the same runs came out
loaded = 3.08 s / 2.92 s against idle 2.94-4.14 s, i.e. no measurable slowdown -- so wall-clock is not
proof of anything.  A load arm needs the load itself measured: CPU seconds consumed by the exact PIDs I
started, sampled twice across the run, then those PIDs killed and nobody else's.

Writes nothing to the tree.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import time

PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
BACKEND = TREE / "backend"
M197 = "tests/test_qoder_ord197_four_class_receipt.py"
BURN_CODE = ("import time\n"
             "t0=time.time()\n"
             "while time.time()-t0 < 60:\n"
             "    sum(range(200000))\n")


def cpu_seconds(pids: list[int]) -> tuple[float, float]:
    """Cumulative user+system seconds for exactly these pids, read from the process table."""
    listing = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$pid_list = @(" + ",".join(str(p) for p in pids) + ");"
         "$rows = Get-Process -Id $pid_list -ErrorAction SilentlyContinue;"
         "$n = @($rows).Count;"
         "$s = ($rows | Measure-Object -Property CPU -Sum).Sum;"
         "if ($null -eq $s) { $s = 0 };"
         "Write-Output (\"n={0}|cpu={1:N2}\" -f $n, $s)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    m = re.search(r"n=(\d+)\|cpu=([\d.,]*)", listing.replace(",", ""))
    if not m:
        raise RuntimeError(f"could not parse process table: {listing!r}")
    return int(m.group(1)), float(m.group(2))


def main() -> int:
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    idle = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", M197],
                          cwd=str(BACKEND), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    idle_tail = [l for l in (idle.stdout + idle.stderr).splitlines()
                 if re.search(r"\d+ (passed|failed)", l)]
    print(f"tree HEAD={head}")
    print(f"{'IDLE module run':<18} exit={idle.returncode} tail={idle_tail[-1].strip('= ') if idle_tail else '(none)'}")

    procs = [subprocess.Popen([PY, "-c", BURN_CODE]) for _ in range(6)]
    pids = [p.pid for p in procs]
    time.sleep(2.0)
    n0, cpu0 = cpu_seconds(pids)
    t0 = time.perf_counter()
    loaded = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--tb=line",
                             "-rf", M197], cwd=str(BACKEND), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    wall = round(time.perf_counter() - t0, 2)
    n1, cpu1 = cpu_seconds(pids)
    loaded_tail = [l for l in (loaded.stdout + loaded.stderr).splitlines()
                   if re.search(r"\d+ (passed|failed)", l)]
    for p in procs:
        p.kill()
    time.sleep(0.5)
    n_after, _ = cpu_seconds(pids)

    grew = cpu1 - cpu0
    report = {"head": head, "burner_pids": pids, "pids_alive_before": n0, "pids_alive_after": n1,
              "cpu_before": cpu0, "cpu_after_sample": cpu1, "cpu_grew_during_run": round(grew, 2),
              "loaded_wall_s": wall, "loaded_exit": loaded.returncode,
              "loaded_tail": loaded_tail[-1].strip("= ") if loaded_tail else "(none)",
              "idle_tail": idle_tail[-1].strip("= ") if idle_tail else "(none)",
              "pids_still_listed_after_kill": n_after}
    print(f"{'LOADED module run':<18} exit={loaded.returncode} wall={wall}s "
          f"tail={report['loaded_tail']}")
    print(f"{'BURNER CPU':<18} pids_alive={n0}->{n1} cpu_seconds {cpu0:.2f} -> {cpu1:.2f} "
          f"(grew {grew:.2f} s over the {wall}s run)")
    print(f"{'AFTER kill':<18} pids still listed={n_after}")
    verdict = ("LOAD_REAL" if grew > 1.0 and loaded.returncode == 0 and n_after == 0
               else "LOAD_NOT_PROVEN")
    report["verdict"] = verdict
    print("VERDICT", verdict)
    pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/flip_load_proof_r12.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("wrote flip_load_proof_r12.json")
    return 0 if verdict == "LOAD_REAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
