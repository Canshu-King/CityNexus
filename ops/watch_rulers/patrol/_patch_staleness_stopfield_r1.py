# -*- coding: utf-8 -*-
u"""给 _stack_staleness_check_r1.py 扩一格：stale 的腿要说清"实际几点收工、现在要不要重启"。

为什么扩（10-06 17:4x）：那把尺只会比"进程起 vs 文件改于"，于是我 17:32 改了两条腿的默认 STOP、
**故意没重启**（它们 env 传对了、正在干活），尺就报两条「跑的是改前代码，要重启」——红是红的，
但它答的不是该答的问题。真问题是"这条腿**实际**到几点收工、够不够撑到你这一班的下班"。
扩展后：对**带收工时刻的腿**，报它的实际 STOP（从 env／默认现读，用该腿自己的解析形制），
  实际到点已过 ⇒ 立刻重启；到点仍晚于下班 ⇒ 标「看着旧·不必现在动」，退出码不因它红。

不改原尺的判定逻辑（stale 仍按文件／进程比对报），只是给 stale 的条目补一个"要不要现在动"的答案。
落盘前 ast.parse；两处锚各须命中一次。
跑法：python _patch_staleness_stopfield_r1.py --check / 直接跑
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "_stack_staleness_check_r1.py")

# ① LEGS 后面加一段 STOP 解析（纯 HHMM / MMDD-HHMM 两形，与各腿 stop_at 同形）
OLD1 = u'''Q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | "
     "ForEach-Object { [PSCustomObject]@{pid=$_.ProcessId;cl=$_.CommandLine;"
     "start=$_.CreationDate} } | ConvertTo-Csv -NoTypeInformation")
'''
NEW1 = OLD1 + u'''

# 每条腿的收工时刻从哪儿取：先 env（它启动时真正拿到的那个），取不到就用它文件里的默认值。
# 形制与各腿自己的 stop_at 一致：`HHMM`＝今天该刻、`MMDD-HHMM`＝指定那天。
STOP_ENV = {
    u"supervise": u"SUP_STOP",
    u"keepalive": u"SENTINEL_STOP",
    u"sentinel": u"SENTINEL_STOP",
    u"keeper": u"STACK_KEEPER_STOP",
    u"inbox_applier": u"APPLIER_STOP",
    u"verdict": u"NVR_AT",
}
STOP_DEFAULT = {
    u"supervise": u"2340",
    u"keepalive": u"2335",
    u"sentinel": u"2335",
    u"keeper": u"2340",
    u"inbox_applier": u"2340",
    u"verdict": u"23:00:20",
}


def stop_epoch(leg):
    """这条腿的**实际**收工时刻（epoch 秒）。取不到返回 None——不猜。"""
    raw = os.environ.get(STOP_ENV.get(leg, u""), u"") or STOP_DEFAULT.get(leg)
    if not raw:
        return None
    raw = str(raw)
    try:
        if "-" in raw:
            md, hm = raw.split("-", 1)
            base = u"%s-%s-%s" % (time.strftime(u"%Y"), md[:2], md[2:])
        else:
            base = time.strftime(u"%Y-%m-%d")
            hm = raw
        h, m = int(hm[:2]), int(hm[2:4])
        return time.mktime(time.strptime(base + u" %02d:%02d:00" % (h, m),
                                          u"%Y-%m-%d %H:%M:%S"))
    except Exception:
        return None
'''

# ② 打印 stale 那行时，把"实际几点收工／现在要不要动"补上
OLD2 = u'''            elif r[u"verdict"] == u"stale":
                sys.stdout.write(u"  !! %-13s 进程起 %s 早于文件改于 %s ⇒ **跑的是改前代码，要重启这一腿**\\n"
                                 % (r[u"leg"], f(r.get(u"proc_start")), f(r.get(u"file_mtime"))))'''
NEW2 = u'''            elif r[u"verdict"] == u"stale":
                e = stop_epoch(r[u"leg"])
                if e is None:
                    tail = u"这条腿不带收工时刻 ⇒ 按老规矩：重启"
                elif e <= time.time():
                    tail = u"**实际到点已过（%s）⇒ 立刻重启**" % f(e)
                else:
                    tail = (u"实际到点 %s（还有 %d 分）⇒ 只是看着旧，**不必现在动**，"
                            u"让它自然重启时带上新代码" % (f(e), (e - time.time()) / 60.0))
                sys.stdout.write(u"  !! %-13s 进程起 %s 早于文件改于 %s ⇒ 跑的是改前代码；%s\\n"
                                 % (r[u"leg"], f(r.get(u"proc_start")), f(r.get(u"file_mtime")), tail))'''

EDITS = [(OLD1, NEW1), (OLD2, NEW2)]


def main():
    t = io.open(T, encoding="utf-8").read()
    if u"stop_epoch" in t:
        print(u"已装过（文件里有 stop_epoch），不重复写")
        return 0
    for i, (old, new) in enumerate(EDITS):
        n = t.count(old)
        if n != 1:
            print(u"REFUSE：第 %d 处锚命中 %d 次，要 1 次 ⇒ 未写盘：%r" % (i + 1, n, old[:56]))
            return 1
    for old, new in EDITS:
        t = t.replace(old, new)
    ast.parse(t)
    if u"--check" in sys.argv:
        print(u"--check：两处锚各命中一次、替换后 ast 过（未写盘）")
        return 0
    io.open(T, "w", encoding="utf-8", newline="\n").write(t)
    print(u"已写 _stack_staleness_check_r1.py：stale 条目补「实际几点收工、现在要不要重启」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
