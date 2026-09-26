#!/usr/bin/env python3
"""Run a NAMED list of backend test files against a given commit, in a private export.

r1 (`cmdr_named_tests_r1.py`) hard-coded three files; this version takes the list from the order
under acceptance, because ORD-0340's own gate is a fourth file and I refuse to land a backend
change on a lane's word for "21 passed together".

Same recipe as r1 and for the same reasons:
  - `git archive <sha> backend data contracts tools scripts agent-mcp | tar -x` into a fresh snap.
    An export without `scripts/` or `agent-mcp/` collects ZERO tests and looks green; excluding root
    `data/mock` or `contracts` manufactures fake reds.
  - interpreter is the venv Python, never a system one; PYTHONPATH is the export root.
  - `--collect-only -q tests` runs FIRST and its number is reported, so a passed count always has
    a denominator attached.
  - the export is deleted by path, and only paths I created are deleted.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
EXPORT_DIRS = "backend data contracts tools scripts agent-mcp"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True, help="40-hex or any rev that resolves locally")
    ap.add_argument("--files", required=True, help="comma-separated test file names under backend/tests")
    ap.add_argument("--tag", default="named")
    a = ap.parse_args()

    full = subprocess.run(["git", "-C", REPO, "rev-parse", a.sha],
                          capture_output=True, text=True, errors="replace")
    sha = full.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        print("SHA_UNRESOLVABLE %r" % a.sha, file=sys.stderr)
        return 2
    tree = subprocess.run(["git", "-C", REPO, "rev-parse", sha + "^{tree}"],
                          capture_output=True, text=True).stdout.strip()
    out = os.path.join(ROOT, "snap_%s_%s" % (a.tag, sha[:8]))
    if os.path.isdir(out):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", out.replace("/", "\\")], timeout=600)
    os.makedirs(out)
    p = subprocess.run("git -C %s archive %s %s | tar -x -C %s" % (REPO, sha, EXPORT_DIRS, out),
                       shell=True, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    report = {"sha": sha, "tree": tree, "export": out.replace("\\", "/"), "archive_rc": p.returncode,
              "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "interpreter": VENV_PY,
              "command": "python -m pytest -p no:cacheprovider -q tests/<file>", "files": []}
    env = dict(os.environ)
    env["PYTHONPATH"] = out
    for k in [k for k in list(env) if re.search(r"(API_KEY|AUTH_TOKEN|SECRET)$|^OPENAI_|^DEEPSEEK_", k)]:
        env.pop(k, None)
    col = subprocess.run([VENV_PY, "-m", "pytest", "--collect-only", "-q", "tests"],
                         cwd=os.path.join(out, "backend"), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900, env=env)
    nums = re.findall(r"(\d+) tests? collected", col.stdout)
    report["whole_suite"] = {"collect_exit": col.returncode,
                             "collected": int(nums[-1]) if nums else None,
                             "interrupted": "Interrupted" in col.stdout}
    for f in [x.strip() for x in a.files.split(",") if x.strip()]:
        r = subprocess.run([VENV_PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "tests/" + f],
                           cwd=os.path.join(out, "backend"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1500, env=env)
        tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-2:]
        m = re.search(r"(\d+) passed", r.stdout or "")
        fm = re.search(r"(\d+) failed", r.stdout or "")
        report["files"].append({"file": f, "rc": r.returncode, "tail": tail,
                                "passed": int(m.group(1)) if m else None,
                                "failed": int(fm.group(1)) if fm else None,
                                "verdict": "GREEN" if r.returncode == 0 else "RED"})
    path = os.path.join(ROOT, "patrol", "backend_named_%s_%s.json" % (a.tag, sha[:8]))
    json.dump(report, io_open(path), ensure_ascii=False, indent=1)
    print("sha %s tree %s collected=%s (collect rc %s)" % (
        sha[:8], tree[:8], report["whole_suite"]["collected"], report["whole_suite"]["collect_exit"]))
    for row in report["files"]:
        print("  %-46s %s passed=%s failed=%s rc=%s" % (
            row["file"], row["verdict"], row["passed"], row["failed"], row["rc"]))
    print("reading -> " + path.replace("\\", "/"))
    return 0 if all(r["verdict"] == "GREEN" for r in report["files"]) else 3


def io_open(path):
    import io
    return io.open(path, "w", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
