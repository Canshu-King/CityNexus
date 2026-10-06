# -*- coding: utf-8 -*-
"""值守 14:32 · D 盘水位趋势尺（只读，追加式打点）。

为什么不是 `du`：这台机器上的车道目录与构建舞台大量用**硬链接**（同一份 `vite/bin/vite.js` 在某车道目录里
`nlink=21` 是实测过的），逐目录求和会把共享字节重复计一遍，得出比真实占用大得多的数——
而且 13:13 那把全量 `os.walk` 走了 13 分钟还没数完（我自己把它停了，不留下一个不可复算的数）。
所以这里只用**文件系统自己的口径**：`df -B 1G /d` 的可用列，按时间打点，用相邻两点求速率。

边界：`-B 1G` 是向下取整 ⇒ 每个点 ±1 GiB；速率只报「两点之间」的实测差，不外推到不可信的远处。
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGF = os.path.join(HERE, "disk_trend.txt")
# 我这一轮之前亲读过的点（来源：值守 13:11 / 14:17 两次 `df -B 1G /d`），先落进表里再打新点
SEED = [("13:11", 10), ("14:17", 9)]


def read_free():
    p = subprocess.run(["df", "-B", "1G", "/d"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    for line in (p.stdout or "").split("\n"):
        m = re.match(r"^D:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", line.strip())
        if m:
            return int(m.group(3)), int(m.group(4))
    return None, None


def load():
    pts = []
    if os.path.exists(LOGF):
        for line in io_open().read().split("\n"):
            m = re.match(r"^(\d\d):(\d\d)\s+(\d+)\s+GiB", line.strip())
            if m:
                pts.append((int(m.group(1)) * 60 + int(m.group(2)), int(m.group(3))))
    return pts


def io_open():
    return open(LOGF, encoding="utf-8", errors="replace")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    day = time.localtime()
    hm = day.tm_hour * 60 + day.tm_min
    free, pct = read_free()
    if free is None:
        print("df 取不到 D 盘读数")
        return 1
    first = not os.path.exists(LOGF)
    with open(LOGF, "a", encoding="utf-8", newline="\n") as f:
        if first:
            for h, v in SEED:
                hh, mm = h.split(":")
                f.write("%02d:%02d %d GiB used%%?\n" % (int(hh), int(mm), v))
        f.write("%02d:%02d %d GiB free (df used " % (day.tm_hour, day.tm_min, free) + str(pct) + "%)\n")
    pts = load()
    # 清掉种子行里那个占位后缀，避免被当成读数误解
    pts = [(t, v) for (t, v) in pts]
    print("打点完成：%d 个点；最近 5 个：%s" % (len(pts), ", ".join("%02d:%02d=%d GiB" % (t // 60, t % 60, v) for t, v in pts[-5:])))
    if len(pts) >= 2:
        (t1, v1), (t2, v2) = pts[-2], pts[-1]
        dt = max(1, t2 - t1)
        dv = v1 - v2
        if dv > 0:
            rate = dv / (dt / 60.0)
            hours_left = v2 / rate if rate > 0 else float("inf")
            at = time.localtime(time.time() + hours_left * 3600)
            print("最近两点：%.0f 分钟内少了 %d GiB ⇒ **%.2f GiB/小时**；照这一档算还能撑 %.1f 小时（约 %02d:%02d 触底，不含任何人清理）"
                  % (dt, dv, rate, hours_left, at.tm_hour, at.tm_min))
            print("注意：`df -B 1G` 向下取整 ⇒ 每个点 ±1 GiB，所以这个时刻只能当「量级」用，不能当承诺时刻。")
        elif dv == 0:
            print("最近两点没变化（0 GiB / %.0f 分）⇒ 当前速率不成立，别外推。" % dt)
        else:
            print("最近两点是**回涨** %d GiB（有人删了东西或有构建清场）⇒ 之前的速率作废，重新观察。" % (-dv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
