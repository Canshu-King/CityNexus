# -*- coding: utf-8 -*-
"""重启后清点：哪些扇在关机前还在写、重启后一直没回来；顺带数收件口开机后进了几枚块。

为什么要它：今天已经第三次重启（14:06 / 22:11 / 23:49），KB5129195 那个注册表 hive 回归
还会继续咬。两版弯路都记在这：
  v1 拿**文件 mtime** 判「重启前在不在写」——重启后一写就把断点整个盖掉，[A][B][C] 三格全空
     （00:05 实跑），那是尺瞎不是车队齐；
  v2 改成扫尾部 3 MB 找断点——但一扇窗写流水约 2 MB/s（09-25 实测），14 分钟就够把断点推出窗口。
所以这里对**断点**用二分（流水是追加写、时间戳单调 ⇒ 谓词单调，log2 次小读就能钉准），
只有「重启后有没有写过」这一步用 mtime 当粗证，并且它只用来做二分下界，不当结论。
判不出就具名写「不可得」，不许把「没扫到」写成「静着」。

只读：不发消息、不碰进程、不动账本。
"""
import io
import json
import os
import sys
import time

PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FLEET = [
    "494abfd7", "42d1a6fa",
    "6a150e1e", "da46954a", "5a53846b", "8ac89982", "2d2d7428",
    "e766b154", "6a773af1", "0afdb49b", "1ba48dbf", "82f55d8a", "1d64acf5",
    "cff87c64",
]


def epoch_of(ts):
    """三形制都认：ISO 带 Z（UTC，timegm）、毫秒 epoch、秒 epoch。"""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        return v / 1000.0 if v > 1e11 else v
    s = str(ts).strip()
    if s.endswith("Z"):
        import calendar
        for f in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return calendar.timegm(time.strptime(s[:-1], f))
            except Exception:
                continue
        return None
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19], f))
        except Exception:
            continue
    return None


def boot_epoch(arg):
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return time.mktime(time.strptime(arg, f))
        except Exception:
            continue
    return None


def ts_at(f, off):
    """从 off 起对齐到一条完整记录，返回 (时间戳, 该记录末尾偏移)；拿不到返回 (None, None)。"""
    f.seek(off)
    f.readline()                     # 丢掉可能被截断的首行
    for _ in range(6):
        line = f.readline()
        if not line:
            return None, None
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue                  # 超长行/损坏行：往下再试几枚
        e = epoch_of(r.get("timestamp"))
        if e is not None:
            return e, f.tell()
    return None, None


def last_before(path, b, max_probe=26):
    """二分出「时间戳 <= b」的最大记录时刻（流水单调 ⇒ 谓词单调）。拿不到返回 None。"""
    with io.open(path, "rb") as f:
        size = os.path.getsize(path)
        lo, hi = 0, size
        best = None
        for _ in range(max_probe):
            if hi - lo < 4096:
                break
            mid = (lo + hi) // 2
            e, nxt = ts_at(f, mid)
            if e is None:
                hi = mid
                continue
            if e <= b:
                best = e
                lo = mid
            else:
                hi = mid
        if best is None:
            return None
        # 往前再走几步，把「同段里最后一条 <= b」钉准（二分只保证量到那一段）
        f.seek(lo)
        cur = None
        for _ in range(400):
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            e = epoch_of(r.get("timestamp"))
            if e is None:
                continue
            if e <= b:
                cur = e
            else:
                break
        return cur if cur is not None else best


def path_of(prefix):
    cands = [p for p in os.listdir(PROJ) if p.startswith(prefix) and p.endswith(".jsonl")]
    return os.path.join(PROJ, cands[0]) if cands else None


def first_after(path, b):
    """二分找「时间戳 > b」的第一条记录时刻——即复工第一笔，不是末笔。"""
    with io.open(path, "rb") as f:
        size = os.path.getsize(path)
        lo, hi = 0, size
        cand = None
        for _ in range(26):
            if hi - lo < 4096:
                break
            mid = (lo + hi) // 2
            e, _n = ts_at(f, mid)
            if e is None:
                hi = mid
                continue
            if e > b:
                cand = e
                hi = mid
            else:
                lo = mid
        if cand is None:
            e, _n = ts_at(f, max(0, size - 1))
            return None
        # 往前退到这一段开头，取这一段里第一条 > b 的
        f.seek(max(0, lo - 2000000))
        first = None
        for _ in range(4000):
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            e = epoch_of(r.get("timestamp"))
            if e is None:
                continue
            if e > b:
                first = e
                break
        return first if first is not None else cand


def main():
    if len(sys.argv) < 2:
        print(u"用法: python _reboot_census_r1.py '2026-10-02 23:49:41'")
        return 2
    b = boot_epoch(sys.argv[1])
    if b is None:
        print(u"REFUSE：开机时刻解析不出来，不想拿错基准去判谁死了")
        return 2
    now = time.time()
    if not (0 < now - b < 6 * 3600):
        print(u"REFUSE：基准距现在 {:.0f} 分钟，不在 0~360 分钟里 ⇒ 钟点或时区不对，拒判".format((now - b) / 60.0))
        return 2
    hm = lambda e: time.strftime("%H:%M:%S", time.localtime(e)) if e else u"—"
    print(u"现在 %s｜开机 %s｜已 %d 分｜断点用流水时间戳二分，mtime 只当粗证" % (
        hm(now), hm(b), int((now - b) / 60)))

    rows = []
    for pre in FLEET:
        cands = [p for p in os.listdir(PROJ) if p.startswith(pre) and p.endswith(".jsonl")]
        if not cands:
            print(u"  %-9s 流水不在（换名/删除？）" % pre)
            continue
        path = os.path.join(PROJ, cands[0])
        mt = os.path.getmtime(path)
        before = last_before(path, b)
        after = mt if mt > b + 5 else None      # 重启后写过 ⇒ mtime 就是复工时刻（粗证）
        rows.append((pre, before, after, mt, os.path.getsize(path)))

    # 只有「关机前 25 分内还落过字」才算手上正有活；否则是早就静着，别赖这次重启
    live = [r for r in rows if r[1] is not None and (b - r[1]) <= 25 * 60]
    cov = [r for r in live if r[2] is not None]
    print(u"\n关机前 25 分内在写 {a} 扇：已复工 {b1} 扇、仍未回来 {b2} 扇｜与本次无关（早静着或断点量不到）{c} 扇".format(
        a=len(live), b1=len(cov), b2=len(live) - len(cov), c=len(rows) - len(live)))

    print(u"\n[A] 回到岗位（断点＝关机前最后一笔；复工＝重启后第一笔；末笔＝现在写到哪）：")
    k = 0
    for pre, before, after, mt, sz in sorted(cov, key=lambda x: -x[1]):
        k += 1
        fa = first_after(path_of(pre), b)
        print(u"  {p:<9} 断在 {hb} → 复工 {ha} → 末笔 {mt}（断 {gap} 分｜流水 {mb} MB）".format(
            p=pre, hb=hm(before), ha=hm(fa), mt=hm(mt),
            gap=int(((fa if fa is not None else mt) - before) / 60),
            mb=round(sz / 1048576.0, 1)))
    if not k:
        print(u"  （无）")

    print(u"\n[B] 关机前手上还在落字、到现在没回来的（这些是被断的，不是交完在等）：")
    k = 0
    for pre, before, after, mt, sz in sorted(live, key=lambda x: -x[1]):
        if after is None:
            k += 1
            print(u"  %-9s 末笔 %s｜已静 %d 分" % (pre, hm(before), int((now - before) / 60)))
    if not k:
        print(u"  （无）")

    print(u"\n[C] 与这次重启无关（关机前 25 分之外就静着；断点量不到会明写）：")
    k = 0
    for pre, before, after, mt, sz in sorted(rows, key=lambda x: -x[3]):
        if not (before is not None and (b - before) <= 25 * 60):
            k += 1
            tag = hm(before) if before is not None else u"断点量不到"
            back = u"（已复工，末笔 %s）" % hm(mt) if after is not None else u""
            print(u"  {p:<9} 断机时末笔 {e}｜文件 mtime {m}｜静 {h} 小时{bk}".format(
                p=pre, e=tag, m=time.strftime("%m-%d %H:%M", time.localtime(mt)),
                h=int((now - (before if before is not None else mt)) / 3600), bk=back))
    if not k:
        print(u"  （无）")

    print(u"\n[D] 收件口：开机时刻之后新落的块（唯一能证明「真的交了货」的东西）")
    nb = 0
    if os.path.isdir(INBOX):
        for p in sorted(os.listdir(INBOX)):
            fp = os.path.join(INBOX, p)
            if not os.path.isfile(fp):
                continue
            mt = os.path.getmtime(fp)
            if mt > b:
                nb += 1
                print(u"  %-52s %s %6d B" % (p[:52], hm(mt), os.path.getsize(fp)))
    print(u"  共 %d 枚" % nb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
