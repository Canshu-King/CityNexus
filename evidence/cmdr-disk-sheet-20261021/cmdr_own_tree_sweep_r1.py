"""CMDR own-tree sweep r1 -- free disk that is provably mine, derived, and dead.

Scope is deliberately narrow, because the owner's standing rule is that only evidence-backed garbage goes:
  * only directories named `_qoder_cmdr_*` at the D:/moodle root (this commander's own exports),
  * only ones whose newest content is older than --days (default 14),
  * never one that any live process names in its command line (a landing gate or proxy still pointing at it),
  * junctions are unmounted with plain rmdir first, and a tree that still holds a reparse point after that
    is left alone rather than deleted through the link.

Default is dry-run; --apply is what deletes.  Bytes freed are summed per directory and the volume reading
before/after is printed so the number is measured, not inferred.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = r"D:\moodle"
DETACHED_CHECK_TIMEOUT = 300


def live_command_lines():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node|cmd|powershell' } "
          "| Select-Object -ExpandProperty CommandLine")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=DETACHED_CHECK_TIMEOUT)
    return r.stdout or ""


def newest_mtime(path):
    newest = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                m = os.stat(os.path.join(root, f), follow_symlinks=False).st_mtime
            except OSError:
                continue
            if m > newest:
                newest = m
    return newest


def size_bytes(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for d in list(dirs):
            full = os.path.join(root, d)
            try:
                st = os.stat(full, follow_symlinks=False)
                if getattr(st, "st_reparse_tag", 0):
                    dirs.remove(d)
            except OSError:
                dirs.remove(d)
        for f in files:
            try:
                st = os.stat(os.path.join(root, f), follow_symlinks=False)
                if getattr(st, "st_reparse_tag", 0):
                    continue
                total += st.st_size
            except OSError:
                pass
    return total


def reparse_under(path):
    ps = ("Get-ChildItem -LiteralPath '" + path + "' -Force -Recurse "
          "| Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } "
          "| ForEach-Object { $_.FullName }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=DETACHED_CHECK_TIMEOUT)
    return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]


def df_free():
    st = shutil_disk_free(ROOT)
    return st


def shutil_disk_free(path):
    import shutil as _sh
    try:
        return _sh.disk_usage(path).free
    except OSError:
        return None


ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--days", type=int, default=14)
ap.add_argument("--out", default="")
a = ap.parse_args()

cmds = live_command_lines()
now = time.time()
report = {"mode": "APPLY" if a.apply else "DRY", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
          "days": a.days, "free_before_bytes": df_free(), "kept": [], "removed": []}

for name in sorted(os.listdir(ROOT)):
    if not name.startswith("_qoder_cmdr_"):
        continue
    full = os.path.join(ROOT, name)
    if not os.path.isdir(full):
        continue
    if full.replace("\\", "/") in cmds.replace("\\", "/") or name in cmds:
        print("KEEP %s (named by a live process)" % name, flush=True)
        report["kept"].append({"dir": name, "why": "named by a live process command line"})
        continue
    nm = newest_mtime(full)
    age_days = (now - nm) / 86400.0 if nm else 9e9
    if age_days < a.days:
        print("KEEP %s (newest content %.1f days old)" % (name, age_days), flush=True)
        report["kept"].append({"dir": name, "why": "newest content %.1f days old" % age_days})
        continue
    entry = {"dir": name, "age_days": round(age_days, 1)}
    print("CANDIDATE %s (%.1f days old)" % (name, age_days), flush=True)
    if a.apply:
        for rp in reparse_under(full):
            r = subprocess.run(["cmd", "/c", "rmdir", rp], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                report["abort"] = "could not unmount reparse point " + rp
                break
        else:
            left = reparse_under(full)
            if left:
                report["abort"] = "reparse points survive unmount: " + json.dumps(left[:2])
            else:
                entry["bytes"] = size_bytes(full)
                rm = subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", full], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace")
                if rm.returncode != 0 or os.path.exists(full):
                    report["abort"] = "rmdir failed for " + full + " :: " + (rm.stderr or "")[:160]
        if "abort" in report:
            break
    else:
        entry["bytes"] = size_bytes(full)
    report["removed"].append(entry)

report["bytes_listed"] = sum(e.get("bytes", 0) for e in report["removed"])
report["free_after_bytes"] = df_free()
report["dirs_kept"] = len(report["kept"])
report["dirs_removed"] = len(report["removed"])
report.pop("kept", None) if not a.apply else None
text = json.dumps({k: v for k, v in report.items() if k != "kept"}, ensure_ascii=False, indent=1)
print(text[:2600])
if a.apply:
    print("kept (not removed): %d dirs -- newest content too recent or referenced by a live process"
          % report["dirs_kept"])
if report.get("abort"):
    print("ABORT: " + report["abort"])
    sys.exit(3)
sys.exit(0)
