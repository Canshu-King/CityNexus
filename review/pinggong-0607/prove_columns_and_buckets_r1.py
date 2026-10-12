# -*- coding: utf-8 -*-
"""两件事：一、证明盖章副本里除 carried 与 absorbed_on 之外没有任何一列被改；
二、把四十一条的「在线上几成」分桶，给交块用。"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
BARE = "D:/moodle/CityNexus"
TIP = subprocess.run(["git", "-C", BARE, "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.split("\t")[0]
NEW = "D:/moodle/_qoder_pinggong_0588/docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"  # 直接对枝上那枚交付字节复算

old = subprocess.run(["git", "-C", REPO, "show", "%s:docs/REVOLUTION_ABSORPTION_MANIFEST.tsv" % TIP],
                     capture_output=True, text=True, encoding="utf-8").stdout
new = open(NEW, encoding="utf-8").read()
o = [ln for ln in old.split("\n") if ln.strip()]
n = [ln for ln in new.split("\n") if ln.strip()]
cols = o[0].split("\t")
print("现尖 %s" % TIP)
print("原表 %d 行｜盖章表 %d 行" % (len(o), len(n)))
touched = {}
for i, (a, b) in enumerate(zip(o, n)):
    fa, fb = a.split("\t"), b.split("\t")
    assert len(fa) == len(fb) == len(cols), "第 %d 行列数不等" % i
    for c, name in enumerate(cols):
        if fa[c] != fb[c]:
            touched.setdefault(name, 0)
            touched[name] += 1
print("被改动的列（列名 -> 改动行数）：%s" % touched)
assert set(touched) <= {"carried", "absorbed_on"}, "改动面越界，交块不能这么写"

buckets = {"9成以上": 0, "5-9成": 0, "1-5成": 0, "不足1成": 0, "零": 0}
rows = [dict(zip(cols, ln.split("\t"))) for ln in n[1:]]
for row in rows:
    carried = row["carried"]
    if "/" not in carried:
        continue
    frac = float(carried.split()[1].split("/")[0]) / float(carried.split()[1].split("/")[1])
    if frac == 0:
        buckets["零"] += 1
    elif frac >= 0.9:
        buckets["9成以上"] += 1
    elif frac >= 0.5:
        buckets["5-9成"] += 1
    elif frac >= 0.1:
        buckets["1-5成"] += 1
    else:
        buckets["不足1成"] += 1
print("四十一条按「自己的改动里已在线上几成」分桶：%s" % buckets)
print("carried 取值种类：%s" % sorted({r["carried"].split()[0] for r in rows}))
print("absorbed_on 非空 %d 条" % len([r for r in rows if r["absorbed_on"].strip()]))
