"""Re-measure the ord197 flip family on the generation that carries the fix.

Background (this lane's own ruling, block `5a53846b_...` for CMDR 02:04 裁语②): the two arms
`test_r3_...` / `test_r4_...` asserted conclusion fields without waiting for the operation to close, so
before the fix the red rate on one clean tree ranged from 0/12 to 8/8 depending on nothing but worker
timing.  The fix added the module's own `_wait_closed` call to both arms.  A single green run is not
evidence that a race is gone, so this instrument repeats the four shapes that used to disagree:

  A  the module alone, 6 runs
  B  the pairing that used to turn both arms red (`test_v6_predictive_real_city.py` first), 3 runs
  C  only r3/r4 selected by `-k`, no partner, 3 runs
  D  the module alone under my own CPU load (6 burner children), 2 runs

Every row records the exact tail summary, the ORD-0211 database header line, the FAILED node names and
the `--tb=line` reason joined by position (r7's correction).  The verdict counts reds from the parsed
rows; nothing here is written into the tree.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import time

PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
BACKEND = TREE / "backend"
M197 = "tests/test_qoder_ord197_four_class_receipt.py"
MPRED = "tests/test_v6_predictive_real_city.py"
R3 = "test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage"
R4 = "test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match"
BURNERS = 6


def pytest(args: list[str]) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--tb=line",
                           "-rf", *args], cwd=str(BACKEND), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    secs = round(time.perf_counter() - t0, 2)
    out = proc.stdout + proc.stderr
    lines = out.splitlines()
    tb = [l.strip() for l in lines if re.match(r"^[A-Za-z]:\\.*\.py:\d+:", l)]
    failed = [l for l in lines if l.startswith("FAILED")]
    header = [l for l in lines if "test database" in l]
    summary = [l for l in lines if re.search(r"\d+ (passed|failed|error)", l)]
    nodes = [f.split(" - ")[0].split("::")[-1] for f in failed]
    return {"exit": proc.returncode, "secs": secs,
            "summary": summary[-1].strip("= ") if summary else "(no summary line)",
            "db": header[0] if header else "(header not printed)",
            "n_red": len(failed),
            "reds": [{"node": n, "reason": tb[i] if i < len(tb) else "<no tb line>"}
                     for i, n in enumerate(nodes)]}


def burners() -> list[int]:
    """Start BURNERS busy children and return their pids; the caller kills exactly these pids."""
    code = ("import time\n"
            "t0=time.time()\n"
            "while time.time()-t0 < 75:\n"
            "    sum(range(200000))\n")
    pids = [subprocess.Popen([PY, "-c", code]).pid for _ in range(BURNERS)]
    time.sleep(2.0)
    return pids


def main() -> int:
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip().splitlines()
    print(f"tree HEAD={head} | dirty lines={len(dirty)}")
    report = {"head": head, "shapes": {}}
    total_runs = total_red = 0
    idle_secs: list[float] = []

    shapes = [
        ("A alone x6", [[M197]] * 6),
        ("B paired x3", [[MPRED, M197]] * 3),
        ("C r3+r4 only x3", [[M197, "-k", f"{R3} or {R4}"]] * 3),
    ]
    for label, arg_sets in shapes:
        reds = 0
        secs = []
        for i, args in enumerate(arg_sets, 1):
            r = pytest(args)
            reds += r["n_red"]
            total_runs += 1
            total_red += r["n_red"]
            secs.append(r["secs"])
            if label.startswith("A"):
                idle_secs.append(r["secs"])
            print(f"{label:<16} try{i}: {r['summary']:<44} exit={r['exit']} wall={r['secs']}s")
            for row in r["reds"]:
                print(f"    RED {row['node'][:60]}")
                print(f"        {row['reason'][:150]}")
            if i == 1:
                report["shapes"][label] = {"first": r, "runs": len(arg_sets), "red_nodes": 0}
        report["shapes"][label]["red_nodes"] = reds
        report["shapes"][label]["wall_secs"] = secs
        print(f"{label:<16} => red nodes {reds} over {len(arg_sets)} runs | wall {secs}\n")

    pids = burners()
    try:
        reds = 0
        secs = []
        for i in (1, 2):
            r = pytest([M197])
            reds += r["n_red"]
            total_runs += 1
            total_red += r["n_red"]
            secs.append(r["secs"])
            print(f"{'D loaded x2':<16} try{i}: {r['summary']:<44} exit={r['exit']} wall={r['secs']}s")
            for row in r["reds"]:
                print(f"    RED {row['node'][:60]}")
                print(f"        {row['reason'][:150]}")
        loaded_secs = secs[:]
        report["shapes"]["D loaded x2"] = {"runs": 2, "red_nodes": reds, "wall_secs": secs}
        print(f"{'D loaded x2':<16} => red nodes {reds} over 2 runs (burner pids {pids})")
    finally:
        for pid in pids:
            try:
                os.kill(pid, 9)
            except OSError:
                pass

    db = pytest([M197, "--collect-only"])["db"]
    report["db_header_sample"] = db
    report["total_runs"] = total_runs
    report["total_red_nodes"] = total_red
    report["idle_wall_secs"] = idle_secs
    report["loaded_wall_secs"] = loaded_secs
    print(f"\ntotal: {total_red} red nodes over {total_runs} runs")
    print(f"load calibration, same module alone: idle wall {idle_secs} vs loaded wall "
          f"{loaded_secs} (this pair is what shows the burner leg was not vacuous)")
    print(f"db header sample: {db[:170]}")
    pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/ord197_flip_tip_r11.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("wrote ord197_flip_tip_r11.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
