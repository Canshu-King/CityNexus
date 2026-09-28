"""ORD-0430 counter arm for the PARTIAL gap: same tree, the shape collapse switched off.

The commander's failing cell was "after it collapses it still overlaps a line of body text", so the
counter has to remove exactly the collapse -- the pill still relocates to the slot the runtime picks,
but keeps its natural 165x54 size. If the text-line overlap comes back, the collapse is what cleared
it. Built in a private export; nothing here is committed as a product candidate.
"""
import json
import os
import re
import subprocess
import time

REPO = "D:/moodle/CityNexus"
SHA = "9bbfafa6e5fa728d792c7ad05b7d64c7b0e3c1aa"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/_build_counter_r3"
FE = os.path.join(OUT, "frontend")
DOCK_OLD = "  width: 44px;\n  height: 44px;\n  padding: 0;\n"
DOCK_NEW = "  width: auto;\n  height: auto;\n  padding: 0;\n"
EDGE_OLD = "  width: 44px;\n  height: 44px;\n  min-height: 44px;\n"
EDGE_NEW = "  width: auto;\n  height: auto;\n"


def run(cmd, cwd=None, timeout=2400):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, shell=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


log = {"sha": SHA, "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "steps": []}
run("cmd /c rmdir /s /q " + OUT.replace("/", "\\"))
os.makedirs(OUT, exist_ok=True)
rc, out = run("git -C %s archive %s frontend | tar -x -C %s" % (REPO, SHA, OUT))
assert rc == 0, out
css = os.path.join(FE, "src/design-tokens.css")
text = open(css, encoding="utf-8").read()
NL = chr(10)
LABEL_OLD = (".cn-copilot-dock.idle-compact.yield-at-rest .cn-copilot-edge > "
             "span:not(.cn-copilot-edge-mark) {" + NL + "  display: none;" + NL + "}")
for old, new_, tag in ((DOCK_OLD, DOCK_NEW, "dock"), (EDGE_OLD, EDGE_NEW, "edge"),
                       (LABEL_OLD, "", "label")):
    n = text.count(old)
    assert n == 1, "%s anchor found %d times" % (tag, n)
    text = text.replace(old, new_, 1)
open(css, "w", encoding="utf-8", newline="").write(text)
check = open(css, encoding="utf-8").read()
log["counter_patch"] = {"dock_collapsed": DOCK_OLD in check, "edge_collapsed": EDGE_OLD in check,
                        "label_rule_present": LABEL_OLD in check,
                        "dock_auto": DOCK_NEW in check, "edge_auto": EDGE_NEW in check}
assert DOCK_OLD not in check and EDGE_OLD not in check and LABEL_OLD not in check

nm = os.path.join(FE, "node_modules")
if os.path.isdir(nm):
    run("cmd /c rmdir " + nm.replace("/", "\\"))
rc, out = run("cmd /c mklink /J %s D:\\moodle\\CityNexus\\frontend\\node_modules" % nm.replace("/", "\\"))
log["steps"].append({"step": "junction", "rc": rc, "out": out.strip()[:200]})
t0 = time.time()
rc, out = run("npm run build", cwd=FE)
log["steps"].append({"step": "vite_build", "rc": rc, "secs": round(time.time() - t0, 2), "tail": out[-300:]})
pre = re.search(r"precache\s+(\d+) entries \(([\d.]+) KiB\)", out)
idx = os.path.join(FE, "dist", "index.html")
html = open(idx, encoding="utf-8").read() if os.path.isfile(idx) else ""
log["build"] = {"rc": rc, "index_exists": bool(html), "asset_refs": re.findall(r'(?:src|href)="(/assets/[^"]+)"', html),
                "precache_entries": pre.group(1) if pre else None, "precache_kib": pre.group(2) if pre else None}
assert rc == 0 and html, out[-1200:]
dst = "D:/moodle/_qoder_ai_ord0387_20260928/_build_counter_r3_info.json"
json.dump(log, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("COUNTER rc=%s assets=%s precache_kib=%s" % (rc, log["build"]["asset_refs"], log["build"]["precache_kib"]))
