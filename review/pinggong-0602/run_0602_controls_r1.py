# -*- coding: utf-8 -*-
"""ORD-0602 三态对照跑批：同一枚测试文件，在「未接线 / 只落 import / 全接线」三代人身上各跑一次。
每态跑完都把字节恢复并核对，落三张读数文件，最后必须停在全接线那一代。"""
import hashlib
import shutil
import subprocess
import sys

VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0588/backend"
TIP = "b68f381712abd9207b5ecd7625d18d0883838459"
TARGET = TREE + "/app/stay_mobility.py"
WIRED = "D:/moodle/_pinggong_scratch/stay_mobility_wired_0602.py"
OUT = "D:/moodle/_pinggong_scratch/"
TEST = "tests/test_qoder_ord0602_private_buddy_location_scope.py"
IMPORT_LINE = b"from app.execution.location_scope import PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE\n"
ANCHOR = b"from app.execution.clock import execution_clock\n"


def blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def write(data):
    with open(TARGET, "wb") as handle:
        handle.write(data)


def read():
    with open(TARGET, "rb") as handle:
        return handle.read()


def run(label, name):
    proc = subprocess.run([VENV, "-m", "pytest", TEST, "-q", "--no-header"], cwd=TREE,
                          capture_output=True)
    text = proc.stdout.decode("utf-8", "replace")
    with open(OUT + name, "w", encoding="utf-8") as handle:
        handle.write("=== state: %s\n=== rc=%d\n%s" % (label, proc.returncode, text))
    tail = [line for line in text.splitlines() if line.strip().startswith(
        ("FAILED", "PASSED", "ERROR")) or " passed" in line or " failed" in line
        or "error" in line.split(":")[0].lower()]
    print("[%s] rc=%d -> %s" % (label, proc.returncode, OUT + name))
    for line in tail:
        print("   ", line.strip())


tip_bytes = subprocess.run(["git", "-C", REPO, "show", TIP + ":backend/app/stay_mobility.py"],
                           capture_output=True).stdout
wired_bytes = read()
assert blob(wired_bytes) == "5a6bf03557471e3acf5357df3575d37f48eb2592", (
    "tree is not on the wired generation before the controls start: %s" % blob(wired_bytes))
shutil.copyfile(TARGET, WIRED)

run("state1 全接线（工作树当前那代）", "0602_control1_wired.txt")

write(tip_bytes)
assert IMPORT_LINE not in read()
run("state2 现尖那代（未接线、也没有 location_scope 的调用面）", "0602_control2_unwired.txt")

write(tip_bytes.replace(ANCHOR, ANCHOR + IMPORT_LINE, 1))
assert read().count(IMPORT_LINE) == 1 and read().count(b"LocationObservation.source !=") == 0
run("state3 只落 import、谓词仍缺", "0602_control3_import_only.txt")

write(wired_bytes)
if blob(read()) != "5a6bf03557471e3acf5357df3575d37f48eb2592":
    sys.exit("ABORT tree did not end on the wired generation")
print("END STATE: wired blob %s, predicate hits %d"
      % (blob(read()), read().count(b"PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE")))
