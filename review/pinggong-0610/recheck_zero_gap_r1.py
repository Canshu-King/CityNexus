# -*- coding: utf-8 -*-
"""复核选料尺的「零缺口」：把每一枚代表枝独有模块的 app.* import 逐名换算成尖上的文件路径，
现读 cat-file 判在不在。尺只看包的第一段（agent 在不在），所以包里没有那一枚时它放过去——
这里按整枚模块路径判，并把每一名的判据行原样打出来。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TIP = "8940570c022950b705cc3b37139d1b8f7052c42a"
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"
ZERO = ["truth.py", "shared_walk.py", "presence.py", "launch_origin.py", "progress_drift.py",
        "readiness.py", "in_transit_reroute.py", "group_presence.py"]

IMPORT = re.compile(r"^\s*(?:from|import)\s+(app\.[A-Za-z0-9_.]+)", re.M)


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def exists_on_tip(dotted):
    """app.a.b -> backend/app/a/b.py（或包 __init__.py），现读 cat-file。"""
    tail = dotted.split(".", 1)[1].replace(".", "/")
    for cand in ("backend/app/%s.py" % tail, "backend/app/%s/__init__.py" % tail):
        if git("cat-file", "-e", "%s:%s" % (TIP, cand)).returncode == 0:
            return cand
    return None


print("尖 %s｜来源代 %s" % (TIP[:12], REP[:12]))
for name in ZERO:
    blob = git("cat-file", "blob", "%s:backend/app/execution/%s" % (REP, name)).stdout
    if not blob:
        print("%s: 取不到字节" % name)
        continue
    mods = sorted(set(IMPORT.findall(blob)))
    missing = []
    for dotted in mods:
        if not exists_on_tip(dotted):
            line = [i + 1 for i, row in enumerate(blob.splitlines()) if dotted in row]
            missing.append("%s（枝内 %s:%s）" % (dotted, name, line[0] if line else "?"))
    verdict = "可独立落地" if not missing else "带了尖上没有的 import：" + "；".join(missing)
    print("%-26s import %d 名 -> %s" % (name, len(mods), verdict))
