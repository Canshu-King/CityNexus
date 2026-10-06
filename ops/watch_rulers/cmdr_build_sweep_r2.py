"""CMDR build sweep r2 -- retire my own derived `_build_*` exports that no live listener serves.

Two hazards this exists to not walk into:
  1. `_build_*/frontend/node_modules` is a directory JUNCTION into a real tree.  A recursive delete that
     follows it destroys shared dependencies, so every reparse point is unmounted with plain rmdir first,
     and a tree still holding a reparse point after that step aborts the run.
  2. "not served" is decided from live process command lines (the --dist argument of running proxies), not
     from memory.  Anything named there, or modified in the last hour, is kept.

Default is dry-run; --apply is what deletes.
"""
import argparse
import json
import os
import subprocess
import sys
import time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
KEEP_MINUTES = 60


def reparse_entries(path):
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-ChildItem -LiteralPath '" + path + "' -Force -Recurse -Depth 2 "
                          "| Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } "
                          "| ForEach-Object { $_.FullName }"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def served_dists():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node' } "
          "| Select-Object -ExpandProperty CommandLine")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    dists = set()
    for line in out.stdout.splitlines():
        if "--dist" in line:
            for tok in line.split():
                if "_build_" in tok:
                    dists.add(tok.split("frontend")[0].rstrip("/\\"))
    return dists


ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--limit", type=int, default=40)
a = ap.parse_args()

served = served_dists()
now = time.time()
cands, kept = [], []
for name in sorted(os.listdir(LIVE)):
    if not name.startswith("_build_"):
        continue
    full = os.path.join(LIVE, name)
    if not os.path.isdir(full):
        continue
    age_min = (now - os.path.getmtime(full)) / 60.0
    reason = None
    if os.path.normcase(full) in {os.path.normcase(s) for s in served if s}:
        reason = "served"
    elif age_min < KEEP_MINUTES:
        reason = "younger_than_" + str(KEEP_MINUTES) + "_min"
    if reason:
        kept.append({"dir": name, "why": reason})
    else:
        cands.append({"dir": name, "age_min": round(age_min), "path": full})

report = {"mode": "APPLY" if a.apply else "DRY", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
          "served_dists": sorted(served), "kept": kept, "candidates": len(cands)}
freed = 0
doomed = cands[: a.limit]
for c in doomed:
    if a.apply:
        for rp in reparse_entries(c["path"]):
            r = subprocess.run(["cmd", "/c", "rmdir", rp], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                report["abort"] = "rmdir on a reparse point failed: " + rp + " :: " + (r.stderr or "")[:200]
                print(json.dumps(report, ensure_ascii=False, indent=1))
                sys.exit(3)
        left = reparse_entries(c["path"])
        if left:
            report["abort"] = "reparse points still present after unmount: " + json.dumps(left[:3])
            print(json.dumps(report, ensure_ascii=False, indent=1))
            sys.exit(4)
        shutil_rm = subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", c["path"]],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
        if shutil_rm.returncode != 0 or os.path.exists(c["path"]):
            report["abort"] = "rmdir /s failed for " + c["path"] + " :: " + (shutil_rm.stderr or "")[:200]
            print(json.dumps(report, ensure_ascii=False, indent=1))
            sys.exit(5)
        freed += c.get("bytes", 0)
    c.pop("path", None)
report["removed"] = [c["dir"] for c in doomed]
report["kept_count"] = len(kept)
print(json.dumps(report, ensure_ascii=False, indent=1)[:2600])
sys.exit(0)
