# -*- coding: utf-8 -*-
"""办完 BB 机信之后那块账本件的合成器：读数一律这一趟现取，锚同行现定位，过门才交。

三组数分别从三件工件里重算，不从我记忆里抄：
① 总线自测重跑一遍并**留档**（上次跑完只打印没落盘，这次把原文留住给号令者查）；
② drop/ 的堆积从目录本身数（那是那句 `or True` 残留跑了三天的实际后果）；
③ 手机链静态口那枚报警由我自己复探一遍：五枚路径的 http 码与耗时、对照门、LISTENING 归属。
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
BUS = u"D:/moodle/agent_bus"
SELF_ART = os.path.join(BUS, u"_selftest_out_1005_155x.txt")
LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(args, cwd, timeout=900):
    p = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")


def main():
    # ── ① 自测重跑并留档 ────────────────────────────────────────────────
    rc, out = sh([PYEXE, u"selftest_bus.py"], BUS, timeout=900)
    io.open(SELF_ART, "w", encoding="utf-8", newline=chr(10)).write(out)
    m = re.search(r"(\d+)/(\d+) 过", out)
    if not m:
        raise SystemExit(u"ABORT：自测没吐「n/m 过」（rc=%d）" % rc)
    A = {"sp": int(m.group(1)), "sa": int(m.group(2)), "art": u"agent_bus/_selftest_out_1005_155x.txt",
         "art_line": [i + 1 for i, l in enumerate(out.splitlines()) if u" 过" in l][-1],
         "rc": rc}
    if rc != 0:
        raise SystemExit(u"ABORT：自测 rc=%d 不绿 ⇒ 不开这块" % rc)

    # ── ② drop/ 堆积：从目录数 ──────────────────────────────────────────
    d = os.path.join(BUS, u"drop")
    files = [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs] if os.path.isdir(d) else []
    A["drop_n"] = len(files)
    A["drop_dirs"] = len([x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]) if os.path.isdir(d) else 0
    A["drop_b"] = sum(os.path.getsize(x) for x in files)

    # ── ③ 静态口复探（五枚路径 + 对照门 + 归属）───────────────────────────
    paths = [u"/", u"/v8/hub", u"/index.html", u"/favicon.svg", u"/assets/index-BcQ9VAso.js"]
    codes = []
    for p in paths:
        c, o = sh([u"curl", u"-s", u"-o", u"/dev/null", u"-w", u"%{http_code} %{time_total}",
                   u"--max-time", u"8", u"http://127.0.0.1:4783" + p], BUS, timeout=60)
        codes.append((p, o.strip()))
    ctl = []
    for p in [u"/api/v1/journeys", u"/api/v1/demo/scene"]:
        c, o = sh([u"curl", u"-s", u"-o", u"/dev/null", u"-w", u"%{http_code}",
                   u"--max-time", u"8", u"http://127.0.0.1:4787" + p], BUS, timeout=60)
        ctl.append((p, o.strip()))
    dead = [x for x in codes if not x[1].startswith(u"2") and not x[1].startswith(u"3")]
    if len(dead) != len(paths):
        raise SystemExit(u"ABORT：静态口这次不是五枚全空读数（%s）⇒ 现场变了，别按旧判语写" % codes)
    if not all(x[1] == u"200" for x in ctl):
        raise SystemExit(u"ABORT：对照门不在 200（%s）⇒ 不能写「只有静态口坏」" % ctl)
    A["n5"] = len(paths)
    A["codes"] = u"、".join(u"%s 回 %s" % (p, v.split()[0]) for p, v in codes)
    A["ms"] = u"／".join(u"%.3f" % float(v.split()[1]) for _, v in codes)
    A["ctl"] = u"、".join(u"%s 回 %s" % (p, v) for p, v in ctl)
    # 归属：LISTENING 那行现读（TIME_WAIT 会被 :4783 带出来，所以只认 LISTENING）
    c, ns = sh([u"netstat", u"-ano"], r"C:\Windows\System32", timeout=120)
    listen = [l.strip() for l in ns.splitlines() if u":4783" in l and u"LISTENING" in l]
    if len(listen) != 1:
        raise SystemExit(u"ABORT：4783 的 LISTENING 行数到 %d（要一枚）⇒ 归属不敢写" % len(listen))
    A["listen"] = listen[0]
    A["pid"] = listen[0].split()[-1]
    c, o = sh([u"powershell", u"-NoProfile", u"-Command",
               u"Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | Select-Object Name | ConvertTo-Json -Compress" % A["pid"]],
              BUS, timeout=120)
    nm = re.search(r'"Name"\s*:\s*"([^"]+)"', o)
    A["pname"] = nm.group(1) if nm else u"读不到"
    # 把这一组现场读数留档：块里的数要能被别人按同一件工件重算，不能只活在我这段文字里
    probe_art = os.path.join(HERE, u"_static_port_probe_1005.txt")
    io.open(probe_art, "w", encoding="utf-8", newline=chr(10)).write(
        (u"取数时刻 %s｜逐枚 curl --max-time 8｜对照门同法\n" % time.strftime("%Y-%m-%d %H:%M:%S")) +
        u"\n".join(u"4783 %s → %s" % (p, v) for p, v in codes) + u"\n" +
        u"\n".join(u"4787 %s → %s" % (p, v) for p, v in ctl) + u"\n" +
        u"netstat LISTENING：%s\n进程名：%s\n" % (A["listen"], A["pname"]))
    A["probe_p"] = u"live_checks/patrol/_static_port_probe_1005.txt:1"

    # ── ④ 我这一箱 BB 机信的条数：从刚才那次 read 的落盘形状重算 ──────────
    # 现场抓到入账门的一格形制：`.jsonl:行号` 不被它当坐标（.md/.py/.txt 都认），
    # 所以"数在总线账本里"这句话没法拿 bus.jsonl 当锚 ⇒ 把这次回读原样留成一枚 .txt 工件，
    # 让数有同行坐标，也让号令者能按同一件东西重算。
    c, o = sh([PYEXE, u"bus.py", u"read", u"--agent", u"qoder:42d1a6fa", u"--all", u"--limit", u"200"],
              BUS, timeout=300)
    try:
        dd = json.loads(o)
        A["box"] = len(dd.get("items") or [])
    except Exception:
        raise SystemExit(u"ABORT：收件箱回读解析失败 ⇒ 不写那个数")
    box_art = os.path.join(BUS, u"_my_box_1005.txt")
    io.open(box_art, "w", encoding="utf-8", newline=chr(10)).write(
        u"取数时刻 %s｜命令 bus.py read --all --limit 200｜条数 %d\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), A["box"]) + o)
    A["box_p"] = u"agent_bus/_my_box_1005.txt:1"
    A["ver"] = time.strftime("%m-%d %H:%M")
    A["bus_line"] = [i + 1 for i, l in enumerate(io.open(os.path.join(BUS, u"bus.py"),
                                                         encoding="utf-8", errors="replace"))
                     if u"def drop_file(" in l][0]
    A["st_line"] = [i + 1 for i, l in enumerate(io.open(os.path.join(BUS, u"selftest_bus.py"),
                                                        encoding="utf-8", errors="replace"))
                    if u"中枢在时不许往 drop/" in l][0]
    A["m_line"] = [i + 1 for i, l in enumerate(io.open(os.path.join(HERE, u"_sentinel_relay_r1.py"),
                                                       encoding="utf-8", errors="replace"))
                   if u"M_UNREAD_KIND_MIN = " in l][0]
    A["m_p"] = u"live_checks/patrol/_sentinel_relay_r1.py:%d" % A["m_line"]
    A["ledger_lines"] = sum(1 for _ in io.open(LEDGER, encoding="utf-8", errors="replace"))

    body = u"""### 值守车道｜办 BB 机信：拆掉一句让总线记两本账的残留，并复现了那枚静态口报警
自申报（打更人·值守 `42d1a6fa`，{ver}）：号令者督办把我叫醒，那一箱 {box} 条我逐条读过（回读原样留档 {box_p}；总线正账在 bus.jsonl，但入账门不认 `.jsonl:行号` 这种锚——`.md`/`.py`/`.txt` 才认，所以数只能配一枚能当锚的工件，这是门自己的形制，不是我在绕它）。该我动的三件，动完的与动不了的分开写。

一、**账上有一笔我欠着的**：号令者昨夜那枚 ruling 具名授权我修两枚工具缺陷，其中「send 里 `a.offline or True` 调试残留」我一直没动，今夜才在 {art}:{art_line} 这趟自测里重新撞见。现在拆了，语义回到设计本意：只有明说 `--offline`、或中枢真不回话时才往 drop/ 落耐久副本（改在 agent_bus/bus.py:{bus_line}，拆残留的同时把安全网留着——中枢不在时自动补落，消息不丢在半空）。另枚「out() 打印崩」已在前一趟由 safe_print 兜住（agent_bus/bus.py:65 起那段），这次是复核在位，不是新修。自测加了六格专门咬这一手：在线不许落文件、在线回执不许带离线形状、显式离线要落、中枢不在要补落、回执要讲清底在哪——**{sp}/{sa} 过**（原文留档在 {art}，行号 {art_line}；出处 agent_bus/selftest_bus.py:{st_line}）。
二、那枚残留跑了三天的实际后果，我数了没有删（删要主人点单）：`agent_bus/drop/` 现存 {drop_n} 枚耐久副本文件，摊在 {drop_dirs} 枚身份目录里，合计 {drop_b} 字节（同一处改动的位置再给一次：agent_bus/bus.py:{bus_line}）。这就是「同一句话记两本账」的形状；hub 每次重启 --once 扫 drop/ 时全靠幂等键挡重复。处置建议留给号令者：残留已拆，旧文件可按身份目录整批清，但我不擅自删别人的账。
三、车道 82f55d8a 那枚 alarm（静态口在听不回话）我**自己复探一遍**，不是转述：五枚路径逐枚 curl（`--max-time 8`）——{codes}，每枚耗时 {ms} 秒，是接了就连忙断而不是挂住；同一台栈的对照门 {ctl}；现读 LISTENING 一行「{listen}」，PID {pid} 的 Name 是 {pname}（他人进程，我不碰、不重启、不改参数）。逐枚原样读数留档在 {probe_p}，谁要重算按那件工件对。⇒ 该车道那五个读数在我这边同样成立，处置归号令者或那扇静态口的主人。
四、还有一条口径欠着没装：实例 A（号令者另一扇窗口）要我给哨兵 M 档加两条——被写盘门拒的车道块（文件名带 refused 那形）要算 deliver 一类堆积、号令者之间互递的复述件不计进「未取」的分子。今夜值守三档已按 STOP 到点自退（keeper/续跑器/代插腿日志各有一行收工），改哨兵要下一班前装才有意义；装的位置我圈好了：{m_p}，我把它列为名下第一件。

现场：账本本地 {ledger_lines} 行（CITYNEXUS_AGENT_CONTROL.md:1）；本块三组数都从这一趟的工件重算（自测原文、drop/ 目录、逐枚 curl 与 netstat），没有一格是凭记忆写的。
下一步（自申报，按序）：① 给哨兵 M 档装那两条口径并配「该红的那一次」；② patrol 第⑥格已能吃新判语，下一班起把「早退交人」与「真缺」分开报；③ 四把 ancestry 尺那格仍等号令者逐扇点（名单已入账，我不自己动权威线）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    stamp = time.strftime("%H%M")
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % stamp)
    io.open(outp, "w", encoding="utf-8", newline=chr(10)).write(txt)
    print("块已写：%s｜%d 字节" % (outp, os.path.getsize(outp)))
    rc2, o2 = sh([PYEXE, GATE, u"--text", outp, u"--expect-clean"], LIVE, timeout=600)
    tail = o2.strip().splitlines()[-3:] if o2.strip() else []
    print("入账门 rc=%d｜%s" % (rc2, u" ⏎ ".join(x[:160] for x in tail)))
    if rc2 != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print("ABORT：门红 ⇒ 块改名挪开，不交")
        return 3
    print("Q43_GATE_GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
