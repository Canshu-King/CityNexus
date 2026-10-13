# -*- coding: utf-8 -*-
"""刀一双臂读数：同一套测试文件，在「只有号令者那两站」与「三站齐」两代各跑一次，
两臂各落一枚读数件（不许用同一枚文件互证两臂）。跑完必须停在三站齐那一代。"""
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
TESTS = ["tests/test_event_resolution_projection.py"]


def git(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900).stdout


def blob(text):
    return hashlib.sha1(b"blob %d\0" % len(text) + text).hexdigest()


def read(rel):
    with open(os.path.join(TREE, rel), "rb") as handle:
        return handle.read()


def write(rel, data):
    with open(os.path.join(TREE, rel), "wb") as handle:
        handle.write(data)


def neighbors():
    out = subprocess.run(["grep", "-rl", "journeys/{journey_id}/events\|/events\b\|event_type",
                          os.path.join(BACK, "tests")], capture_output=True, text=True).stdout
    return sorted("tests/" + os.path.basename(l) for l in out.splitlines() if l.strip())


def run(tag, files, extra=""):
    proc = subprocess.run([VENV, "-m", "pytest"] + files + ["-q", "--no-header", "--tb=line"],
                          cwd=BACK, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=2400)
    text = proc.stdout
    with open(OUT + tag + ".txt", "w", encoding="utf-8", newline="\n") as handle:
        handle.write("=== %s%s\n=== rc=%d\n%s" % (tag, extra, proc.returncode, text))
    tail = [l.strip() for l in text.split("\n") if " passed" in l or " failed" in l or " error" in l]
    print("[%s] rc=%d -> %s｜%s" % (tag, proc.returncode, OUT + tag + ".txt", tail[-1] if tail else "无判语行"))
    return text


os.makedirs(OUT, exist_ok=True)
edited = {p: read(p) for p in PRODUCT}
tip_bytes = {p: git("show", "%s:%s" % (TIP, p)).encode("utf-8", "replace") for p in PRODUCT}
for p in PRODUCT:
    write(p, tip_bytes[p])
    if blob(read(p)) != blob(git("show", "%s:%s" % (TIP, p)).encode("utf-8", "replace")):
        sys.exit("ABORT 退代失败 " + p)
print("臂 A：退回现尖那三代字节（三站都不在），测试文件保留")
run("armA_tip_generation", TESTS)
neigh = neighbors()
print("   邻面文件 %d 枚" % len(neigh))
run("armA_neighbors_tip", neigh)

for p in PRODUCT:
    write(p, edited[p])
if [blob(read(p)) for p in PRODUCT] != [blob(edited[p]) for p in PRODUCT]:
    sys.exit("ABORT 没回到改后那一代")
print("臂 B：改后那一代（三站齐）")
run("armB_after", TESTS)
run("armB_neighbors_after", neigh)

print("两臂产物：%s" % "、".join(sorted(os.listdir(OUT))))
