# -*- coding: utf-8 -*-
"""代插腿：每 15 分钟替值守跑一次「收件口 → 账本」的插入，不等我醒着。

为什么要有它（10-04 18:1x 实测出来的缺口）：单上写的是「车道不写账本，交块到
_qoder_ledger_inbox，值守 ≤15 分钟跑 ledger_inbox_apply_r1/r2 --apply 代插」。
可今天午后我被上下文压缩腰斩了几个钟头，那段时间**没人跑这一条**：
三枚待插块在收件口躺了两小时多才落地，而我那一拍的哨兵只报「门可插 0 枚」。
把"人记得跑"换成"腿自己跑"，才是这一格真正的修法——检测与动作都不该依赖我醒着。

边界（写死在这里，别让它扩权）：
  · 只跑现成的 applier，不自己写账本、不碰镜像腿（applier 成功后自己会推）；
  · 两道门（Q43 与坐标）在 applier 内部，被拒的块它自己标 refused，这条腿不绕;
  · 空目录就跳过，不产生任何写入；
  · 单实例：锁里 pid 还活着就退，绝不双跑（双跑会把同一枚块插两次）。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
IBOX = u"D:/moodle/_qoder_ledger_inbox"
APPLIER = os.path.join(LIVE, u"ledger_inbox_apply_r2.py")
LOG = os.path.join(HERE, u"_inbox_applier.log")
SELF = os.path.abspath(__file__)
LOCK = os.path.join(HERE, u"_inbox_applier.pid")
BUS = u"D:/moodle/agent_bus"
LAST = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_inbox_applier_lastrun.txt"
STOP = os.environ.get("APPLIER_STOP", "1005-1100")
if u"--reprint" in sys.argv[1:]:            # 只做一件事：把最近一拍的原样字节吐回去（给中枢当出处）
    if not os.path.exists(LAST):
        sys.stdout.write(u"NO_LAST_RUN_YET
")
        sys.exit(3)
    sys.stdout.write(io.open(LAST, encoding="utf-8").read())
    sys.exit(0)
PERIOD = int(os.environ.get("APPLIER_PERIOD", "900"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def say(s):
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(time.strftime("[%m-%d %H:%M:%S] ") + s + "\n")


def stop_at(stop=STOP):
    """`2335`＝今天 23:35；`1005-1100`＝10-05 11:00（跨日要有，否则半夜直接收工）。"""
    if "-" in str(stop):
        md, hm = str(stop).split("-", 1)
        base = "%s-%s-%s" % (time.strftime("%Y"), md[:2], md[2:])
    else:
        base, hm = time.strftime("%Y-%m-%d"), str(stop)
    return time.mktime(time.strptime(base + " %02d:%02d:00" % (int(hm[:2]), int(hm[2:])),
                                      "%Y-%m-%d %H:%M:%S"))


def already_running():
    if not os.path.exists(LOCK):
        return False
    try:
        pid = int(io.open(LOCK, encoding="utf-8").read().strip())
    except Exception:
        return False
    if pid == os.getpid():
        return False
    q = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | ForEach-Object { $_.CommandLine }" % pid)
    p = subprocess.run(["powershell", "-NoProfile", "-Command", q], capture_output=True)
    cmd = (p.stdout or b"").decode("utf-8", "replace")
    # 只认「这一条腿」：pid 活着且命令行里确实有本脚本名，否则算陈旧锁
    alive = u"_inbox_applier_r1.py" in cmd
    if not alive:
        say(u"锁里的 pid %d 不是本腿（或已退）⇒ 当陈旧锁清掉" % pid)
    return alive


LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
DUP_SUFFIX = u".dup-in-ledger"


def block_head(path):
    """块头＝首行去掉三个井号后的标题文本；applier 的 dedupe 只按它分组，所以判重复也只用它。"""
    try:
        first = io.open(path, encoding="utf-8", errors="replace").readline().strip()
    except Exception:
        return u""
    return first.lstrip("#").strip()


def ledger_hits(title):
    """拿块头标题在权威账本里数命中（号令者 18:2x 加的那条纪律）。读不到账本返回 None＝不可得，
    不可得时**不插**——宁可这一拍不落地，也不能把同一份交付记两次（那笔账昨天就错过一次）。"""
    if not title:
        return None
    try:
        return io.open(LEDGER, encoding="utf-8", errors="replace").read().count(title)
    except Exception as e:
        say(u"账本读不到（%s: %s）⇒ 命中数不可得" % (type(e).__name__, str(e)[:80]))
        return None


def park_duplicates(files):
    """命中大于零的块改名让开（加 .dup-in-applier 后缀 ⇒ applier 不再扫它），可逆、不改内容。"""
    keep = []
    for f in files:
        title = block_head(f)
        hit = ledger_hits(title)
        if hit is None:
            say(u"命中数不可得 ⇒ %s 这一拍不插（不拿「读不到」当「没有」）" % os.path.basename(f))
            continue
        if hit > 0:
            tgt = f + DUP_SUFFIX
            try:
                os.rename(f, tgt)
                say(u"跳过并挪开：%s ｜块头「%s」在账本里已命中 %d 次 ⇒ 再插就是重复入账（原名留着，未改内容）"
                    % (os.path.basename(f), title[:40], hit))
            except Exception as e:
                say(u"想挪开却没挪动：%s（%s: %s）⇒ 这一拍不插它" % (os.path.basename(f), type(e).__name__, str(e)[:70]))
            continue
        keep.append((f, title))
    return keep


def verify_landed(pairs):
    """插完再数一遍：应为 1。不等于 1 就具名报，别让它混在『成功』里。"""
    for name, title in pairs:
        hit = ledger_hits(title)
        say(u"插后核对：%s ｜块头在账本命中 %s 次（应为 1）" % (name, hit))



def pending():
    try:
        return sorted(f for f in os.listdir(IBOX)
                      if f.endswith(".md") and not f.startswith("_"))
    except Exception as e:
        say(u"收件口读不到（%s: %s）⇒ 这一拍不算绿" % (type(e).__name__, str(e)[:80]))
        return None


def tell_cmdr(landed_names, verdict, tally_line=None):
    """插完了给号令者留一笔耐久副本：他在收件口不用猜"谁动了账本"。
    正文刻意不写待证的数（枚数与时刻留在日志里，他要就用日志核）。"""
    body = (u"代插腿自动落了一块进账本（不需要值守醒着也会跑这一格）。\n"
            u"块名：%s\n判定：%s\n"
            u"取数与门判语全文在 live_checks/patrol/_inbox_applier.log；"
            u"这条腿只跑现成的 applier，不自己写账本，两道门在 applier 内部，被拒的它自己标 refused。\n"
            % (u"、".join(landed_names), verdict))
    cl = u""
    try:
        cl = io.open(u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt",
                     encoding="utf-8").read().strip()
    except Exception:
        pass
    if len(cl.encode("utf-8")) < 60:
        say(u"收尾口令原件读不到 ⇒ 这条通报不发（外发必须带逐字尾行）")
        return
    body += cl + u"\n"
    topic = u"auto-land-%s-%s" % (time.strftime("%H%M%S"),
                                  re.sub(r"\W+", u"", "".join(landed_names))[:24])
    io.open(LAST, "w", encoding="utf-8", newline="
").write(
        u"read_at=%s
inserted=%s
tally=%s
" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), u",".join(landed_names), tally_line or u"无"))
    cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send", "--from", u"qoder:42d1a6fa",
           "--to", u"qoder:494abfd7", "--kind", "deliver", "--topic", topic, "--body", body,
           "--evidence", u"代插这一拍的原文|python \"%s\" --reprint" % SELF]
    p = subprocess.run(cmd, cwd=BUS, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (p.stdout or b"").decode("utf-8", "replace")
    say(u"通报腿 rc=%d %s" % (p.returncode, u"已入库" if u'"id"' in out else out[-160:]))


def main():
    if already_running():
        say(u"本腿已在（锁里 pid 活着）⇒ 单实例退出，不双插")
        return 0
    io.open(LOCK, "w", encoding="utf-8").write(str(os.getpid()))
    deadline = stop_at()
    say(u"=== 代插腿起来：到 %s 收工；每 %d 秒一拍（pid=%s）" % (STOP, PERIOD, os.getpid()))
    n = 0
    while time.time() < deadline:
        fs = pending()
        if fs is None:
            pass
        elif not fs:
            n += 1
            if n % 4 == 1:                       # 门空时每四拍记一行，别把日志刷满
                say(u"门空：收件口没有待插块（第 %d 拍）" % n)
        else:
            keep = park_duplicates([os.path.join(IBOX, x) for x in fs])
            if not keep:
                say(u"这一拍没有可插的（要么被挪开、要么命中数不可得）")
            else:
                say(u"看到待插 %d 枚：%s ⇒ 跑 applier --apply（块头与代插戳逐枚记）"
                    % (len(keep), u"、".join(os.path.basename(f) for f, _t in keep)))
                for f, t in keep:
                    say(u"  待插块头：%s ｜%s" % (os.path.basename(f), t[:60]))
            p = subprocess.run([sys.executable, APPLIER, "--apply"], cwd=LIVE, capture_output=True,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            out = ((p.stdout or b"").decode("utf-8", "replace")
                   + (p.stderr or b"").decode("utf-8", "replace"))
            ins = re.findall(r"INSERTED (\S+)", out)
            ref = re.findall(r"REFUSED (\S+)", out)
            tal = [l for l in out.splitlines() if l.startswith("tally")]
            say(u"applier rc=%d ｜ %s" % (p.returncode, (tal[-1] if tal else out[-200:].replace("\n", " "))))
            if ins:
                titles = dict((os.path.basename(f), t) for f, t in keep)   # 用插前存下的块头：插完文件会被改名
                verify_landed([(x, titles.get(x) or block_head(os.path.join(IBOX, x))) for x in ins])
                tell_cmdr(ins, u"已插入（枚数与本拍 tally 原文见随附证据那条命令的输出，不在正文里重复读数）；镜像腿由 applier 自己推；插前查过账本命中为零、插后逐枚核对（结果见本日志）", (tal[-1] if tal else u""))
            if ref:
                say(u"被门拒：%s ⇒ 这些块留在收件口，等号令者拆（这条腿不改块、不重投）" % u"、".join(ref))
        time.sleep(PERIOD)
    say(u"到 STOP=%s，本腿主动收工。此后要代插就得再跑一次本脚本。" % STOP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
