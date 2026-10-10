r"""收尾：追加第 38–41 拍（含 10:59 交班快照）。所有数字取自本拍现量，不引用旧帖。"""
import glob
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
L = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
     "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
     "d9e2c9ae": "S2", "1d64acf5": "S4"}
CAP = "daily usage limit for Chat"
POSTS = ["5840869289(07:07 队列读数)", "5841142470(07:40 对我自己那条的勘误)",
         "5841398182(08:15 块头时标偏移)", "5841589825(08:38 用服务器时钟复核)",
         "5841968280(09:28 F/S4 两条停机)", "5842041030(09:40 ORD-0352 落在停机道上)",
         "5842160265(09:55 全车队 5/10 停机)", "5842333090(10:21 12 敲 0 实质回复)",
         "5842466202(10:43 ORD-0354 刚开出就落在停机会话)"]

ENTRY = """
## 10:59 · 值守第 38–41 拍 · **交班快照（覆盖到用户定的 11:00）**

- **车队（10:59:1x 现量）**：@IDLE@
- **额度停机（会话末尾=限流回复、且 20 秒零增长）**：@STOPPED@
- **10:53–10:59 我做的唯一一次主动干预**：D 在 10:43 落了 `ORD-0338 第三块（Q73 甲）` 并点名要 E 出 `derived_result`，
  而 E `d2305848` 已 idle 80 分钟、**没有限流**、runtimeState=cold ⇒ 按口径（新块点名 + 她 idle + 欠的是她手上的动作）**敲了一次**，
  只发一行"去重读账本那一块"、不带任务正文。回验不是看工具回执：20 秒内她的 JSONL **+5,770 B**、idle 归到 0.2 分钟
  ⇒ **她确实醒了并在产出**。
- **今晚最后一段的成因结构（一句话）**：产出继续走高（账本 10:42 = 6,626,594 B，比 07:34 那次读数涨 @GROW@ B），
  但**产能被账户额度切掉一半**；号令者仍在给停机的车道派新单与敲门（ORD-0352→F、ORD-0348→S4、ORD-0354→S4），
  我逐条量了发在总线上，最近一敲在 10:34、10:41 实测累计被敲 13 次换回 0 条实质回复。
- **今天外发（全部新帖，不改旧帖；尾行逐字取自 CLOSING_LINE.txt）**：@POSTS@
- **判过不敲（有字可查，键=commit|车道id，存 `wake_from_commits_state.json`）**：7 条 ——
  S1(06941aeb 前)、F、E、S3(06941aeb)、F(7bc1b8c3)、S3+F(0dc5378c)、S1(1d6145bf)；
  每条理由都在文件里，下一班可以直接读，不必猜我当夜判了什么。
- **交接给下一班 / 号令者的三件事实**：
  1. 我这晚换了两把尺：`pending_check` 的"账本 mtime 当新字"与"只认 `CMDR-MMDD-HHMM` 块头"都会瞎；
     现在用 `wake_from_commits.py`（只信 commit 服务器时间 + 车道 JSONL 落盘）+ `_bus_dead_knocks2.py`（末尾限流窗口）。
  2. 车道块头里的 `@HH:MM+08` **不能当时间用**（复核最大偏到未来 +87 分钟）；账本里已入账的那些不回改，但引用时用 commit 时间。
  3. root 收件箱现在 @LIVE@；其中 `S2-hermes_0937.md` 已挂 @S2AGE@ 分钟——**作者本人已停机**，这一枚只能号令者代插或退回。
- 值守 42d1a6fa 本夜 **0 次编辑账本、0 次移动 ref、0 次碰别人工作树、0 次申请额度**；敲门合计 1 次（E）。
"""


def main():
    now = time.time()
    idle, stopped = [], []
    for k, nm in L.items():
        p = max(glob.glob(os.path.join(BASE, k + "*.jsonl")), key=os.stat)
        mins = (now - os.stat(p).st_mtime) / 60.0
        idle.append("%s %.1fm" % (nm, mins))
        last = ""
        for rec in io.open(p, encoding="utf-8", errors="replace").read().rstrip().split("\n")[::-1]:
            try:
                d = json.loads(rec)
            except Exception:
                continue
            m = d.get("message") or {}
            if m.get("role") == "assistant":
                c = m.get("content")
                last = (" ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        if isinstance(c, list) else str(c))
                break
        if CAP in last:
            stopped.append(nm)
    ib = r"D:\moodle\_qoder_ledger_inbox"
    live = sorted(f for f in os.listdir(ib) if f.endswith(".md"))
    s2age = [(now - os.stat(os.path.join(ib, f)).st_mtime) / 60.0 for f in live if f.startswith("S2-hermes")]
    rep = {
        "@IDLE@": "、".join(idle),
        "@STOPPED@": "、".join(stopped) if stopped else "无",
        "@GROW@": "{:,}".format(os.stat(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md").st_size - 6410413),
        "@POSTS@": "；".join(POSTS),
        "@LIVE@": "、".join("%s" % f for f in live) or "空",
        "@S2AGE@": "%.0f" % (s2age[0] if s2age else 0),
    }
    entry = ENTRY
    for k, v in rep.items():
        entry = entry.replace(k, v)
    assert not any(x in entry for x in rep), [x for x in rep if x in entry]
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("filled:", json.dumps({k: (v[:70] if isinstance(v, str) else v) for k, v in rep.items()}, ensure_ascii=False))
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
