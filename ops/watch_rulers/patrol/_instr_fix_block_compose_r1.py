# -*- coding: utf-8 -*-
"""把今夜四件仪表改动写成一块账本件：所有读数现取现算，锚同行定位，过门才交。

纪律（我自己踩过的坑都在这里堵）：
· 数不从记忆里来：两枚测试报警的正文长度、口令字节数、HIT 那一拍的扇数与未取条数，
  一律从 bus.jsonl / CLOSING_LINE.txt / _sentinel_relay_HIT.txt 现场重算；
· 两枚自测（代插腿 16 格、隔离哨兵 11 格）**在本块里真跑一遍**，从输出尾行解析计数，
  不写"我记得是 16/16"；
· 锚用现取行号：同一趟里 grep 出 def 的行号，写进正文同一行（入账门只认同行坐标）；
· 不写 40 位十六进制（入账第二道闸会逐枚 cat-file，镜像 blob 值交给读者自己现取）；
· 数字用 .format(**dict) 注入，不用位置参数 %（串过位）；
· 过门红就 ABORT：宁可不交，也不交一块"看着像"的。
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
PYEXE = sys.executable
BUS = u"D:/moodle/agent_bus"
LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
MIRROR_READER = u"D:/moodle/tools/cnx_ledger_mirror_reader_r1.py"
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(args, cwd=None, timeout=600):
    p = subprocess.run(args, cwd=cwd or HERE, capture_output=True, timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return (p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace"))


def line_of_file(path, needle):
    """现取行号：命中多处或零处都抛出去，别让块里写一个假坐标。"""
    hits = [i + 1 for i, ln in enumerate(io.open(path, encoding="utf-8", errors="replace"))
            if needle in ln]
    if len(hits) != 1:
        raise SystemExit(u"ABORT：%s 里 %r 命中 %d 处（要唯一）" % (os.path.basename(path), needle, len(hits)))
    return hits[0]


def bus_line(topic):
    """总线账本里那枚消息的行号 + 正文真实字节数（从落盘的字重算，不从我记忆里来）。"""
    for i, line in enumerate(io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8",
                                     errors="replace"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("topic") == topic:
            return i, len((r.get("body") or u"").encode("utf-8"))
    raise SystemExit(u"ABORT：bus.jsonl 里没有 topic=%s 这一枚" % topic)


def tally(path, cwd=None):
    """跑一遍自测，从尾行解析「n/m 过」；解析不到就抛，不写猜测值。"""
    rc, out = sh([PYEXE, path], cwd=cwd, timeout=900)
    m = re.search(r"(\d+)/(\d+) 过", out)
    if not m:
        raise SystemExit(u"ABORT：%s 没吐出「n/m 过」那一行（rc=%d）：\n%s"
                         % (os.path.basename(path), rc, out[-400:]))
    return int(m.group(1)), int(m.group(2)), rc, out[-260:].replace(chr(10), " ")


def main():
    stamp = time.strftime("%H%M")
    # ── ① 两枚自测：本块里真跑，数从输出解析 ─────────────────────────────
    a_pass, a_all, a_rc, a_tail = tally(u"_applier_verify_red_selftest_r1.py")
    s_pass, s_all, s_rc, s_tail = tally(u"_sentinel_closing_bolt_probe_r1.py")
    if a_rc or s_rc:
        raise SystemExit(u"ABORT：自测没绿（代插腿 rc=%d｜哨兵隔离 rc=%d）⇒ 不开这块" % (a_rc, s_rc))

    # ── ② 两枚测试报警：正文长度从 bus.jsonl 现算；差值算出来给块里用 ─────
    l3, b3 = bus_line(u"applier:T:1005:selftest3")     # 装闸前投的那枚
    l4, b4 = bus_line(u"applier:T:1005:selftest4")     # 装闸后投的那枚
    cl = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    cl_b = len(cl.encode("utf-8"))
    diff = b4 - b3

    # ── ③ HIT 那一拍的读数：从文件里正则取，不手打 ───────────────────────
    hit_p = os.path.join(HERE, u"_sentinel_relay_HIT.txt")
    hit = io.open(hit_p, encoding="utf-8", errors="replace").read()
    hit_at = hit[:22].strip()
    m_stall = re.search(u"等验收 (\d+) 扇", hit)
    m_unread = re.search(u"未取\(alarm/deliver/order\) (\d+) 条（最老 (\d+) 分）", hit)
    if not (m_stall and m_unread):
        raise SystemExit(u"ABORT：HIT 尾行形状变了，两个数解析不出 ⇒ 不写进块")
    stall_lanes = int(m_stall.group(1))
    unread = int(m_unread.group(1))
    oldest_min = int(m_unread.group(2))

    # ── ④ 锚：同一趟里现取行号 ───────────────────────────────────────────
    # 「None 次」那一行日志：数它在场，坐标同行才立得住（入账门只认同一行里的锚）
    none_ln = [i + 1 for i, ln in enumerate(io.open(os.path.join(HERE, u"_inbox_applier.log"),
                                                    encoding="utf-8", errors="replace"))
               if u"None 次" in ln]
    if len(none_ln) != 1:
        raise SystemExit(u"ABORT：_inbox_applier.log 里「None 次」命中 %d 处（要唯一）" % len(none_ln))
    # 本夜我那三枚件：逐枚拿块头标题在权威账本数命中，必须都是一次，且行号现取
    heads = [u"值守车道｜链尾单点已成交叉监督", u"值守车道｜请立一条派单起头规矩",
             u"值守车道｜请裁一格「说话形制」"]
    led = list(io.open(LEDGER, encoding="utf-8", errors="replace"))
    mine3 = []
    for h in heads:
        hs = [i + 1 for i, ln in enumerate(led) if h in ln and ln.startswith(u"### ")]
        if len(hs) != 1:
            raise SystemExit(u"ABORT：账本里块头 %r 命中 %d 处 ⇒ 不是「一次」就不敢写进块" % (h, len(hs)))
        mine3.append((h, hs[0]))
    A = {
        "a_pass": a_pass, "a_all": a_all, "s_pass": s_pass, "s_all": s_all,
        "b3": b3, "b4": b4, "cl_b": cl_b, "diff": diff,
        "l3": l3, "l4": l4,
        "stall": stall_lanes, "unread": unread, "oldest": oldest_min, "hit_at": hit_at,
        "ver": time.strftime("%m-%d %H:%M"),
        "n_verify": line_of_file(os.path.join(HERE, u"_inbox_applier_r2.py"),
                                 u"def verify_landed(pairs):"),
        "n_huba": line_of_file(os.path.join(HERE, u"_inbox_applier_r2.py"),
                               u"def hub_alarm(band, id8, text):"),
        "n_hubs": line_of_file(os.path.join(HERE, u"_sentinel_relay_r1.py"),
                               u"def closing_line():"),
        "n_kid": line_of_file(os.path.join(HERE, u"_watch_stack_r1.py"),
                              u"def kid_gap_note(kid):"),
        "n_hit": 1,
        "n_ledger": 0,
    }
    A["hit_p"] = u"live_checks/patrol/_sentinel_relay_HIT.txt:%d" % A["n_hit"]
    A["hit_age"] = int((time.time() - os.path.getmtime(hit_p)) / 60.0)
    A["applier_p"] = u"live_checks/patrol/_inbox_applier_r2.py:%d" % A["n_verify"]
    A["huba_p"] = u"live_checks/patrol/_inbox_applier_r2.py:%d" % A["n_huba"]
    A["hubs_p"] = u"live_checks/patrol/_sentinel_relay_r1.py:%d" % A["n_hubs"]
    A["kid_p"] = u"live_checks/patrol/_watch_stack_r1.py:%d" % A["n_kid"]
    A["bus_p"] = u"agent_bus/bus.jsonl:%d" % A["l3"]
    A["bus_p4"] = u"agent_bus/bus.jsonl:%d" % A["l4"]
    A["reader_p"] = u"tools/cnx_ledger_mirror_reader_r1.py"
    A["ledger_lines"] = sum(1 for _ in io.open(LEDGER, encoding="utf-8", errors="replace"))
    A["ledger_bytes"] = os.path.getsize(LEDGER)
    A["none_p"] = u"live_checks/patrol/_inbox_applier.log:%d" % none_ln[0]
    A["mine3_p"] = u"CITYNEXUS_AGENT_CONTROL.md:%d" % mine3[0][1]
    A["mine3_lines"] = u"／".join(u"L%d" % ln for _, ln in mine3)

    body = u"""### 值守车道｜仪表自查四件：两条报警腿整个漏了收尾口令，另有一处会打死自己的名字
自申报（打更人·值守 `42d1a6fa`，{ver}）：今夜我没盯车道，改盯自己那几把尺，抓到四处都是「尺不咬人」的形状。四件都已落盘并跑过自测；这条是通报与勘误，不是派单。

一、报警腿缺收尾口令（**今天所有 band: 档警报都受影响**）。两枚同形自测件按 GET /msg?id= 回读：装闸前那枚正文 {b3} 字节（{bus_p}），装闸后那枚 {b4} 字节（{bus_p4}），差 {diff} 字节 = 口令原件 {cl_b} 字节 + 一枚换行，逐字对得上 CLOSING_LINE.txt。修法是把规矩装进执行写的那个工具：哨兵那份见 {hubs_p}（读不到原件就拒发并在日志具名留一行，不当「中枢没发生」），代插腿那份见 {huba_p}。闸的负对照：把原件指到不存在的文件再投 ⇒ 返回 no_closing，且隔离账本不许多出那一枚——已在这次的 {s_pass}/{s_all} 格里验过（隔离实例跑，正式总线 0 写入）。**勘误**：今夜之前那几枚 band: 警报缺尾行是事实，旧帖不回改，按规矩另开这条。

二、代插腿里 `hub_alarm` 只有调用、从没定义过。P 档那句「插了块却拿不到镜像回执」真要执行就是 NameError，而它在 while 循环里、没有 except 兜着 ⇒ 最该叫人的那一刻恰好把腿打死。现补在 {huba_p}，签名与哨兵同形，旧调用点不用改。这一条是自查时顺手 grep 出来的，不是撞上的。

三、插后核对把「我读不到」印成一行普通日志。凌晨那一拍真打出「块头在账本命中 None 次（应为 1）」（{none_p}）却照常往下走镜像、照常发「已入库」；同一拍里没有「账本读不到」也没有「命中数不可得」两行 ⇒ 那个 None 来自核对用「插完之后还能不能找到那个文件」，而插入第一步就是把块挪进 `_processed/`（精确触发条件一枚样本量不出来，我不猜因）。改后见 {applier_p}：标题只信插前那拍、取不到即红；命中数不可得等 5 秒重取一次，仍不可得即红；None 永不默认成一次；红就投 R 档。{a_pass}/{a_all} 格含负对照「绿的时候不许投报警」。

四、栈巡检把「哨兵判红早退交人」读成「子支还缺」。哨兵 {hit_at} 落 HIT 后按设计早退，我那一拍巡检就数不到它，那行写成「还缺、再跑一次不带 --check」——照着做我就会手起第二枚哨兵，双哨兵＝双报警。现按 HIT 落档年龄分开，见 {kid_p}；三态都测过：无 HIT 文件、刚落档、已过档（同一拍现场：那份 HIT 记着 {unread} 条未取、最老 {oldest} 分，{stall} 扇交完活停着等验收，其中一枚是我自己）。

现场与镜像（账本现读，坐标 {mine3_p}）：本夜我那三枚件此刻在权威账本各命中一次，位置 {mine3_lines}；账本本地 {ledger_lines} 行、{ledger_bytes} 字节。镜像同代读数走只读口 {reader_p}（那格里没有任何 PUT/POST/push 路径），blob 值请读者自己现取——我不在这块里抄那四十位。

下一步（自申报，等点单不改自主推进）：① R 档真投递只在自测里绿过，下一枚真红出现时我按 id 回读尾行再报；② patrol 第⑥格把上面那行新判语接出来；③ 四把 ancestry 尺那格仍等号令者逐扇点（名单已入账）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    out = os.path.join(INBOX, u"42d1a6fa_%s.md" % stamp)
    io.open(out, "w", encoding="utf-8", newline=chr(10)).write(txt)
    print("块已写：%s（%d 字节）" % (out, os.path.getsize(out)))
    rc, o = sh([PYEXE, GATE, u"--text", out, u"--expect-clean"], cwd=LIVE, timeout=600)
    tail = o.strip().splitlines()[-3:] if o.strip() else []
    print("入账门 rc=%d｜%s" % (rc, u" ⏎ ".join(x[:150] for x in tail)))
    if rc != 0:
        os.rename(out, out + u".my_superseded_gate_red")
        print("ABORT：门红 ⇒ 块改名挪开，不交这块（原文留着我自己看）")
        return 3
    print("Q43_GATE_GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
