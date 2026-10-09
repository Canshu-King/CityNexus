# -*- coding: utf-8 -*-
"""代插腿 r2：每 15 分钟替值守跑一次「收件口 → 账本」的插入，不等我醒着。

为什么要有它（10-04 18:1x 实测出来的缺口）：单上写的是「车道不写账本，交块到收件口，值守
一刻钟内跑 applier --apply 代插」。可今天午后我被上下文压缩腰斩了几个钟头，那段时间
**没人跑这一条**：三枚待插块在收件口躺了两小时多才落地，而那一拍哨兵的 F 格写的是
「门可插零枚」——尺没错（它数的是当下共存件），错在没人跑。把「人记得跑」换成「腿自己跑」。

r2 相对 r1 的改动，全部来自号令者 18:2x 追加的纪律（装进代码，不是写进文档靠自觉）：
  · 插之前先拿块头标题在权威账本数命中：大于零就改名挪开不插——applier 自己的 dedupe 只按
    块头分组、不看账本，挡不住「同一份交付记两次」（那笔账我昨天错过一次）；
  · 插完再数一遍，应为一次；不等于一次就具名报，不混进「成功」里；
  · 通报腿带上「本拍原文」当出处（--reprint 吐同一样字节），否则它自己会被数的闸拒掉——
    r1 那一拍就是 rc=2 静默失败，日志里有。

边界（写死，别扩权）：只跑现成的 applier，不自己写账本、不碰镜像腿（applier 成功后自己会推）；
空目录零写入；被坐标门拒的块原样留着等号令者拆，本腿不改别人写的字、不重投；单实例锁按
CommandLine 认，绝不双插。
"""
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
SELF = os.path.abspath(__file__)
IBOX = u"D:/moodle/_qoder_ledger_inbox"
APPLIER = os.path.join(LIVE, u"ledger_inbox_apply_r2.py")
LOG = os.path.join(HERE, u"_inbox_applier.log")
LAST = os.path.join(HERE, u"_inbox_applier_lastrun.txt")
LOCK = os.path.join(HERE, u"_inbox_applier.pid")
LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
DUP_SUFFIX = u".dup-in-ledger"
BUS = u"D:/moodle/agent_bus"
CLOSING = os.path.join(LIVE, u"CLOSING_LINE.txt")
FROM = u"qoder:42d1a6fa"
CMDR = u"qoder:494abfd7"
STOP = os.environ.get("APPLIER_STOP", "2340")   # 默认=今天 23:40（纯 HHMM 形制，stop_at 认得）。
# 10-06 17:3x 修：旧默认是 "1005-1100"——写死的上一班收工日。一旦不带 env 冷启动（重启后由栈补起正是这条路），
# 它算出来早已在过去 ⇒ 这条腿**一起步就自退**，而栈那一格照样打"栈完整"。日期写死＝定时炸弹，别再写。
PERIOD = int(os.environ.get("APPLIER_PERIOD", "900"))
NL = chr(10)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if u"--reprint" in sys.argv[1:]:
    # 只做一件事：把最近一拍的原样字节吐回去，给「通报」那条腿当出处（同源同一次读数）
    if not os.path.exists(LAST):
        sys.stdout.write(u"NO_LAST_RUN_YET" + NL)
        sys.exit(3)
    sys.stdout.write(io.open(LAST, encoding="utf-8").read())
    sys.exit(0)


def say(s):
    io.open(LOG, "a", encoding="utf-8", newline=NL).write(time.strftime("[%m-%d %H:%M:%S] ") + s + NL)


def stop_at(stop=STOP):
    """`2335`＝今天 23:35；`1005-1100`＝10-05 11:00（跨日形制必须有，否则过午夜直接收工）。"""
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
    alive = u"_inbox_applier" in cmd            # 只认「这一条腿」（r1/r2 同一职责），否则算陈旧锁
    if not alive:
        say(u"锁里的 pid %d 不是本腿（或已退）⇒ 当陈旧锁清掉" % pid)
    return alive


def block_head(path):
    """块头＝首行去掉井号后的标题。applier 的 dedupe 只按它分组，所以判重复也只用它。"""
    try:
        return io.open(path, encoding="utf-8", errors="replace").readline().strip().lstrip("#").strip()
    except Exception:
        return u""


def ledger_hits(title):
    """拿块头在权威账本数命中。读不到返回 None＝不可得——不可得时**不插**，
    绝不把「读不到」当「没有」（那正是重复入账的成因形状）。"""
    if not title:
        return None
    try:
        return io.open(LEDGER, encoding="utf-8", errors="replace").read().count(title)
    except Exception as e:
        say(u"账本读不到（%s: %s）⇒ 命中数不可得" % (type(e).__name__, str(e)[:80]))
        return None


def park_duplicates(names):
    """命中大于零的改名让开（applier 不再扫它）。可逆、不动内容。返回还能插的 [(路径, 块头)]。"""
    keep = []
    for name in names:
        f = os.path.join(IBOX, name)
        title = block_head(f)
        hit = ledger_hits(title)
        if hit is None:
            say(u"命中数不可得 ⇒ %s 这一拍不插（不拿「读不到」当「没有」）" % name)
            continue
        if hit > 0:
            try:
                os.rename(f, f + DUP_SUFFIX)
                say(u"跳过并挪开：%s｜块头「%s」在账本已命中 %d 次 ⇒ 再插就是重复入账（未改内容）"
                    % (name, title[:40], hit))
            except Exception as e:
                say(u"想挪开却没挪动：%s（%s: %s）⇒ 这一拍不插它" % (name, type(e).__name__, str(e)[:70]))
            continue
        keep.append((f, title))
    return keep


def verify_landed(pairs):
    """插完再数一遍：应为一次。不等于一次也具名打出来，别混在「成功」里。

    10-05 01:34 抓到旧写法把「我读不到」写成「数出来是 None」，然后照常往下走：
    标题取自 `ti.get(x) or block_head(IBOX/x)`，可插入的第一步就是把块文件移进
    `_processed/`，那一拍再回 IBOX 读只能读空，`ledger_hits(u"")` 便返回 None。
    现在标题只信插入前那一拍记下的（pairs 由调用方从 keep 传进来），取不到＝红；
    命中数不可得＝等 5 秒重取一次，仍不可得＝红。**None 永远不默认成一次**。
    返回转红的块名列表，调用方据此把「已入库」那句改口。
    """
    bad = []
    for name, title in pairs:
        if not title:
            bad.append(name)
            say(u"插后核对转红：%s｜块头标题取不到 ⇒ 无法核账，按红办（不拿「没标题」当「没重复」）"
                % name)
            continue
        hit = ledger_hits(title)
        why = u""
        if hit is None:
            time.sleep(5)          # 账本正被整本重写时读到空面，是已知形状，等一手再取
            hit = ledger_hits(title)
            why = u"（重试一次仍不可得）"
        if hit != 1:
            bad.append(name)
            say(u"插后核对转红：%s｜块头在账本命中 %s 次（应为 1%s）" % (name, hit, why))
        else:
            say(u"插后核对：%s｜块头在账本命中 1 次（应为 1）" % name)
    if bad:
        hub_alarm(u"R", u"verify",
                  u"代插腿插完再数命中，有块头转红：要么标题取不到、要么命中数不可得、"
                  u"要么不为一次。这一拍的入账不可证，别按「已入库」办；逐枚名单与原因都在"
                  u"本腿日志的转红行里，随附证据那份原样字节是本拍出处。")
    return bad


def pending():
    try:
        return sorted(f for f in os.listdir(IBOX) if f.endswith(".md") and not f.startswith("_"))
    except Exception as e:
        say(u"收件口读不到（%s: %s）⇒ 这一拍不算绿" % (type(e).__name__, str(e)[:80]))
        return None


def hub_alarm(band, id8, text):
    """报红的同一时刻往 BB 机投一枚 alarm：日志红只有我回来才看得见，中枢那条号令者会读。

    为什么这里要自己有一份：本文件以前直接调了 hub_alarm（P 档那句镜像回执缺失的报警），
    却从没定义或导入过它——那个分支真执行就是 NameError，而它在 while 循环里、没有
    except 兜着，于是「最该叫人的那一刻」恰好把腿自己打死。签名与哨兵那份同形
    （band, id8, text），旧调用点不用改。
    正文刻意不带阿拉伯读数：本腿的数都在 --reprint 那份原样字节里，正文里的数必须与
    证据同源才算数（哨兵 04:52 撞过：无出处的数被中枢拒收⇒这条腿永远投不出去）。
    上报失败不许改变判定，只记一行——红该红还是该红。
    """
    topic = u"applier:%s:%s:%s" % (band, time.strftime("%m%d"), id8)
    try:
        cl = io.open(CLOSING, encoding="utf-8").read().strip()
    except Exception as e:
        cl = u""
        say(u"收尾口令原件读不到（%s: %s）" % (type(e).__name__, str(e)[:80]))
    if len(cl.encode("utf-8")) < 60:
        say(u"收尾口令原件不足 60 字节 ⇒ %s 这枚 alarm 不投（外发必须带逐字尾行）" % topic)
        return False
    text = text.rstrip() + NL + cl + NL
    try:
        cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send",
               "--from", FROM, "--to", CMDR, "--kind", "alarm",
               "--topic", topic, "--body", text,
               "--evidence", u"本拍原文|python \"%s\" --reprint" % SELF]
        q = subprocess.run(cmd, capture_output=True, cwd=BUS, timeout=90,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = (q.stdout or b"").decode("utf-8", "replace")
        ok = (u'"id"' in out) and q.returncode == 0
        say(u"BB 机 alarm %s（%s）%s" % (u"已投" if ok else u"没投出去", topic,
            u"" if ok else (out[:120] or (q.stderr or b"").decode("utf-8", "replace")[:120])))
        return ok
    except Exception as e:
        say(u"BB 机 alarm 抛错（%s）：%s" % (topic, e))
        return False


def tell_cmdr(landed_names, verdict, tally_line):
    """插成了就给号令者留一笔耐久副本：他在收件口不用猜「谁动了账本」。
    读数不在正文里重复——随附证据那条命令吐出的就是本拍原样字节。"""
    io.open(LAST, "w", encoding="utf-8", newline=NL).write(
        u"read_at=%s%sinserted=%s%stally=%s%s" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), NL, u",".join(landed_names), NL,
            tally_line or u"（applier 没打 tally 行）", NL))
    body = (u"代插腿自动落了块进账本（这一格不再靠值守醒着）。块名与本拍 tally 原文都随本条证据附上——"
            u"读数只在它那一刻成立，别当现状引用。\n"
            u"块名：%s\n判定：%s\n"
            u"这一腿的纪律：插前拿块头在权威账本数命中、大于零就改名挪开不插；插后再数一遍应为一次；"
            u"被坐标门拒的块原样留在收件口等号令者拆，本腿不改别人写的字、不重投。\n"
            % (u"、".join(landed_names), verdict))
    try:
        cl = io.open(CLOSING, encoding="utf-8").read().strip()
    except Exception:
        cl = u""
    if len(cl.encode("utf-8")) < 60:
        say(u"收尾口令原件读不到 ⇒ 这条通报不发（外发必须带逐字尾行）")
        return
    body += cl + NL
    topic = u"auto-land-%s-%s" % (time.strftime("%H%M%S"),
                                  re.sub(r"\W+", u"", u"".join(landed_names))[:24])
    cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send", "--from", u"qoder:42d1a6fa",
           "--to", u"qoder:494abfd7", "--kind", "deliver", "--topic", topic, "--body", body,
           "--evidence", u'代插这一拍的原文|python "%s" --reprint' % SELF]
    p = subprocess.run(cmd, cwd=BUS, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = (p.stdout or b"").decode("utf-8", "replace")
    say(u"通报腿 rc=%d %s" % (p.returncode,
        u"已入库" if u'"id"' in out else out[-200:].replace(NL, u" ")))


def main():
    if already_running():
        say(u"本腿已在（锁里 pid 活着）⇒ 单实例退出，不双插")
        return 0
    io.open(LOCK, "w", encoding="utf-8").write(str(os.getpid()))
    deadline = stop_at()
    say(u"=== 代插腿 r2 起来：到 %s 收工；每 %d 秒一拍（pid=%s）" % (STOP, PERIOD, os.getpid()))
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
            keep = park_duplicates(fs)
            if not keep:
                say(u"这一拍没有可插的（要么已挪开、要么命中数不可得）")
            else:
                say(u"有待插 ⇒ 跑 applier --apply（块头与代插戳逐枚记）")
                for f, t in keep:
                    say(u"  待插块头：%s｜%s" % (os.path.basename(f), t[:60]))
                p = subprocess.run([sys.executable, APPLIER, "--apply"], cwd=LIVE, capture_output=True,
                                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                out = ((p.stdout or b"").decode("utf-8", "replace")
                       + (p.stderr or b"").decode("utf-8", "replace"))
                ins = re.findall(r"INSERTED (\S+)", out)
                ref = re.findall(r"REFUSED (\S+)", out)
                tal = [l for l in out.split(NL) if l.startswith("tally")]
                # 镜像那一步以前被这里丢掉了：日志里 grep "mirror rc=" 恒为 0，
                # 于是"插进去了"被当成"也推上去了"——看不见结果不等于成功。
                MIR_W = (u"mirror rc=", u"BYTE_LEVEL_CONFIRMED", u"PROVEN", u"REMOTE_LEDGER_READ_FAILED",
                         u"Bad credentials", u"ABORT:")
                mir = [l for l in out.split(NL) if any(w in l for w in MIR_W)]
                tally_line = tal[-1] if tal else out[-200:].replace(NL, u" ")
                say(u"applier rc=%d｜%s" % (p.returncode, tally_line))
                if ins:
                    ti = dict((os.path.basename(f), t) for f, t in keep)
                    bad = verify_landed([(x, ti.get(x) or u"") for x in ins])
                    if mir:
                        for l in mir[-3:]:
                            say(u"镜像回执：%s" % l[:150])
                        good = any((u"BYTE_LEVEL_CONFIRMED" in l) or (u"PROVEN" in l) for l in mir)
                        note = (u"镜像回执已转印进本日志（%s）"
                                % (u"含 BYTE_LEVEL_CONFIRMED/PROVEN" if good else u"结论不是成功，见日志原文"))
                    else:
                        note = u"注意：这一拍插了 %d 块，但 applier 输出里没有镜像那一步的任何回执" % len(ins)
                        say(u"镜像回执：无 ⇒ 不能当它推成功了（%s）" % note)
                        hub_alarm(u"P", u"mirror", u"P 档：代插腿插了 %d 块却拿不到镜像回执，"
                                u"账本本地已进、远端不可证；出处是本腿日志尾行与 "
                                u"live_checks/merge_ledger_then_mirror_r2.py 的 mirror rc 那行" % len(ins))
                    note += (u"；但插后核对有转红的（标题取不到／命中数不可得／不为一次），"
                             u"逐枚原因见本腿红行，R 档 alarm 已投" if bad
                             else u"；插前命中为零、插后逐枚核对每枚都只命中一次")
                    tell_cmdr(ins, note, tally_line)
                if ref:
                    say(u"被门拒：%s ⇒ 原样留在收件口等号令者拆（本腿不改块、不重投）" % u"、".join(ref))
        time.sleep(PERIOD)
    say(u"到 STOP=%s，本腿主动收工。此后要代插就得再跑一次本脚本。" % STOP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
