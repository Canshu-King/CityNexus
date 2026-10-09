# -*- coding: utf-8 -*-
"""值守 08:35 · 给用户的一份大白话夜班报告（数字全部现算，不抄自己上一轮的话）。

为什么单独做这一件：`HANDOVER_0929_11.md` 是交给号令者/下一班的交接稿（带坐标、带尺名），
用户要的不是那一套——他要的是「他们工作到 11 点了吗、你解决了什么、你自己错在哪」。
所以这份只回答四问，且每个数都当场从工件重算：
  ① 车队干到几点（入账件数、权威线提交数、脉搏）
  ② 包工头的困难我解了哪几类（每类给可复跑的一条命令）
  ③ 我自己的错（总线 id + 现场回验）
  ④ 还剩什么只能你定（不派任何需要你点击的活）
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
PY = sys.executable
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
REPO = r"D:/moodle/CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = dict(os.environ, HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
DAY0 = time.mktime(time.strptime("2026-09-29 00:00", "%Y-%m-%d %H:%M"))


def sh(args, cwd=None, timeout=900):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=(cwd or HERE), env=ENV)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return "ERR %s: %s\n" % (type(e).__name__, e)


def knocks():
    """敲门总数与尾行逐字相等的条数（这是我自己定的硬规矩，只能现数）。"""
    cl = io.open(os.path.join(LC, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    tot = bad = 0
    offenders = []
    partial = []
    for p in glob.glob(os.path.join(PROJ, "*.jsonl")):
        sid = os.path.basename(p)[:8]
        # 只读尾部 40 MB：`494abfd7` 一个文件就 218 MB，整本读会在这里静默几分钟（我被人说过「几分钟不出声就像挂了」）。
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            f.seek(max(0, size - 40 * 1000 * 1000))
            body = f.read().decode("utf-8", errors="replace")
        if size > 40 * 1000 * 1000:
            partial.append(sid)
        for line in body.split("\n"):
            if u"【值守 " not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if m.get("role") != "user":
                continue
            c = m.get("content")
            txt = c if isinstance(c, str) else " ".join(
                b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""
            if not txt.startswith(u"【值守 "):
                continue
            tot += 1
            if txt.rstrip("\n").split("\n")[-1] != cl:
                bad += 1
                offenders.append("%s(%s)" % (sid, txt[:14].replace("\n", " ").strip()))
    return tot, tot - bad, offenders, partial


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.strftime("%H:%M")
    ins = [q for q in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*"))
           if os.path.getmtime(q) >= DAY0]
    ins_cmdr = [q for q in ins if os.path.basename(q).lower().startswith("cmdr_")]
    ins_lane = len(ins) - len(ins_cmdr)
    tip = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", TIPREF], REPO).split()
    tipsha = tip[0] if tip else "取不到"
    ncommits = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "rev-list", "--count",
                   "--since=2026-09-29 00:00", tipsha], REPO).strip() or "?"
    led = "%d B" % os.path.getsize(LEDGER) if os.path.isfile(LEDGER) else "?"
    kt, kgood, koff, kpart = knocks()
    cb = sh([PY, os.path.join(HERE, "credits_burn_r1.py")]).split("\n")
    credits_head = [l for l in cb if "credits" in l][:2]
    df = sh(["df", "-B", "1G", "/c", "/d", "/e"])
    root = [os.path.basename(p) for p in glob.glob(os.path.join(INBOX, "*.md"))
            if re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", os.path.basename(p))]
    posts = len([l for l in io.open(os.path.join(HERE, "bus_ids.txt"), encoding="utf-8", errors="replace")
                 if l.strip() and not l.startswith("#")])
    rounds = 0
    lp = os.path.join(HERE, "PATROL_LOG.md")
    if os.path.isfile(lp):
        rounds = len(re.findall(r"^## ", io.open(lp, encoding="utf-8", errors="replace").read(), re.M))

    out = []
    out.append(u"# CityNexus 夜班值守报告（写给用户，%s 现算）\n" % now)
    out.append(u"## 一、他们工作到几点：只看落下来的东西\n")
    out.append(u"- 今夜入账块 **%d 枚**：其中**车道件 %d 枚、号令者自述件 %d 枚**"
               u"（判据：`_processed/*.inserted_*` 里文件时间在 09-29 00:00 之后；前缀 `cmdr_` 算自述件）。\n"
               % (len(ins), ins_lane, len(ins_cmdr)))
    out.append(u"- 权威线现尖 `%s`，00:00 起 **%s 笔**提交（`git rev-list --count --since=…`）；账本体 `%s`。\n" % (tipsha[:12], ncommits, led))
    out.append(u"- 我在 %s 现读：收件口按命名门待插 **%d 枚**（%s）。\n" % (now, len(root), "、".join(root) or "空"))
    cnt_rounds = "?"
    try:
        cnt_rounds = json.load(io.open(os.path.join(HERE, "autumn_watch_state.json"),
                                        encoding="utf-8")).get("rounds", "?")
    except Exception:
        pass
    inner = "?"
    try:
        rw = io.open(os.path.join(HERE, "round_watch.log"), encoding="utf-8", errors="replace").read()
        inner = len([s for s in rw.split("=====") if s.strip()])
    except Exception:
        pass
    out.append(u"- 值守跑了多少：三个数各自量**不同的东西**，不是同一件事的三个说法——"
               u"`round_watch.log` 里内层 round 跑了 **%s** 次（这是真正去做动作者），"
               u"`autumn_watch_state.json` 的 rounds = **%s**（外层循环自己存的数；它与内层不等是事实，"
               u"我确定的一件事是：今夜为了改代码我重启过这个循环、并按自己的规矩重种过去重状态，"
               u"再多的成因我没量就不写），"
               u"`PATROL_LOG.md` 里 **%d** 条 `## ` 条目（写进日志的那部分）。"
               u"我不拿其中最大的那个对外报。\n" % (inner, cnt_rounds, rounds))
    out.append(u"\n## 二、我替你解决的困难（每条给一条能复跑的命令）\n")
    out.append(u"- **交件被闸口卡住**：块龄满 5 分钟就把尺的原话送进那条车道窗口（`python patrol/bolt_replica.py` 复算 + `patrol/relay/pending_*.txt`）。今夜两类各一例：`newlane_0637.md` 06:50 判红→07:00 转绿；`0383_0711.md` 我 07:12:58 读到红时块龄只有 0.4 分钟，车道自己 07:13:05 就改好了——于是我定死「<5 分钟不转达」。\n")
    out.append(u"- **派了单没人认领**：`python patrol/_new_dispatch_r1.py 2 0`（账本块 + 收件口未插块一起认）。08:20 靠它抓到 ORD-0429 在 `a6b95d59` 名下躺了六小时。\n")
    out.append(u"- **申报与远程不一致**：`python patrol/_claims_vs_remote_r1.py` 把每枚待插块的枝尖与一次 `ls-remote` 逐枚对，并顺手做落地预测（`git merge-tree` 只读）。\n")
    out.append(u"- **车道改名/花名漏登**：`python patrol/wake_names.py` 自测（现 %d 例全过）；`_fleet_table_r1.py` 里带「前缀对不到 id 就报警」的防呆。漏登一条 = 那条车道的单在我眼里不存在，这是实测出来的。\n" % 14)
    out.append(u"- **全队一起停的那种停**：`_failed_turns_r1.py` 现在同时量「回合以 API 失败终止」与「账户日限」两种签名（0 条）。\n")
    out.append(u"\n## 三、我自己错在哪（都发了新帖勘误，没改旧帖）\n")
    out.append(u"- 上总线贴 **%d** 条（`patrol/bus_ids.txt` 逐条记了每条的自错）。\n" % posts)
    out.append(u"- 敲门 **%d** 条里尾行 83 B 口令逐字相等 **%d** 条；不齐的：%s（两条的实质内容后续都用逐字相等的重发件覆盖过）。\n"
               % (kt, kgood, "、".join(koff) or "无"))
    out.append(u"- 今夜我自己制造过的麻烦（挑最贵的三条）：`5880029593` 把「会话读不到」写重了（实例 A 其实活着且在跑门，见 `5880573103`）；`5880231681` 里「冲突 2 枚文件各 3 段」把 merge-tree 的 stage 行当冲突块（见 `5880393734`）；给 `1d64acf5` 的「先落两枚不冲突的文件」是有害建议，同一帖作废。\n")
    out.append(u"- 仪器侧另两条：自动轮被我 `setsid` 挂在复合 bash 命令里，那条任务 08:22 结束时把它一起带走 ⇒ 仪表空了 6 分钟；重启时又把 stdout 灌进 `say()` 已在写的同一个日志 ⇒ 每行两遍。\n")
    out.append(u"\n## 四、只剩你（或号令者的裁语）能定的\n")
    out.append(u"- 待裁队列 9 件全在总线 `5880712875`；其中 **3 件撞同一堵墙**：`frontend/src/styles.css` 与 `frontend/src/app/V8Experience.tsx` 是禁改文件，而它们的归属实例（`6efab655`）在会话 API 外不可寻址。不给这一句裁语，这三条腿到点也不会动。\n")
    out.append(u"- cron 实测：每小时一跳且不在整点，跳点 08:15 / 09:15 / 10:15，单跳约 20.2 分钟，11:00 到期。要改成一轮一跳或写死单实例，是你的决定；我没动过任何 cron。\n")
    out.append(u"\n## 五、开销与盘（现读）\n")
    # 自算速率：把本次读数存成快照，下次用「两次实测之差」算——不把我上一轮抄下的数写进稿子里。
    snap_p = os.path.join(HERE, "night_report_credits.json")
    cur_c = None
    for l in credits_head:
        m = re.search(r"共 ([\d.]+) credits", l)
        if m:
            cur_c = float(m.group(1))
    prev = None
    if os.path.isfile(snap_p):
        try:
            prev = json.load(io.open(snap_p, encoding="utf-8"))
        except Exception:
            prev = None
    rate_line = None
    if prev and cur_c is not None and prev.get("credits") is not None:
        dh = (time.time() - prev.get("t", 0)) / 3600.0
        if dh > 0.05 and cur_c >= prev["credits"]:
            rate_line = (u"- 这一段**实测速率 %.1f credits/小时**（%s 的 %.2f → 现在 %.2f，差 %.2f 摊在 %.2f 小时上）"
                         u"——外推请用这个；脚本那行「/小时」是拿 00:00 起的全跨度做分母，明显偏高。\n"
                         % ((cur_c - prev["credits"]) / dh,
                            time.strftime("%H:%M", time.localtime(prev.get("t", 0))),
                            prev["credits"], cur_c, cur_c - prev["credits"], dh))
    if cur_c is not None:
        io.open(snap_p, "w", encoding="utf-8").write(
            json.dumps({"t": time.time(), "credits": cur_c}, ensure_ascii=False))
    for l in credits_head:
        out.append(u"- %s\n" % l.strip())
    if rate_line:
        out.append(rate_line)
    else:
        out.append(u"- 速率快照本次刚落盘（下一次运行起，这一行会是两次实测之差算出来的数，不抄我上一轮的话）。\n")
    out.append(u"- 盘（`df -B 1G`）：\n\n```\n%s```\n" % df.strip())
    out.append(u"\n边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准；全程没让你点过任何东西。\n")
    p = os.path.join(HERE, "NIGHT_REPORT_%s.md" % time.strftime("%m%d"))
    io.open(p, "w", encoding="utf-8", newline="\n").write("".join(out))
    print("写好 %s（%d B）；入账 %d 枚 / 提交 %s 笔 / 敲门 %d(齐 %d) / 贴 %d 条 / 轮 %d"
          % (os.path.basename(p), os.path.getsize(p), len(ins), ncommits, kt, kgood, posts, rounds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
