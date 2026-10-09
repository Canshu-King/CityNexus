# -*- coding: utf-8 -*-
"""C: 撑不撑得到明天 11:00 —— 用实测斜率回答，不外推「每天涨 8G」那种旧账。

取两拍：会话流水目录里所有 .jsonl 的字节和，间隔 SAMPLE_S 秒；
顺带报最大单文件、以及非会话那部分（C: 剩余空间）自己的降速。
"""
import glob
import io
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SAMPLE_S = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def snap():
    tot = 0
    n = 0
    big = (0, u"")
    for p in glob.glob(os.path.join(PROJ, "*.jsonl")):
        try:
            s = os.path.getsize(p)
        except OSError:
            continue
        tot += s
        n += 1
        if s > big[0]:
            big = (s, os.path.basename(p))
    return tot, n, big, shutil.disk_usage("C:/").free


a, na, biga, fa = snap()
t0 = time.time()
time.sleep(SAMPLE_S)
b, nb, bigb, fb = snap()
dt = time.time() - t0
growth = b - a
rate_h = growth / dt * 3600.0
free_drop = fa - fb
print(u"取样窗口 %d 秒｜流水 %d 枚，字节和 %d -> %d（净增 %d B）" % (int(dt), na, a, b, growth))
print(u"会话增长斜率 %.2f GB/小时" % (rate_h / 2**30,))
print(u"C: 剩余 %.2f -> %.2f GB（这 %d 秒里降 %.1f MB）" % (fa / 2**30, fb / 2**30, int(dt), free_drop / 2**20))
print(u"最大单文件 %.1f MB（%s）" % (bigb[0] / 2**20, bigb[1][:40]))
if rate_h > 0:
    print(u"照这一窗的斜率，C: 现有 %.2f GB 还能撑 %.1f 小时（只算会话流水，不含别的写盘）" % (fb / 2**30, fb / rate_h))
else:
    print(u"这一窗没增长（斜率为零）——单窗不能当结论，要连着看几窗")
