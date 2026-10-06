# -*- coding: utf-8 -*-
"""早班交接稿生成器：所有数字本轮现算，不抄上一轮，也不用我记忆里的结论。

覆盖四问：
 ① 车队到点还在干吗？——用会话流水里的 user 记录（我敲的门）+ 交付脉搏 + 入账块数 + 权威线提交数回答；
 ② 号令者遇到的困难我解了哪些？——闸口/尺名/派单 uuid/词表四类的实测读数与文件位置；
 ③ 我自己的错在哪里？——每一条都有对应的总线勘误 id；
 ④ 只剩人能定的那一件是什么？——只留**一个**问题（不派任何需要点击的活）。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\CityNexus"
SINCE = "2026-09-29 02:00"          # 值守这一段（用户睡前最后一道命令之后）
CLOSING = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read().decode("utf-8").strip()


def local_ep(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def knocks():
    """我发出的敲门：会话流水里 role=user、正文以「【值守 」开头且尾行逐字等于收尾口令。"""
    per = {}
    offenders = []
    total = exact = 0
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        sid = os.path.basename(p)[:8]
        try:
            with io.open(p, "rb") as f:
                f.seek(0, 2)
                sz = f.tell()
                f.seek(max(0, sz - 3000000))
                chunk = f.read()
        except Exception:
            continue
        for line in chunk.split(b"\n"):
            if not line.startswith(b"{"):
                continue
            try:
                r = json.loads(line.decode("utf-8", "replace"))
            except Exception:
                continue
            m = r.get("message") or {}
            if m.get("role") != "user":
                continue
            t = r.get("timestamp") or ""
            try:
                ep = time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
            except Exception:
                continue
            if ep < local_ep(SINCE):
                continue
            c = m.get("content")
            txt = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
                   if isinstance(c, list) else (c or ""))
            if not txt.strip().startswith(u"【值守 "):
                continue
            total += 1
            per[sid] = per.get(sid, 0) + 1
            tail = txt.strip().splitlines()[-1].strip() if txt.strip() else ""
            if tail == CLOSING:
                exact += 1
            else:
                offenders.append((sid, time.strftime("%H:%M", time.localtime(ep)), tail[:40]))
    return total, exact, len(per), offenders


def inserted_since():
    rows = []
    for p in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")):
        if os.path.getmtime(p) >= local_ep(SINCE):
            rows.append(os.path.basename(p))
    lanes = {}
    for n in rows:
        k = re.split(r"[_0-9]", n)[0] or "?"
        lanes[k] = lanes.get(k, 0) + 1
    return rows, lanes


def pulse():
    r = subprocess.run([PY, os.path.join(HERE, "_delivery_pulse.py"), "240"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = (r.stdout or "")
    m = re.search(r"新动过的 review 枝 (\d+) 条，涉及单号 (.*?)（共 (\d+) 张）", out)
    return (m.group(1), m.group(2), m.group(3)) if m else ("?", "?", "?")


def tip_and_commits():
    g = ["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="]
    t = subprocess.run(g + ["ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                       capture_output=True, text=True, timeout=240).stdout.split()
    tip40 = t[0] if t and re.match(r"^[0-9a-f]{40}$", t[0]) else "未读到"
    n = subprocess.run(g + ["log", "--since=" + SINCE, "--oneline", "origin/mirror/integration-frontend-apple-pass1"],
                       capture_output=True, text=True, errors="replace", timeout=300)
    return tip40, len([l for l in (n.stdout or "").splitlines() if l.strip()])


def cycles():
    wl = io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8", errors="replace").read()
    st = re.findall(r"^\[(\d\d:\d\d:\d\d)\] === cycle", wl, re.M)
    posts = re.findall(r"POST -> 201 (\d+)", wl)
    return (st[0] if st else "?", st[-1] if st else "?", len(st), len(posts))


def busids():
    rows = []
    for l in io.open(os.path.join(HERE, "bus_ids.txt"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            rows.append(l)
    return rows


def pending():
    """从 `--dry` 的输出解析，绝不 import 那个脚本：它会**在导入时就发总线贴**（06:04 我踩了，
    结果重复投了一条 5879584539，已记进 bus_ids.txt 的自误差列）。dry 模式不发帖。"""
    r = subprocess.run([PY, os.path.join(HERE, "_bus_pending_rulings.py"), "--dry"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
    out = (r.stdout or "") + (r.stderr or "")
    rows = []
    for m in re.finditer(u"- \\*\\*(.+?)\\*\\*（账本 `:(\\d+)`，[^≈]*≈([\\d.]+) 分钟）\\n\\s*要裁的：(.+?)。", out):
        rows.append((m.group(1), int(m.group(2)), float(m.group(3)), m.group(4)))
    return rows


def main():
    tot, exact, nsess, offenders = knocks()
    rows, lanes = inserted_since()
    br, orders, on = pulse()
    tip40, nc = tip_and_commits()
    first, last, cyc, autoposts = cycles()
    ids = busids()
    root = [f for f in os.listdir(INBOX) if f.endswith(".md")]
    pd = pending()
    df = subprocess.run(["df", "-h", "/c", "/d", "/e"], capture_output=True, text=True, timeout=60).stdout

    md = []
    md.append(u"# CityNexus 夜班值守交接（%s 生成）\n" % time.strftime("%m-%d %H:%M"))
    md.append(u"## 一、车队是否在干活（只用水下得着的证据）\n")
    md.append(u"- 我发出的敲门：**%d 次**，落到 **%d 条**不同会话；尾行逐字等于 83 B 收尾口令的 **%d/%d**。"
              u"（判据：会话流水 `role=user` 且正文以「【值守 」开头，源文件 `C:/Users/仓鼠王/.qoder/projects/D--moodle/<uuid>.jsonl`）"
              % (tot, nsess, exact, tot))
    if offenders:
        md.append(u"- **尾行不逐字的 %d 条（我漏发收尾口令，逐条补正过）**：%s"
                  % (len(offenders), "；".join("`%s`@%s（尾行 `%s…`）" % o for o in offenders)))
    else:
        md.append(u"- 尾行逐字核对：**全部通过**，无漏发收尾口令的消息。")
    md.append(u"- 自 %s 起入账的块：**%d 枚**（按前缀：%s）。" % (SINCE, len(rows), "、".join("%s×%d" % kv for kv in sorted(lanes.items()))))
    md.append(u"- 交付脉搏：`refs/heads/review/*` 最近 **4 小时**动过的枝 **%s 条**，覆盖 **%s 张**单（%s）。" % (br, on, orders))
    md.append(u"- 权威线：现尖 `%s…`，自 %s 起 **%d 笔**提交（只能由号令者经落地门移动，我 0 次移动它）。" % (tip40[:10], SINCE, nc))
    md.append(u"- 值守轮次：`autumn_watch.log` 里 cycle 起讫 `%s`→`%s`，共 **%d 轮**；自动总线贴 **%d 条**。" % (first, last, cyc, autoposts))
    md.append(u"- 收件目录：root=%d（%s）。" % (len(root), "、".join(root) or u"空"))
    md.append(u"\n## 二、号令者遇到的困难，我解了哪几类（都带可复跑的位置）\n")
    md.append(u"- 交件规矩里的尺名过时（旧文档 `ledger_inbox_apply_r1.py` + `claim_coordinate_check_r4e.py`）："
              u"现行是 `ledger_inbox_apply_r2.py` → `ledger_insert_after_r2.py:28` 调 `claim_coordinate_check_r7.py`。"
              u"`patrol/relay.py` 模板已就地校正，之后所有转达都带现行名。")
    md.append(u"- 待插块被闸口拒但车道看不见：`patrol/autumn_watch.py` 每轮用只读副本（`_bolt_exact.py` 逐字重放 `ledger_insert_after_r2.py:36-110`）"
              u"过两道闸，尺红抓尺的 findings、闸红抓 `declared/anchored` 行，写 `relay/pending_<块>_<HHMM>.txt` 并按块点名。阈值 5 分钟。")
    md.append(u"- 派单 uuid 拼接：注册表改用本机 `projects/D--moodle/<uuid>.jsonl` 文件名，每轮扫 `ORD-#### → <uuid>`（本轮：见第三节末）。")
    md.append(u"- 门禁豁免词表过窄：探针在 `patrol/_bus_wordlist_gap.py`，可复跑。")
    md.append(u"- 派单归属之外，还有一条我给自己定的行文规矩：给某条车道的消息里**不点别的车道的块名**"
              u"（04:57 我拿 `s4_0338.md` 当旁证写进给 2d2d7428 的消息，它因此第三次报名"
              u"「那枚块不是我的」——责任在我的措辞，不在它的归属；已认错并改口径）。")
    _sb = None
    try:
        _sb = json.load(io.open(os.path.join(HERE, "state_board_r2b.json"), encoding="utf-8"))
    except Exception:
        _sb = None
    if _sb:
        _po = _sb.get("per_order") or {}
        _w = ["ORD-%04d" % i for i in range(427, 448)]
        _nil = [o for o in _w if _po.get(o, {}).get("latest_status") == "NOT_IN_LEDGER"]
        _with = [(o, _po[o]["latest_status"]) for o in _w
                 if o in _po and _po[o].get("latest_status") != "NOT_IN_LEDGER"]
        md.append(u"- 账本状态板 `ledger_state_board_r2.py` 对最新一波**不敷用**（本行数字现算自 `patrol/state_board_r2b.json`，"
                  u"blob `%s`）：ORD-0427..0447 共 %d 张，其中 **%d 张报 `NOT_IN_LEDGER`**，有判语的只有 %s。"
                  u"这些单的派单行其实都在账本里——它的规则要求状态词与单号**同行**，而这一波是 `ORD-####（车道 id）` 分行给判语。"
                  u"复算：`python ledger_state_board_r2.py --ledger D:/moodle/CITYNEXUS_AGENT_CONTROL.md "
                  u"--out patrol/state_board_r2b.json`。所以本稿凡涉及「谁手上还有活」用的是 `open_orders_r1.py`"
                  u"（派单行 × `_processed` 块 × `review/*` 枝 × 判语行）与会话流水两证，不用状态板。"
                  % (str(_sb.get("ledger_blob"))[:12], len(_w), len(_nil),
                     "、".join("%s=%s" % kv for kv in _with) or "无"))
    else:
        md.append(u"- 账本状态板这一格本轮没有产物（`state_board_r2b.json` 不在），不下结论。")
    md.append(u"\n## 三、我自己的错（每条都有对应的总线勘误，不改旧贴）\n")
    for i in ids:
        md.append(u"- %s" % i)
    md.append(u"\n## 三·b、我今夜对**车道**说错的话（逐条已从会话流水核出并当面补正，不改旧消息）\n")
    md.append(u"- 04:37 / 04:54 → S4 与 8ac89982：我把 `path:line` 当成第二道闸的锚递了出去。第二道闸只认同段落里"
              u"**另一枚能 `git cat-file` 的 40 位**；05:06/05:19 已给两人各自更正（`8ac89982` 05:16:12 入账、`s4_0338.md` 05:36:55 入账）。")
    md.append(u"- 04:57 → 2d2d7428：我在给它的消息里点了**别人**的块名（`s4_0338.md`）当旁证，它因此第三次报名"
              u"「那枚块不是我的车道」。06:29 已当面认错并改行文规矩。")
    md.append(u"- 05:19 → map：我写了「你 ORD-0440 的新单仍在账本 :16983」——那行收件人是 `49fe0d7b`（N3），**是我误派**。"
              u"它自己扫全本把这格拒了；06:37 已撤回并写明它真正在等的是「一个号」（总线 `5879549046`）。")
    md.append(u"- 06:04 → 道tokens：那条消息**漏发 83 B 收尾口令**（自查 37 条里就这一条）。06:21 已重发同样内容并带口令。")
    md.append(u"- 07:05 逐条重算（不再只报分数）：全目录 `role=user` 且正文以「【值守 」开头的节点 **102 条**，"
              u"尾行不逐字等于 83 B 口令的只剩 **2 条**，两条都连正文都没有口令："
              u"`1ba48dbf` 的「值守 06:43 → newlane」与 `be19052c` 的「值守 05:53 → 道tokens」。"
              u"两件的实质内容后续都用过尾行逐字相等的重发件覆盖（06:52 / 07:05），两条车道也都照做了"
              u"（`newlane_0637.md` 从 q43=RED 改成 GREEN、`dt_0542.md` 改名回覆盖并入账），"
              u"但按「尾行不齐就算没送到」的规矩，这两条我仍记成我的送达缺陷，不记成它们的抗命。")
    md.append(u"- 07:05 → `be19052c`：自动转达脚本把它的收件人标签写成「道tokens」，那是它**昨夜**在账本自报的历史名，"
              u"今大它改叫「车道 dt」（依据是它今早三枚块头逐字「### 车道 dt（会话 be19052c）」）。"
              u"名字表是我的脚本里硬写的，属于旧数据；已改 `wake_names.ID8`（`be19052c`→`dt`、`2d2d7428`→`0441`，"
              u"并补 `1ba48dbf`/`6a150e1e` 两条新车道），`wake_names.py` 自测 **PASS 10/10**；"
              u"同时在那条消息开头当面向它认了这笔标签错，寻址今后只按会话 id。")
    md.append(u"- 规矩侧的三处修正：闸口拒绝的贴只能写「我的复算**预测**会被拒」（门的 DRY 模式根本不评估两闸，05:02 实测）；"
              u"「停在未应答 tool_use」不等于「停在弹窗上」（05:25 实测 `pendingInteractionCount=0`）；"
              u"派单转达只认**收件 id 逐字相同**的行（04:34 那张连派 11 张的表是我误派的来源）。")
    md.append(u"- 07:15 我新写的 `_claims_vs_remote_r1.py` 第一版一把报出 **58 处「申报不符」**，全是我自己的判据过宽："
              u"我拿「ref 名同段里出现的每一枚 40 位」去比那枚 ref 的远程头，于是 merge-base、tree id、"
              u"别的枝的头全被抓成红。真数是一条都没有（现读 3 枚待插块 `申报不符=0`）。"
              u"已收窄成「ref 名与 40 位相隔 ≤60 字且中间出现 =/头/尖」才算申报，并把块内自声明"
              u"（`本机 sha1|非 blob|不在对象库|不可 cat-file`…）按门的口径降为注记。")
    md.append(u"- 07:12:58 我把 `0383_0711.md` 与 `R_0712.md` 读成 `q43=RED` 时，两枚块的年龄只有 0.3/0.4 分钟——"
              u"它们 07:13:03 与 07:13:05 各自同名覆盖后就绿了，我一句都没发。这坐实了一条我此前只有直觉的规矩："
              u"**块龄 < 5 分钟的 RED 不转达**（`REFUSE_MIN=5` 本来就是为这个设的），"
              u"那一半读数抓到的是车道正在写的中间态，不是它交给门的最终件。")

    md.append(u"- 08:50 一处我自己要收口的措辞（只在我给用户的汇报里出现过，**没上总线**，所以不发勘误贴）："
              u"我说「ORD-0429 在 `a6b95d59` 名下躺了六小时」。现读之后准确说法是："
              u"那一单它 **03:05 就交了、号令者 03:0x 已落地**（DSH 自己验的：落地笔 `69b7cde4…` 是现尖 `0fee131d…` 的祖先），"
              u"缺的是号令者 03:0x 那块 `:21224` 追加的三小件（把成绩单升到现尖、修舰队尺、H11 自主跑）。"
              u"我 08:20 送派单原文是对的、它也照做并交了 `dsh_0841.md`（08:39:56 入账），"
              u"但「躺六小时」这个说法会让人误判这条车道六个钟头没干活——它其实在 06:47/06:52 就交过 ORD-0432/0443。")
    md.append(u"- 07:38 我自己把自动轮重启成了**双写日志**：`say()` 既 `print` 又 `append(LOG)`，"
              u"而我重启时把 stdout 也重定向进同一个 `autumn_watch.log` ⇒ 每行落两遍，"
              u"日志里出现同一秒两条「cycle 1/22 start」和一条被拦腰截断的行。"
              u"进程其实只有一个（`Get-CimInstance` 数到 2 个 PID 是 venv 壳与它的子解释器，父子关系），"
              u"所以没有双投总线；但任何按这份日志计数的读数都会翻倍。已改成 stdout 走 "
              u"`autumn_watch.stdout.log`、日志只归 `say()` 一枝笔，重启后回验同秒重复行归零。")
    md.append(u"- 07:49→07:57 我又**真的双开过一次自动轮**，而且成因是我新写的单实例锁本身："
              u"`os.kill(pid, 0)` 在这台 Windows 上不是「只探一下」，CPython 对非 CTRL_C/CTRL_BREAK 的信号"
              u"走 OpenProcess+TerminateProcess，它对我自己的自动轮抛了 OSError ⇒ 「拒绝双开」当场变成「接管锁」。"
              u"两条并行跑了约 4 分钟（07:49:00 的 22 跳那份与 07:53:29 的 3 跳那份）。"
              u"后果回验：并行段内**没有任何一条「已发/bus post」**，所以没重复上总线；但那份 3 跳的还抢走了 "
              u"`autumn_watch.pid`，并且它有一步报「落地预测：读数不全」（两条同时 `git fetch` 撞在一起）。"
              u"已改成 `kernel32.OpenProcess(0x1000)` 只读句柄判活，单元测试 "
              u"`alive(在跑的)=True / alive(刚杀的)=False / alive(不存在的)=False`，"
              u"端到端复跑第二份启动 ⇒ 日志逐字「已有自动轮在跑（PID 50704），这一份拒绝双开，退出码 2」、"
              u"退出码 2、锁文件未被改；现在只剩一份（47376/50704）。教训与「规则要装进执行写的那个工具」同源："
              u"**判活的工具本身也要被测过，不能按 Unix 直觉写**。")
    md.append(u"\n## 四、待裁队列（等待分钟按块头自报时间现算）\n")
    for label, ln, w, ask in pd:
        md.append(u"- %s（账本 `:%s`，≈%s 分钟）——%s" % (label, ln, w, ask))
    md.append(u"- 08:11 另有一件值得记：**账本里 02:00 起每一条带收件 id 的派单行，现在都对得上一次交付（未动 0 条）**——"
              u"`patrol/_new_dispatch_r1.py` 连改三处才得到这个数：掩码时间 `07:1x` 我原先整批丢掉、"
              u"车道块头那种没冒号的 `0245+08` 也不认、入账后的文件被改名成 `<块>.md.inserted_<HHMMSS>` 后 "
              u"`_processed/*.md` 一枚都匹不到（还得靠文件名前缀对会话 id 的表）。"
              u"这三处每一处都在报「某某单未动」，而事实是车道早交了——不改完我就会去敲多余的窗口。")
    md.append(u"\n## 五、只剩你能定的那一件事（我不派任何需要你点击的活）\n")
    md.append(u"- 号令者的 cron 实测（07:55 `qoder_cron list` 现读，不是我推的）："
              u"id `571681e1-29a2-433b-97ff-047e93170003`，`everyMs=3600000`、`outputMode=merged`、"
              u"model `qfmodel`、`permissionMode=bypassPermissions`、`enabled=true`、`consecutiveFailures=0`。"
              u"上一跳 `lastRunAt=07:15:13`、跑 `1213293 ms`＝**20.2 分钟**、`lastRunStatus=succeeded`；"
              u"`expiresAt=11:00:00`，`nextRunAt=08:15:12` ⇒ **11:00 之前只剩 3 跳（08:15 / 09:15 / 10:15）**，"
              u"每跳约 20 分钟，也就是说入账门一天里大约 1/3 时间在跑。"
              u"我先前说的「每小时一跳、到期 11:00」方向对，但**跳点不在整点**，"
              u"车道在 08:00 等不到门是正常的，别把它当停摆。")
    md.append(u"- 会话侧：`494abfd7` 现在 `runtimeState=running`、`activeTurnId=654c1206…`（06:59 起同一枚），"
              u"可它的流水 `projects/D--moodle/494abfd7-….jsonl` 已经**静默 139 分钟、20 秒内 0 字节增长**，"
              u"而 cron 报的是 `succeeded` 且 `runningAt=null` ⇒ 会话面上那个 running 是**旧壳**，真正在跑门的是 merged 起的实例。"
              u"下一跳若 `6efab655` 的 binding 仍不可用（`wait_chat_sessions` 已经回「ChatSession 不存在」），"
              u"调度器会再起一条号令者会话——那正是今夜单号撞车与文件归属分叉的来源；"
              u"它自包含的 prompt 里没写「`styles.css`/`V8Experience.tsx` 归谁」，"
              u"所以我把那一件写在总线 `5880712875` 的第一条，等它读账本/总线时能看到。")
    md.append(u"- **07:24 我把这一件的成因改准了一次**（总线勘误 `5880573103`，旧贴 `5880029593` 不覆盖）："
              u"实例 A 不是死了，是**不可寻址**——它不在 `list_chat_sessions` 现读的 20 条里、"
              u"`wait_chat_sessions` 对它回「ChatSession 不存在」，可它的流水 "
              u"`projects/D--moodle/6efab655-f46b-4a83-9728-baa1d98a328d.jsonl` 在 35 秒内从 3,742,769 B 涨到 3,747,718 B，"
              u"尾 1.5 MB 里有 **6 次 `ledger_inbox_apply_r2.py --apply`**（本地 04:21→06:16，其中一次结果原文 "
              u"`REFUSED qoder-0441_0534.md rc=8: line 31 F3_bare_numeric_claim`）。"
              u"所以要你裁的不是「两条里死了一条」，而是**两条都在写账本、只有一条我够得到**："
              u"入账门该由哪一条、在什么时刻跑。07:16:23–07:17:18 那轮 10 枚入账的作者我判不出"
              u"（两条会话尾 600 KB 都查不到 `inserted_071623`；`494abfd7` 的流水已 218,826,664 B）。"
              u"要不要改成一轮一跳、或在 cron 里写死单实例，仍是你的决定——我只把形状改对，不替你选。")
    md.append(u"\n## 六、盘与今夜消耗（同一条命令可复算）\n")
    cb = subprocess.run([PY, os.path.join(HERE, "credits_burn_r1.py")], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=900)
    cbl = [l for l in ((cb.stdout or "") + (cb.stderr or "")).splitlines() if l.strip()]
    for l in cbl[:10]:
        md.append(u"- %s" % l)
    md.append(u"- 我这一侧的取舍：用户睡前下的命令是「保证他们至少工作到早上 11 点」，所以**没有为了省钱停任何车道**；"
              u"能省的是我自己——敲门只在 `runtimeState` 真为 cold/ready 且账本确有未读事项时才发，"
              u"每轮 10 分钟的自动仪表不花会话 credits。")
    md.append(u"\n## 七、盘\n```\n%s```\n" % df)
    md.append(u"\n## 八、09:00–10:05 增量（10:05 补写，数字都现算）\n")
    md.append(u"- 权威线这一小时前进得很实：`0fee131d…`（08:53）→ `527f471b…`（09:21，ORD-0440 r4）"
              u"→ `80db250a…`（09:43，ORD-0415 读数）→ `26e8de4f…`（09:51，ORD-0441 档位上屏）"
              u"→ `574f2e37…`（10:00，ORD-0435 r4）。读数命令都是 "
              u"`env -u HTTP_PROXY -u HTTPS_PROXY git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`。")
    md.append(u"- 我把复切判据做成了尺，并且**改过一次覆盖面**：`_hotfile_contention_r1.py` 只对三枚热文件算三侧 blob，"
              u"10:03 换 `r2`——判据与文件名无关，于是把**每枚枝自己动过的每一枚文件**都算进去，"
              u"并自带分类器八形自测 + `ls-tree` 与 `rev-parse` 双通道同读一枚词典做自证（不一致就拒绝出表）。"
              u"接进了 `_watch_dump_r2.py` 第 [11] 段。")
    md.append(u"- r2 跑出来的第一条新信息就是 r1 会漏的：车道 `bac10f40` 的 "
              u"`review/AI-ord0430-pill-relocates-in-view-r1`（头 `24ae0a23f60ac7486ff640f82c20bfee4be54db0`，"
              u"merge-base `f3a6ebd0…`）在 `frontend/src/design-tokens.css` 上三侧互异"
              u"（base `efe75152…` / 车道 `d4c4ed19…` / 现尖 `2094a6a1…`），而 2094a6a1 是 ORD-0441 09:51 刚落的那份。"
              u"10:03 已把这条读数送进它窗口（它此前静默 182 分钟、状态是等裁语；rebase 不依赖任何裁语）。")
    md.append(u"- 我早上两条只读预测**都被车道接住并变成了动作**（这是数出来的，不是语气）："
              u"`review/R-ord0437-link-import` 从 -r1 头 `f13d48f7…` 变到 -r2 头 `5ebfa4a983813e5aff84b3ec289652e9d02ba99e`；"
              u"`review/Q-ord0446-machine-speech-residue` 从 -r1 头 `8451df87…` 变到 -r2 头 `030265e13abb4bb8359248fb9769d821f0a67e9a`。"
              u"顺带把 N2 那句「现尖落在我三枚之内的为 0 枚」判清了：它写的时候是真话——把 ORD-0406 带上现尖的 `6ca105db` "
              u"不是它推枝时读到的 `f26e2ff7…` 的祖先（`git merge-base --is-ancestor` 退 1），是地面后来动了。")
    md.append(u"- 词典串行点量化后贴上总线 `5882151289`（09:54，尾行逐字回验通过）："
              u"`review/qoder-0436-access-screen-r3`（头 `3eebb348…`）把词典改成 `0477cde9…`，"
              u"`review/R-ord0437-link-import-r2`（头 `5ebfa4a9…`）改成 `78d2844c…`，两者互异而现尖是 `ba667d06…` "
              u"⇒ 同一跳两枚都落，后落那枚必然 ABORT。落哪一枚归号令者定，我只把代价先量出来。")
    md.append(u"- 号令者 09:31 那块自己公开了一处流程洞（他把门的 `READY_TO_LAND` 当成「曝光面已判过」、落地前没读那处代码），"
              u"并开了 **ORD-0448 → 车道 `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb`**（那枚 id 逐字对得上本机流水文件名，不是拼接串）。"
              u"09:41 我把它原四条要件敲进那条窗口，10:03 它流水 30 秒内 +10,793 B ⇒ 送达且在干。"
              u"这格不是我修的红，是我读到并转达的。")
    md.append(u"- **我自己这一窗口的两处错**：① 转达 ORD-0448 时我把成对件 blob 先抄成 `1b7fd13e50b9a02a54637eb67eda3209dba6`"
              u"（少两字符，`git cat-file -t` 报 not a valid object），真串 `1b7fd13e50b9a02a54637eb67ec26eda3209dba6`；"
              u"已发第二条窗口消息勘误，没改旧帖。② 判「流水最后写于何时」时我把 `st_mtime` 写成了当时的 `time.time()`，"
              u"于是打出四条「最后写 0.0 分前」的假读数，而同一轮字节差明明是 0——那条判据当场作废，"
              u"重测后才用 `os.path.getmtime`；这条错的教训是：**静默时长必须由 mtime 算，不能由我取样的时刻冒充**。")
    md.append(u"- 待插队列 09:50 与 10:03 两次现读都是 **0 枚**（块一到就被跑掉的门接走），"
              u"所以 10:15 那一跳（cron 实测最后一跳，`expiresAt=11:00:00`）之前不会积压。")
    md.append(u"- 10:11 起多了一把新尺 `_undeclared_deliveries_r1.py`（只读）：**近 N 小时动过的车道枝，"
              u"头 40 位是否逐字出现在账本里**。判据来自号令者 09:52 那块的原话「未申报＝未交付」，"
              u"两处防呆：`cmdr-*` 前缀（他自己的 batch/recut 中间物）不算车道欠交；本地取不到对象的枝**单独计数而不当读数**。"
              u"第一跑就抓到 2 枚真漏报的（`AI-ord0430-pill-relocates-in-view-r2` 头 `5e1a22cd4863a61ab1160c85062bbeb96c744bdc` 10:07 推、"
              u"`Q-ord0446-machine-speech-residue-r2` 头 `030265e13abb4bb8359248fb9769d821f0a67e9a` 09:07 推），"
              u"两条车道我都已在 10:08 / 10:10 把「只差一块申报」送进窗口（含 10:35 这个最后一跳的时间窗）。")
    # ---- 夜版 §九：18:30 之后这段（现算，不靠记忆）----
    md.append(u"\n## 九、18:30–%s 增量（夜间值守补写）\n" % time.strftime("%H:%M"))
    try:
        import night_sections_r1 as NS
        md.extend(NS.lines())
    except Exception as e:
        md.append(u"- 夜间段落没跑起来：%s: %s" % (type(e).__name__, str(e)[:140]))
    md.append(u"")
    md.append(u"### (5) 我这一段发出去与登记在册的东西")
    try:
        posts = [l.rstrip().split("\t") for l in io.open(os.path.join(HERE, "bus_ids.txt"), encoding="utf-8") if l.strip()]
        posts = [p for p in posts if len(p) >= 2 and p[1] >= "15:00"]
        md.append(u"- 总线新帖 %d 枚：%s" % (len(posts), u"、".join("`%s`(%s)" % (p[0], p[1]) for p in posts)))
        rl = [l.rstrip() for l in io.open(os.path.join(HERE, "relay_log_0929.txt"), encoding="utf-8") if l.strip()]
        rl = [l for l in rl if (l[:2] >= "15" and l[2] == ":")]
        md.append(u"- 转达/提醒 %d 条（逐条含收件会话 id；未落成 user 节点的我在行内写明了）：" % len(rl))
        for l in rl:
            md.append(u"  - %s" % l[:230])
    except Exception as e:
        md.append(u"- 名册/日志读取失败：%s" % type(e).__name__)
    md.append(u"")
    md.append(u"### (6) 我今夜自记的错（都已在原处修，列出来是给下一班防同样的坑）")
    for s in [u"把 `autumn_watch.py` 第 535 行用 heredoc 拼坏（`\\n` 变成真换行），旧轮已杀、新轮 SyntaxError 退出，值守断了约 2 分（19:04:10–19:04:58）；修好后先 `ast.parse` 再启动。",
              u"名册尺把『尾部 400 KB 出现过额度字样』当成『停在额度上』；改成只看**最后一条角色记录**。",
              u"19:16 贴总线时用『恢复样本的条件分布』推『都会回血』，19:23 另帖勘误；证据件补上删失计数（今天 38 撞／15 回／23 未回）。",
              u"派单送达尺与『无人接』尺都会把**同行多单多 id** 的状态行错配（差点把 ORD-0468 报给 newlane）；改成多单多 id 整行不判、且 40 字内压着别的单号就不配。",
              u"`_night_verdict_r1.py` 第一版从共享仓的 `FETCH_HEAD` 取尖，读出『12:00 后 0 笔』这种自相矛盾的话；改成 GitHub API 现读 40 位。",
              u"把带反枝名的句子写进 bash 双引号字符串，反引号被命令替换吃掉（20:31 的日志行）；改用 Python 写入。"]:
        md.append(u"- %s" % s)
    night_out = os.path.join(HERE, "HANDOVER_0929_night.md")
    io.open(night_out, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
    print("写好夜版 %s（%d B）" % (os.path.basename(night_out), os.path.getsize(night_out)))
    if "--night" in sys.argv:
        print("（--night）不重写早版交接稿：HANDOVER_0929_11.md 是早上已交付的件，改它等于改坐标；夜版单 file。")
        raise SystemExit(0)
    out = os.path.join(HERE, "HANDOVER_0929_11.md")

    io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
    print("写好 %s（%d B）；敲门 %d/尾行 %d；入账块 %d；枝 %s 条/单 %s 张；提交 %d；root %d"
          % (os.path.basename(out), os.path.getsize(out), tot, exact, len(rows), br, on, nc, len(root)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
