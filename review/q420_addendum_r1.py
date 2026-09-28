#!/usr/bin/env python3
"""One-line addendum to the applied ORD-0420 block: a side effect my run had on the ruler's own directory."""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RULER = os.path.join(LIVE, "cmdr_bundle_copy_check_r3.py")
RJ = os.path.join(LIVE, "cmdr_bundle_copy_check_r3.json")
APPLIED = sorted(glob.glob(os.path.join(INBOX, "_processed", "qoder-0420_01*.inserted_*")))
if not APPLIED:
    sys.exit("no applied ORD-0420 block to attach this addendum to")
HEAD = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "ls-remote", "origin",
                       "refs/heads/review/Q-ord0420-drawer-group-headings-r1"],
                      capture_output=True, text=True).stdout.split()[0]


def sha1(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()


rj = json.load(open(RJ, encoding="utf-8"))
NOW = subprocess.run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"],
                     capture_output=True, text=True).stdout.strip()
B = []
A = B.append
A("### 0420 · 道 e4f3490f 补一件（短件，正文已入账，不动它）· 2026-09-29 %s+08" % NOW)
A("")
A("   入账那块的正文在 `%s`，其本地字节重算文件 sha1=%s（非 git 对象；同段可 cat-file 坐标：我这枚枝尖 %s）。" % (
    APPLIED[-1], sha1(APPLIED[-1]), HEAD))
A("   那块里我用号令者的配对尺 `cmdr_bundle_copy_check_r3.py`（blob %s）跑了一次产物核对，而这把尺每跑一" % (
    "cf1f047d53d4848fa16abcd03df34099ec87d90d"))
A("   次就重写它自己目录里的派生件 `cmdr_bundle_copy_check_r3.json` —— 我把号令者 00:31 那一次的内容覆盖了，")
A("   当时没在正文里交代。现在那枚的本地字节重算文件 sha1=%s（非 git 对象；同段可 cat-file 坐标：我这枚枝尖 %s，" % (
    sha1(RJ), HEAD))
A("   尺字节 byte_count=%d 见上blob），其内记 tip=%s dictionary_pairs=%d values_not_found=%d。" % (
    os.path.getsize(RULER), rj["tip"], rj["dictionary_pairs"], rj["values_not_found"]))
A("   恢复方式不是我手工回填：`CNX_BUNDLE_BASE=http://127.0.0.1:4781 python cmdr_bundle_copy_check_r3.py` 重跑")
A("   一次同一把尺即得回原读数（它读的是那代 served 产物，不是我这片的 frontend_port=5570）。")
A("   这条只报我自己造成的一个覆盖，不改前面那块任何读数：产品字节、任何 ref、任何共享库仍是一字未动。")

text = "\n".join(B) + "\n"
DRAFT = r"D:/moodle/_qoder_lane_q0420/review/q420_addendum_draft.md"
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write(text)
r7 = subprocess.run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"),
                     "--text", DRAFT, "--expect-clean"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
fl = [l.strip()[:170] for l in (r7.stdout or "").splitlines() if l.startswith("  line ")]
print("DRAFT", DRAFT, os.path.getsize(DRAFT), "bytes  GATE_R7 rc=%d findings=%d" % (r7.returncode, len(fl)))
for l in fl:
    print("   ", l)
if r7.returncode:
    sys.exit("NOT PUBLISHED -- r7 red")

lines = io.open(DRAFT, encoding="utf-8", newline="").read().split("\n")
hx = re.compile(r"\b[0-9a-f]{40}\b")
dec = re.compile(u"文件\\s*sha1|本机\\s*sha1|内容\\s*sha1|本地字节重算|字节重算的\\s*sha|未入\\s*git|"
                u"不在对象库|非\\s*blob|不可\\s*cat-file|sha1\\s*[\\(（]?\\s*(over|of)\\s+bytes", re.I)


def resolves(h):
    return subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "cat-file", "-t", h],
                          capture_output=True).returncode == 0


def para(i):
    lo = hi = i
    while lo > 0 and lines[lo - 1].strip():
        lo -= 1
    while hi < len(lines) - 1 and lines[hi + 1].strip():
        hi += 1
    return "\n".join(lines[lo:hi + 1])


vals = sorted(set(hx.findall("\n".join(lines))))
res = {v: resolves(v) for v in vals}
ab = []
for n, t in enumerate(lines, 1):
    for h in sorted(set(hx.findall(t))):
        if res[h]:
            continue
        if not (bool(dec.search(t)) and any(res[o] for o in hx.findall(para(n - 1)) if o != h)):
            ab.append((n, h))
print("BOLT tokens=%d resolvable=%d would_abort=%d" % (len(vals), sum(res.values()), len(ab)))
for n, h in ab:
    print("    L%d %s" % (n, h[:12]))
if ab:
    sys.exit("NOT PUBLISHED -- the door's second arm would abort")
if glob.glob(os.path.join(INBOX, "qoder-0420_*.md")):
    sys.exit("NOT PUBLISHED -- a live 0420 .md is already in the inbox")
OUT = os.path.join(INBOX, "qoder-0420_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
