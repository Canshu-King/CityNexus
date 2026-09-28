"""ORD-0430 round-2 counter arm: the candidate with the relocation switched off.

Same tree, same sha, one line: `const yieldsAtRest = idleCompact && restOverlap` becomes
`false`, so the pill stays wherever the page came to rest. If the ink covering comes back, the
relocation is what cleared it; if it does not, my own reading caused the difference and the arm
says so. node_modules arrives as a junction and is dropped with plain rmdir, never recursively.
"""
import json
import os
import re
import subprocess
import time

REPO = "D:/moodle/CityNexus"
SHA = "c2e3535710aaa9dd148b75bcda93dd2233b14c83"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/_build_counter_r2"
FE = os.path.join(OUT, "frontend")
OLD = "  const yieldsAtRest = idleCompact && restOverlap;"
NEW = "  const yieldsAtRest = false; /* counter arm: relocation off, rest position kept */"


def run(cmd, cwd=None, timeout=2400):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, shell=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


log = {"sha": SHA, "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "steps": []}
run("cmd /c rmdir /s /q " + OUT.replace("/", "\\"))
os.makedirs(OUT, exist_ok=True)
rc, out = run("git -C %s archive %s frontend | tar -x -C %s" % (REPO, SHA, OUT))
log["steps"].append({"step": "archive", "rc": rc, "out": out.strip()[:200]})
assert rc == 0, out

dock = os.path.join(FE, "src/features/agent/CopilotDock.tsx")
text = open(dock, encoding="utf-8").read()
assert text.count(OLD) == 1, "anchor line present %d times" % text.count(OLD)
open(dock, "w", encoding="utf-8", newline="").write(text.replace(OLD, NEW, 1))
after = open(dock, encoding="utf-8").read()
log["counter_patch"] = {"line_replaced": OLD.strip(), "old_still_present": OLD in after,
                        "new_present": NEW in after}
assert OLD not in after and NEW in after

nm = os.path.join(FE, "node_modules")
if os.path.isdir(nm):
    run("cmd /c rmdir " + nm.replace("/", "\\"))
rc, out = run("cmd /c mklink /J %s D:\\moodle\\CityNexus\\frontend\\node_modules" % nm.replace("/", "\\"))
log["steps"].append({"step": "junction", "rc": rc, "out": out.strip()[:200]})

t0 = time.time()
rc, out = run("npm run build", cwd=FE)
log["steps"].append({"step": "vite_build", "rc": rc, "secs": round(time.time() - t0, 2), "tail": out[-400:]})
pre = re.search(r"precache\s+(\d+) entries \(([\d.]+) KiB\)", out)
idx = os.path.join(FE, "dist", "index.html")
html = open(idx, encoding="utf-8").read() if os.path.isfile(idx) else ""
log["build"] = {"rc": rc, "index_exists": bool(html),
                "asset_refs": re.findall(r'(?:src|href)="(/assets/[^"]+)"', html),
                "precache_entries": pre.group(1) if pre else None,
                "precache_kib": pre.group(2) if pre else None}
assert rc == 0 and html, out[-1200:]
dst = "D:/moodle/_qoder_ai_ord0387_20260928/_build_counter_r2_info.json"
json.dump(log, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("COUNTER rc=%s assets=%s precache=%s" % (rc, log["build"]["asset_refs"], log["build"]["precache_kib"]))
