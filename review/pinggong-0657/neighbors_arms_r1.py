# -*- coding: utf-8 -*-
"""刀一的邻面回归双臂：57 枚引用事件面的测试文件，在「现尖那一代」与「改后那一代」各跑一次。
两臂各一枚读数件。跑完停改后那一代，并核对三枚产品字节的 blob 没被中途换错。"""
import hashlib
import os
import subprocess
import sys

VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588"
BACK = TREE + "/backend"
TIP = "8f2e05ad1d2ba56b3a5a0bbc851cf122b23640d0"
OUT = TREE + "/review/pinggong-0657/"
PRODUCT = ["backend/app/schemas.py", "backend/app/main.py", "backend/db/schema.sql"]
LIST_FILE = r"D:/moodle/_pinggong_scratch/0657/neighbors.txt"


def blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git_show(ref, path):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)], capture_output=True)
    if proc.returncode:
        sys.exit("ABORT 取不到 %s:%s" % (ref, path))
    return proc.stdout


def read(rel):
    with open(os.path.join(TREE, rel), "rb") as handle:
        return handle.read()


def write(rel, data):
    with open(os.path.join(TREE, rel), "wb") as handle:
        handle.write(data)


files = [l.strip() for l in open(LIST_FILE, encoding="utf-8").read().split("\n") if l.strip()]
assert len(files) > 40, "邻面名单不完整，只取到 %d 枚" % len(files)
after = {p: read(p) for p in PRODUCT}
before = {p: git_show(TIP, p) for p in PRODUCT}


def run(tag):
    proc = subprocess.run([VENV, "-m", "pytest"] + files + ["-q", "--no-header", "--tb=line"],
                          cwd=BACK, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=3600)
    text = proc.stdout
    with open(OUT + tag + ".txt", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("=== %s｜邻面 %d 枚｜rc=%d\n%s" % (tag, len(files), proc.returncode, text))
    verdict = [l.strip() for l in text.split("\n") if " passed" in l or " failed" in l]
    reds = [l.strip() for l in text.split("\n") if l.startswith("FAILED")]
    print("[%s] %s｜红 %d 条 -> %s" % (tag, verdict[-1] if verdict else "无判语行", len(reds), OUT + tag + ".txt"))
    return reds


for p in PRODUCT:
    write(p, before[p])
reds_a = run("armA_neighbors_on_tip")
for p in PRODUCT:
    write(p, after[p])
if [blob(read(p)) for p in PRODUCT] != [blob(after[p]) for p in PRODUCT]:
    sys.exit("ABORT 没回到改后那一代")
reds_b = run("armB_neighbors_after")

new = [r for r in reds_b if r not in reds_a]
gone = [r for r in reds_a if r not in reds_b]
print("两臂红集合对照：改后新增红 %d 条、改后消失 %d 条" % (len(new), len(gone)))
for r in new:
    print("   新增 %s" % r[:140])
print("工作树未登记改动 %d 处" % len([l for l in subprocess.run(
    ["git", "-C", TREE, "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines() if l.strip()]))
