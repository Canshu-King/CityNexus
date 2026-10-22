# -*- coding: utf-8 -*-
"""号令者对 ORD-0709 甲这一刀的独立复算——不用车道那把尺的结论，自己再数一遍。

要证的三件事，任何一件不成立就写 CHECK 并退非零：
1. 同一代两个尖之间，内联双语那把尺的总数正好降 20，且他那两枚文件各归零；
2. 他新增的每一枚字典键，中英文值都能在**旧尖那两枚文件里**找到同样字节的原句（是搬运不是改写）；
3. 那些原句在新尖的这两枚文件里已经没有了，而键在旧尖的字典里原本不存在（没有留两处）。

车道交了三枚 blob，这里逐枚拿 git cat-file 对拍，对不上就是代次不对。
"""
import re
import subprocess
import sys
from collections import Counter

REPO = "D:/moodle/CityNexus"
BASE = "af8ad6a1c32021852ade9a7fa6d9f782f687879f"
CAND = "01d6f8fc811e9abd44b09374591e4fc51e0bdcab"
PC = "frontend/src/features/planning/PlanComparison.tsx"
JT = "frontend/src/features/setup/JourneyTrialSetup.tsx"
LOC = "frontend/src/i18n/LocaleContext.tsx"
CLAIMED_BLOBS = {PC: "0587fb8ba61d985c0a0e62c8238a705fb1e387b3",
                 JT: "ff4eb18a8d09c6561ab284ce409c673ad24be509",
                 LOC: "e35d1c7ac2bba3d2f0804a02dfa4ff6f17537089"}

CJK = re.compile(u"[\u3400-\u4dbf\u4e00-\u9fff]")
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
ROW = re.compile(r'^[ \t]*"([^"]+)":[ \t]*"((?:[^"\\]|\\.)*)",[ \t]*$', re.M)


def show(ref, path):
    r = subprocess.run(["git", "show", "%s:%s" % (ref, path)], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise SystemExit("SHOW_FAIL %s:%s" % (ref, path))
    return r.stdout.decode("utf-8", "replace")


def blob_of(ref, path):
    return subprocess.run(["git", "rev-parse", "%s:%s" % (ref, path)], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


def pairs(text):
    n = 0
    for m in TERN.finditer(text):
        if bool(CJK.search(m.group(1))) != bool(CJK.search(m.group(2))):
            n += 1
    return n


def dicts(text):
    en = text.split("const en: Dict = {", 1)[1].split("\n};", 1)[0]
    zh = text.split("const zhCN: Dict = {", 1)[1].split("\n};", 1)[0]
    return ({m.group(1): m.group(2) for m in ROW.finditer(en)},
            {m.group(1): m.group(2) for m in ROW.finditer(zh)},
            len(en.splitlines()), len(zh.splitlines()))


problems = []

# 0) blob 对拍
for path, sha in CLAIMED_BLOBS.items():
    got = blob_of(CAND, path)
    print("blob %s -> %s %s" % (path.split("/")[-1], got[:12], "OK" if got == sha else "MISMATCH got=" + got))
    if got != sha:
        problems.append("blob mismatch " + path)

# 1) 尺的复算
files_base = [l.strip() for l in subprocess.run(
    ["git", "ls-tree", "-r", "--name-only", BASE, "--", "frontend/src"], cwd=REPO,
    capture_output=True, text=True).stdout.splitlines() if l.strip().endswith((".ts", ".tsx"))]
counts_base, counts_cand, tot_base, tot_cand = Counter(), Counter(), 0, 0
for f in files_base:
    b = pairs(show(BASE, f))
    c = pairs(show(CAND, f))
    tot_base += b
    tot_cand += c
    if b or c:
        counts_base[f] = b
        counts_cand[f] = c
print("ruler recount: files read %d | %s=%d %s=%d delta=%d"
      % (len(files_base), BASE[:10], tot_base, CAND[:10], tot_cand, tot_base - tot_cand))
if tot_base - tot_cand != 20:
    problems.append("delta is %d, not 20" % (tot_base - tot_cand))
for path in (PC, JT):
    print("  %s: %d -> %d" % (path.split("/")[-1], counts_base.get(path, 0), counts_cand.get(path, 0)))
    if counts_cand.get(path, 0) != 0:
        problems.append(path + " still carries " + str(counts_cand.get(path, 0)) + " inline pairs")

# 2)+3) 新键的字节对账
en_b, zh_b, en_lines_b, zh_lines_b = dicts(show(BASE, LOC))
en_c, zh_c, _, _ = dicts(show(CAND, LOC))
new_keys = sorted(set(en_c) - set(en_b))
print("dictionary rows at base: en=%d zh=%d | new keys at candidate: %d"
      % (en_lines_b, zh_lines_b, len(new_keys)))
if not new_keys:
    problems.append("no new dictionary keys found -- the read is blind, not clean")
old_files = show(BASE, PC) + show(BASE, JT)
new_files = show(CAND, PC) + show(CAND, JT)
moved = 0
for k in new_keys:
    v_en, v_zh = en_c.get(k), zh_c.get(k)
    if v_en is None or v_zh is None or k in en_b or k in zh_b:
        problems.append("key %s not present on both sides or already existed" % k)
        continue
    hit_en, hit_zh = ('"%s"' % v_en) in old_files, ('"%s"' % v_zh) in old_files
    left_en, left_zh = old_files.count('"%s"' % v_en), new_files.count('"%s"' % v_en)
    if hit_en and hit_zh and new_files.count('"%s"' % v_zh) == 0 and left_en == 1:
        moved += 1
    else:
        problems.append("key %s: en-in-old=%s zh-in-old=%s en-left-at-candidate=%d zh-left=%d"
                        % (k, hit_en, hit_zh, left_en, new_files.count('"%s"' % v_zh)))
print("keys proven moved byte-identically: %d of %d" % (moved, len(new_keys)))

print("VERDICT %s" % ("RECOMPUTED OK" if not problems else "CHECK"))
for p in problems:
    print("  -", p)
sys.exit(0 if not problems else 1)
