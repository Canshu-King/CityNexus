"""Run the three backend test files that my landing gate's collection arm has been naming as
error_lines, against the CURRENT authoritative tip -- in its own export, its own interpreter.

Why: the landing gate prints `whole_suite.error_lines` but refuses nothing for them, because a
collection *error* on a candidate that touches no backend file cannot be attributed to it.  That is
correct gate behaviour and a bad commander habit at the same time: three named test files have been
riding along as noise since ORD-0323.  Either they are red on the line (then somebody must own them)
or they are fine and my extractor is over-reporting.  Measure, don't inherit.

  python cmdr_named_tests_r1.py [--sha <40-hex>]
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
LINE = "origin/mirror/integration-frontend-apple-pass1"
ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
EXPORT_DIRS = "backend data contracts tools scripts agent-mcp"
FILES = ["test_qoder_ord0310_keyless_leg_receipts.py",
         "test_qoder_ord0327_write_bound_default.py",
         "test_solver_runtime_policy.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default="")
    a = ap.parse_args()
    subprocess.run(["git", "-C", REPO, "fetch", "origin", "--quiet"], timeout=900)
    sha = a.sha or subprocess.run(["git", "-C", REPO, "rev-parse", LINE], capture_output=True,
                                 text=True).stdout.strip()
    tree = subprocess.run(["git", "-C", REPO, "rev-parse", sha + "^{tree}"], capture_output=True,
                          text=True).stdout.strip()
    out = os.path.join(ROOT, "snap_named_tests_%s" % sha[:8])
    if os.path.isdir(out):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", out.replace("/", "\\")], timeout=600)
    os.makedirs(out)
    p = subprocess.run("git -C %s archive %s %s | tar -x -C %s" % (REPO, sha, EXPORT_DIRS, out),
                       shell=True, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    report = {"sha": sha, "tree": tree, "export": out, "archive_rc": p.returncode,
              "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "interpreter": VENV_PY, "files": []}
    env = dict(os.environ, PYTHONPATH=out)
    col = subprocess.run([VENV_PY, "-m", "pytest", "--collect-only", "-q", "tests"],
                         cwd=os.path.join(out, "backend"), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900, env=env)
    nums = re.findall(r"(\d+) tests? collected", col.stdout)
    report["whole_suite"] = {"collect_exit": col.returncode,
                             "collected": int(nums[-1]) if nums else None,
                             "interrupted": "Interrupted" in col.stdout}
    for f in FILES:
        r = subprocess.run([VENV_PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "tests/" + f],
                           cwd=os.path.join(out, "backend"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1200, env=env)
        tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-3:]
        rep = re.search(r"(\d+) passed.*?(\d+) failed", r.stdout or "", re.S)
        report["files"].append({"file": f, "rc": r.returncode, "tail": tail,
                                "passed": int(rep.group(1)) if rep else None,
                                "failed": int(rep.group(2)) if rep else None,
                                "verdict": "GREEN" if r.returncode == 0 else "RED"})
    json.dump(report, io.open(os.path.join(ROOT, "patrol", "named_tests_%s.json" % sha[:8]),
                              "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("sha %s tree %s  collected=%s (rc %s, Interrupted=%s)" % (
        sha[:12], tree[:12], report["whole_suite"]["collected"], report["whole_suite"]["collect_exit"],
        report["whole_suite"]["interrupted"]))
    for row in report["files"]:
        print("  %-46s %-6s passed=%s failed=%s  %s" % (row["file"], row["verdict"], row["passed"],
                                                        row["failed"], " | ".join(row["tail"])[:120]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
