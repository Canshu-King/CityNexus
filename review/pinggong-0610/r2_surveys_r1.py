# -*- coding: utf-8 -*-
"""在现尖那一代重出三份读数：接线面普查（逐枚现读行号）、零缺口复核、agent 包清册。
全部只读；读数按 \n 落盘。"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
OUTDIR = TREE + "/review/pinggong-0610"
BARE = r"D:/moodle/CityNexus"
REP = "a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9"
ZERO = ["truth.py", "shared_walk.py", "presence.py", "launch_origin.py", "progress_drift.py",
        "readiness.py", "in_transit_reroute.py", "group_presence.py"]
IMPORT = re.compile(r"^\s*(?:from|import)\s+(app\.[A-Za-z0-9_.]+)", re.M)

TIP = subprocess.run(["git", "-C", BARE, "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.split("\t")[0].strip()


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def save(name, rows):
    with open(os.path.join(OUTDIR, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(rows) + "\n")
    print("WROTE %s (%d 行)" % (name, len(rows)))


def show_lines(ref, path, needles, label):
    body = git("show", "%s:%s" % (ref, path)).stdout.replace("\r\n", "\n").split("\n")
    rows = []
    for needle in needles:
        for number, row in enumerate(body, start=1):
            if needle in row:
                rows.append("%s %s:%d %s" % (needle, path, number, row.strip()[:96]))
                break
        else:
            rows.append("%s 在 %s:%s 命中零处" % (needle, label, path))
    return rows


# 一、接线面普查（现尖那一代）
rows = ["尖 %s｜来源代 %s" % (TIP, REP), ""]
exec_list = git("ls-tree", "--name-only", "%s:backend/app/execution" % TIP).stdout.split()
rows.append("[一] execution/ 现读 %d 枚：%s" % (len(exec_list), " ".join(sorted(exec_list))))
rows.append("")
rows += show_lines(TIP, "backend/app/stay_mobility.py",
                   ["def experience_payload", "def _active_plan_payload"], "尖")
rows += show_lines(TIP, "backend/app/operations/v9.py",
                   ["def _execution_truth", "def refresh_offline_snapshot", "def record_location",
                    "row = LocationObservation(", "def edge_snapshot"], "尖")
rows += show_lines(TIP, "backend/app/main.py",
                   ["row = record_location(", "payload = edge_snapshot(session, device)",
                    "def get_edge_journey_snapshot"], "尖")
member_hits = git("grep", "-c", "JourneyMember", TIP, "--", "backend/app").stdout.splitlines()
rows.append("")
rows.append("[二] 尖上生产侧 JourneyMember 命中（按文件计）：")
rows += ["   " + line.split(":", 1)[1].replace(TIP + ":", "") for line in member_hits]
rows.append("")
rows += show_lines(REP, "backend/app/execution/presence.py",
                   ["journey_member_id == str(viewer_member_id)"], "枝内")
save("r2_wiring_survey.txt", rows)

# 二、纪律允许宿主的成员面命中数（现读）
host = git("show", "%s:backend/app/stay_mobility.py" % TIP).stdout
save("r2_host_member_hits.txt", [
    "命令口径：git grep -c JourneyMember <尖> -- backend/app/stay_mobility.py",
    "现读命中行数：%d" % len([r for r in host.split("\n") if "JourneyMember" in r]),
    "该文件行数：%d" % len(host.rstrip("\n").split("\n")),
])

# 三、零缺口八枚的整路径复核（对现尖）
tip_top = set(x for x in git("ls-tree", "--name-only", "%s:backend/app" % TIP).stdout.split())
tip_files = set(git("ls-tree", "-r", "--name-only", TIP, "--", "backend/app").stdout.split())
rows = ["尖 %s｜来源代 %s" % (TIP, REP),
        "判据：import 的整枚模块路径必须能在尖上 cat-file 到（只比包名第一段会放过去）", ""]
for name in ZERO:
    blob = git("cat-file", "blob", "%s:backend/app/execution/%s" % (REP, name)).stdout
    mods = sorted(set(IMPORT.findall(blob)))
    missing = []
    for dotted in mods:
        tail = dotted.split(".", 1)[1].replace(".", "/")
        if "backend/app/%s.py" % tail in tip_files or "backend/app/%s/__init__.py" % tail in tip_files:
            continue
        line = next((i for i, r in enumerate(blob.split("\n"), start=1) if dotted in r), 0)
        missing.append("%s（枝内 %s:%d）" % (dotted, name, line))
    rows.append("%-26s import %d 名 -> %s" % (name, len(mods),
                                              "可独立落地" if not missing else "带了尖上没有的 import：" + "；".join(missing)))
save("r2_recheck_zero_gap.txt", rows)

# 四、agent 包清册（证明 watch_policy / journey_intent 不在尖上，并列出尖上真有的那些）
agent = sorted(x for x in git("ls-tree", "--name-only", "%s:backend/app/agent" % TIP).stdout.split())
rows = ["尖 %s" % TIP,
        "backend/app/agent/ 现读 %d 枚：%s" % (len(agent), " ".join(agent))]
for name in ("watch_policy.py", "journey_intent.py"):
    hit = "backend/app/agent/%s" % name in tip_files
    rows.append("   %s 在尖上：%s" % (name, "有" if hit else "无"))
save("r2_agent_inventory.txt", rows)
print("\n".join(rows))
print("TIP=%s" % TIP)
