# -*- coding: utf-8 -*-
"""盘紧贴「掉档才贴 / 回档上弦」的判定自测——直接重放 autumn_watch.py 里那段真代码。

为什么这么测：这一格 inline 在产品脚本里，跑整个脚本会真往总线贴（import 会发帖的那类教训）。
所以按 348–385 行的**行范围**取出原块、dedent、exec，`post_to_bus` 换成计数桩——判据必须来自
被守护的那段行为本身，不能另抄一份正则（抄窄了/抄宽了都会让自测全绿而产品照旧）。

覆盖的五条都是 10-03 00:25 实测撞出来的：C: 记着的下界停在 6，而它已经回到 8.07 又掉到 7.65，
旧写法既不会再贴、也不会把下界抬起来 ⇒ 白捡 1.65 GB 静默。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "autumn_watch.py")
LO, HI = 348, 385                     # 闭区间：frees = re.findall(...) 起，到「已发盘紧贴」止
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(SRC, encoding="utf-8").read().split(chr(10))
block = raw[LO - 1:HI]
assert "frees = re.findall" in block[0], block[0]
assert "已发盘紧贴" in block[-1], block[-1]
ind = len(block[0]) - len(block[0].lstrip())
code = chr(10).join(x[ind:] if x.startswith(" " * ind) or not x.strip() else x for x in block)


def run(body, st):
    posts = []

    def post_to_bus(text, key):
        posts.append((key, text))
        return "STUB-%d" % len(posts)

    logs = []

    def say(s):
        logs.append(s)

    g = {"re": re, "LOW_GB": 8.0, "body": body, "st": st, "post_to_bus": post_to_bus, "say": say,
         "time": __import__("time")}
    exec(compile(code, "autumn_watch.py:348-385", "exec"), g)
    return posts, logs, g["st"]


res = []


def check(name, got, want):
    ok = str(got) == str(want)
    res.append(ok)
    print(u"%s %s｜得 %s｜要 %s" % (u"过" if ok else u"红", name, got, want))


def body_of(reading):
    return "".join(u"磁盘 %s free=%.2f GB used=90.0%%\n" % (d, v) for d, v in reading.items())


# 1) 记着 6、现读 8.07（阈值上方）⇒ 只上弦，不贴
posts, logs, st = run(body_of({u"C:\\": 8.07, u"D:\\": 14.5}), {u"disk_bands": {u"C:\\": 6, u"D:\\": 1}})
check("回档只上弦不贴", len(posts), 0)
check("C: 下界抬到 8", st[u"disk_bands"][u"C:\\"], 8)
check("D: 下界抬到 14", st[u"disk_bands"][u"D:\\"], 14)
check("上弦要留一行话", len([x for x in logs if u"回弦" in x]), 2)

# 2) 记着 8、现读 7.65（已低于阈值）⇒ 这一拍必须贴（旧写法在这里哑）
posts, logs, st = run(body_of({u"C:\\": 7.65}), {u"disk_bands": {u"C:\\": 8}})
check("抬过下界之后再掉一档要贴", len(posts), 1)
check("贴的下界记成 7", st[u"disk_bands"][u"C:\\"], 7)
check("贴的键按盘名去重", posts[0][0], u"disk_C")

# 3) 同一档连着两拍 ⇒ 第二拍不许重复贴
posts2, _l, st2 = run(body_of({u"C:\\": 7.64}), st)
check("同档不重复贴", len(posts2), 0)

# 4) 再掉一档 ⇒ 又贴一次
posts3, _l, st3 = run(body_of({u"C:\\": 6.90}), st2)
check("再掉一档再贴一次", len(posts3), 1)
check("第二贴记成 6", st3[u"disk_bands"][u"C:\\"], 6)

# 5) 没记过的盘、且已在阈值下方 ⇒ 只种子不贴（免得跟着别人刚报过的数刷一遍）
posts4, logs4, st4 = run(body_of({u"C:\\": 5.20}), {u"disk_bands": {}})
check("首见只种子", len(posts4), 0)
check("种子写在 5", st4[u"disk_bands"][u"C:\\"], 5)
check("种子那行要说明为什么不贴", len([x for x in logs4 if u"种子" in x]), 1)

# 6) 真读数：把现读的 C:/D: 拿去跑一遍，只验「不炸、且判断与现值一致」
import shutil
real = {}
for d in (u"C:\\", u"D:\\"):
    real[d] = shutil.disk_usage(d).free / 1073741824.0
posts5, logs5, st5 = run(body_of(real), {u"disk_bands": {}})
check("现读跑通不抛（贴数=0，因为首见只种子）", len(posts5), 0)
print(u"   现读：C: %.2f GB｜D: %.2f GB｜种子后 %s" % (real[u"C:\\"], real[u"D:\\"], st5[u"disk_bands"]))

n_ok = len([x for x in res if x])
print(u"\n%d/%d 过" % (n_ok, len(res)))
sys.exit(0 if n_ok == len(res) else 1)
