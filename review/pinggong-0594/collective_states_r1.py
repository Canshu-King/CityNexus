# -*- coding: utf-8 -*-
"""ORD-0594 三态对照的取数器（机械化，不靠记忆）：
对 collective 那三枚模块，逐枚算出它 import 的每一个 app.* 名字，
再去现尖那一代的源文件里查这个名字在不在（按顶层 def/class/赋值 的名字行判，不猜）。
分三态：能直接接 / 要改哪一枚签名（模块在、个别名字缺）/ 现尖根本没有对应形状（模块文件都不在）。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
REP = "1725a449a50898e1c63889f0e7c0a81f347a7a1f"
TIP = open("D:/moodle/_pinggong_scratch/tip_0593.txt").read().strip()
MODULES = ["backend/app/collective_authority.py", "backend/app/collective_mediation.py",
           "backend/app/collective_operator.py"]
FROM_APP = re.compile(r"^\s*from\s+(app\.[\w.]+)\s+import\s+\(([^)]*)\)", re.M | re.S)
FROM_APP_ONE = re.compile(r"^\s*from\s+(app\.[\w.]+)\s+import\s+([\w, ]+)$", re.M)
TOP_NAME = re.compile(r"^(?:class|def)\s+([A-Za-z_]\w*)|^[ \t{]*(?:\"|')([A-Za-z_]\w*)(?:\"|')\s*[:,]", re.M)
ASSIGN = re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*[:=]", re.M)


def show(ref, path):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)], capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def app_names(text):
    pairs = []
    for match in FROM_APP.finditer(text):
        module = match.group(1)
        for name in match.group(2).replace("\n", " ").split(","):
            name = name.strip().split(" as ")[0].strip()
            if name:
                pairs.append((module, name))
    for match in FROM_APP_ONE.finditer(text):
        module = match.group(1)
        for name in match.group(2).split(","):
            name = name.strip().split(" as ")[0].strip()
            if name:
                pairs.append((module, name))
    return pairs


def tip_symbols(path):
    text = show(TIP, path)
    if text is None:
        return None
    names = {m.group(1) or m.group(2) for m in TOP_NAME.finditer(text)}
    names |= set(ASSIGN.findall(text))
    return names


report = []
for module in MODULES:
    text = show(REP, module)
    if text is None:
        report.append((module, "代表枝读不到", [], []))
        continue
    pairs = sorted(set(app_names(text)))
    missing_file, missing_name = [], []
    for path, name in pairs:
        rel = "backend/" + path.replace(".", "/") + ".py"
        if not path.endswith("_"):
            pass
        symbols = tip_symbols(rel)
        
        if symbols is None:
            missing_file.append(path)
        elif name not in symbols:
            missing_name.append("%s:%s" % (path, name))
    state = "能直接接" if not missing_file and not missing_name else (
        "要改签名或补名字" if not missing_file else "现尖根本没有对应形状")
    report.append((module, state, sorted(set(missing_name)), sorted(set(missing_file))))

lines = ["模块\t三态\t缺的名字\t缺的文件\tapp.* 引用数"]
for module, state, names, files in report:
    text = show(REP, module)
    lines.append("%s\t%s\t%s\t%s\t%d" % (module, state, ";".join(names) or "无",
                                          ";".join(files) or "无", len(set(app_names(text)))))
out = "\n".join(lines) + "\n"
open("D:/moodle/_pinggong_scratch/collective_states_r1.txt", "w", encoding="utf-8").write(out)
print(out)
