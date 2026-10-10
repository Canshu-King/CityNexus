# -*- coding: utf-8 -*-
"""两点斜率：把两份盘趋势文件的「现空闲 + 时刻」各读一枚，算实测平均消耗，并据此重算到 2 GiB 档还要多久。

为什么要单独一枚（14:30）：07:24 那块交出去的外推用的是最陡的短窗口（+1.47 GiB/小时），
它承诺「今晚 17:49—23:42 落到 2 GiB 档」；到 14:16 那一拍根本还没到。
「同一批点、窗口不同就差 2.5 倍」这句话我自己在 `_disk_trend_0357.txt:13` 写过，却没拿它约束选窗。
这一枚只做一件事：取两个已落档的实测点，算它们之间的平均斜率——这是唯一不需要选窗的数。

用法：python _disk_two_point_r1.py [旧趋势文件] [新趋势文件]
边界：只读两份 txt 的第 1 行，0 次 df、0 次写盘（除 stdout）。两点之间的坑（清理让空闲回升）算不进平均。
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BAND_GIB = 2.0

def read_point(path):
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    m = re.search(u"现空闲 ([\\d.]+) GiB（(\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})）", txt)
    if not m:
        m2 = re.search(u"空闲 ([\\d.]+) GiB", txt)
        if not m2:
            raise SystemExit("读不到现空闲：%s" % path)
        raise SystemExit("读不到那个点的时刻：%s" % path)
    # 文件里的时刻只有「月-日 时:分:秒」，补年份不能硬写：取现年的两位数，若补出来的时刻比现在还晚（说明那条是去年 12 月的），退一年。
    y = int(time.strftime("%Y"))
    t = time.mktime(time.strptime("%d-%s" % (y, m.group(2)), "%Y-%m-%d %H:%M:%S"))
    if t > time.time() + 86400:
        t = time.mktime(time.strptime("%d-%s" % (y - 1, m.group(2)), "%Y-%m-%d %H:%M:%S"))
    return float(m.group(1)), m.group(2), t

def main():
    old_p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_disk_trend_0357.txt")
    new_p = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "_disk_trend_1424.txt")
    f0, s0, t0 = read_point(old_p)
    f1, s1, t1 = read_point(new_p)
    if t1 <= t0:
        raise SystemExit("两点顺序不对：新点 %s 不晚于旧点 %s" % (s1, s0))
    dh = (t1 - t0) / 3600.0
    df_ = f0 - f1
    rate = df_ / dh
    line1 = "两点实测：旧点 %s 空闲 %.2f GiB｜新点 %s 空闲 %.2f GiB" % (s0, f0, s1, f1)
    line2 = "跨度 %.2f 小时，空闲变化 %+.2f GiB ⇒ 平均消耗 %+.2f GiB/小时（这是两点之间的平均，不选窗）" % (dh, -df_, rate)
    line3 = ("按这个平均外推到 %.1f GiB 档还要 %.1f 小时（约 %s）——外推不是预测" % (
        BAND_GIB, (f1 - BAND_GIB) / rate, time.strftime("%m-%d %H:%M", time.localtime(t1 + (f1 - BAND_GIB) / rate * 3600)))
        ) if rate > 0 else "按这个平均，空闲在回升（%+.2f GiB/小时），够不到 %.1f GiB 档" % (rate, BAND_GIB)
    for x in (line1, line2, line3):
        print(x)
    io.open(os.path.join(HERE, "_disk_two_point_latest.txt"), "w", encoding="utf-8", newline="\n").write(
        "_disk_two_point_r1.py 于 %s｜输入 %s + %s\n%s\n%s\n%s\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(old_p), os.path.basename(new_p), line1, line2, line3))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
