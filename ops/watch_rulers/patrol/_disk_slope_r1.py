# -*- coding: utf-8 -*-
"""每枚盘的实测斜率：从 round_watch.log 的「===== [HH:MM:SS] round」+「磁盘 X free=…」成对读。

为什么不用旧的 `_disk_two_point_r1.py`：那一枚要人手给两份趋势文件，只有 D: 一格，
而 10-02 夜里真正可能出事的是 **C:**——全部会话流水（含 261 MB 一枚的）都落在
`C:\\Users\\仓鼠王\\.qoder\\projects\\D--moodle\\*.jsonl`，车道一起写的时候先干的是 C:。

时刻怎么钉：日志里只有 HH:MM:SS，没有日期。按「序号单调 + 回绕就加一天」推相对日，
再把**最后一拍**锚到文件 mtime；锚不上（差 >15 分）就 REFUSE，不猜。
斜率小于噪声阈值时**不给爆盘时刻**——±0.3 GB 的晃动不配换算成小时。
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("RW_LOG", os.path.join(HERE, "round_watch.log"))
OUT = os.path.join(HERE, "_disk_slope_latest.txt")
NOISE_GB = 0.05
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEAD = re.compile(r"^===== \[(\d\d):(\d\d):(\d\d)\] round")
DISK = re.compile(r"^\s+磁盘 (\S+) free=([\d.]+) GB used=([\d.]+)%")


def parse():
    cur = None
    pts = {}
    prev_sec = None
    day = 0
    seq_t = []
    for line in io.open(LOG, encoding="utf-8", errors="replace"):
        mh = HEAD.match(line)
        if mh:
            sec = int(mh.group(1)) * 3600 + int(mh.group(2)) * 60 + int(mh.group(3))
            if prev_sec is not None and sec < prev_sec - 600:
                day += 1                     # 秒数变小 ⇒ 跨过一次午夜（留 10 分回退余量）
            prev_sec = sec
            cur = day * 86400 + sec
            seq_t.append(cur)
            continue
        md = DISK.match(line)
        if md and cur is not None:
            d = md.group(1).rstrip("\\").rstrip("/")
            pts.setdefault(d, []).append((cur, float(md.group(2))))
    gaps = [seq_t[i + 1] - seq_t[i] for i in range(len(seq_t) - 1)]
    meta = {
        "rounds": len(seq_t),
        "day_rollovers": day,
        "gap_min": min(gaps) if gaps else 0,
        "gap_max": max(gaps) if gaps else 0,
        "gap_avg": (sum(gaps) / len(gaps)) if gaps else 0,
        "first": seq_t[0] if seq_t else 0,
        "last": seq_t[-1] if seq_t else 0,
    }
    return pts, meta


def main():
    if not os.path.exists(LOG):
        print(u"REFUSE：日志不在 %s" % LOG)
        return 1
    pts, meta = parse()
    if not pts:
        print(u"REFUSE：一行『磁盘 X free=』都没读到，尺没吃东西")
        return 1
    mt = os.path.getmtime(LOG)
    lt = time.localtime(mt)
    # 日志里的 HH:MM:SS 是**本地**钟点，锚也必须用本地当天秒数；用 int(mt)%86400 会差出一个时区（实测差 16 小时）
    last_abs_sec = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
    lines = [u"_disk_slope_r1.py 于 %s｜日志 %s｜读到 %d 拍、跨午夜回绕 %d 次、拍间隔 均 %.1f 分（最小 %.1f／最大 %.1f）" % (
        time.strftime("%Y-%m-%d %H:%M:%S", lt), os.path.basename(LOG), meta["rounds"],
        meta["day_rollovers"], meta["gap_avg"] / 60.0, meta["gap_min"] / 60.0, meta["gap_max"] / 60.0)]
    worst = []
    offset = 0.0
    anchor = mt
    for d in sorted(pts):
        seq = pts[d]
        if len(seq) < 2:
            lines.append(u"%s 只有 1 拍，算不出斜率（不给爆盘时刻）" % d)
            continue
        t0, f0 = seq[0]
        t1, f1 = seq[-1]
        # 锚：把「最后一拍的秒数」贴到 mtime 的当天秒数上，反推整段的绝对时刻
        offset = last_abs_sec - (t1 % 86400)
        span_h = (t1 - t0) / 3600.0
        rate = (f0 - f1) / span_h if span_h > 0 else 0.0
        anchor = mt - offset
        lines.append(u"{d}：首拍 {f0:.1f} GB｜末拍 {f1:.1f} GB｜跨度 {sp:.2f} 小时 ⇒ 平均消耗 {r:+.2f} GB/小时".format(
            d=d, f0=f0, f1=f1, sp=span_h, r=rate))
        if abs(rate) < NOISE_GB:
            lines.append(u"   这枚盘的斜率在噪声里（|%.2f| < %.2f GB/h）⇒ **不给爆盘时刻**；末拍 %.1f GB 只是现值" % (
                abs(rate), NOISE_GB, f1))
        else:
            for band in (8.0, 2.0):
                if f1 > band:
                    hrs = (f1 - band) / rate
                    lines.append(u"   到 %.0f GB 档：按这个平均还要 %.1f 小时（约 %s）——外推不是预测" % (
                        band, hrs, time.strftime("%m-%d %H:%M", time.localtime(anchor + hrs * 3600))))
                else:
                    lines.append(u"   到 %.0f GB 档：**已经低于这一档**（现 %.1f GB）" % (band, f1))
            worst.append((d, rate, f1))
        # 近 12 拍的最低值一起给：整段平均会把「早上清过一轮」的回升抹平
        tail = seq[-12:]
        lines.append(u"   近 %d 拍：最低 %.1f GB、最高 %.1f GB（同一枚盘，别只看平均）" % (
            len(tail), min(x[1] for x in tail), max(x[1] for x in tail)))
    anchor = mt - offset
    chk = abs(int(offset))
    lines.append(u"锚核对：末拍的钟点 %s、日志 mtime 的钟点 %s ⇒ 差 %d 秒（>900 就不可信）；整段跨度按锚算是 %.2f 小时" % (
        time.strftime("%H:%M:%S", time.localtime(anchor)), time.strftime("%H:%M:%S", time.localtime(mt)),
        chk, (meta["last"] - meta["first"]) / 3600.0))
    if chk > 900:
        lines.append(u"警告：末拍与 mtime 对不上，跨午夜回绕可能数错了 ⇒ 上面所有 ETA 一律不作数")
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
