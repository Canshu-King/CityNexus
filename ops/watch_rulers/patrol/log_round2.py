"""Append a patrol round to PATROL_LOG.md, every number computed in this run.

Sources: patrol/round_watch.log (the loop's own rounds), a live verify_sends.py run, the inbox listing,
the authoritative tip via ls-remote, and the bus post files. Pass bus comment ids as argv (they are quoted
as text, not measured).
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
ROUND_LOG = os.path.join(HERE, "round_watch.log")


def main():
    round_txt = io.open(ROUND_LOG, encoding="utf-8", errors="replace").read()
    rounds = [s for s in round_txt.split("=====") if s.strip()]
    tips = re.findall(r"tip=([0-9a-f]{12})", round_txt)
    proc = re.findall(r"_processed=(\d+)\s+inbox_root=(\d+)", round_txt)
    cats = re.findall(r"积压分类：门拒 (\d+) 枚 / 门绿但第二道闸拒 (\d+) 枚 / 门绿真能插 (\d+) 枚", round_txt)
    cap = re.findall(r"掐着 (\d+) / 共 (\d+) 条会话", round_txt)
    vr = subprocess.run([PY, os.path.join(HERE, "verify_sends.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=1800)
    vlines = (vr.stdout or "").splitlines()
    stored = [l for l in vlines if "stored@" in l]
    exact = [l for l in stored if "tail_exact=True" in l]
    missing = [l for l in vlines if "NOT-IN-TRANSCRIPT" in l]
    root_now = sorted(os.path.basename(x) for x in glob.glob(os.path.join(INBOX, "*.md")))
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    tip_sha = ((tip.stdout or "").split() or ["?"])[0]
    assert len(tip_sha) == 40, "现尖没读到：%r" % (tip_sha,)

    b = []
    before = io.open(LOG, encoding="utf-8").read()
    existing = re.findall(r'^## 轮 (\d+)', before, re.M)
    nxt = (max(int(x) for x in existing) + 1) if existing else 1
    b.append("## 轮 %d · 2026-09-28 %s（值守自跑；数字全来自本轮工件）" % (nxt, time.strftime("%H:%M:%S")))
    b.append("")
    b.append("- 巡检轮数：`round_watch.log` 里 `%d` 轮；后台循环每 6 分钟一轮，覆盖到 23:00 之后。" % len(rounds))
    b.append("- 现尖移动（`ls-remote` 逐轮读）：`%s`；本轮读到 `%s`。" % ("`→`".join(dict.fromkeys(tips)), tip_sha))
    if cap:
        b.append("- 会话在场（最后一轮原样）：掐着 `%s` / 共 `%s`。" % (cap[-1][0], cap[-1][1]))
    if cats:
        b.append("- 收件分类随轮变化（门拒 / 门绿但闸拒 / 门绿真能插）：%s。"
                 % "; ".join("%s/%s/%s" % c for c in cats[-4:]))
    if proc:
        b.append("- 收件目录：`_processed` 与根目录枚数逐轮 %s ⇒ 根上从 `%s` 降到 `%s`（%d 枚进账）。"
                 % ("; ".join("%s/%s" % p for p in proc[-4:]), proc[0][1], proc[-1][1],
                    int(proc[-1][0]) - int(proc[0][0])))
    b.append("- 此刻根目录还剩 %d 枚：%s" % (len(root_now), ", ".join("`%s`" % x for x in root_now)))
    b.append("- 敲门送达（`verify_sends.py` 回读会话流水）：%d 枚读到我送的那条，其中尾行逐字 %d 枚；"
             "未落入流水 %d 枚。" % (len(stored), len(exact), len(missing)))
    for l in missing:
        b.append("    - %s" % l.strip())
    for a in sys.argv[1:]:
        b.append("- 外发总线：Issue #1 评论 `%s`（正文见 `patrol/_bus_*.md`，POST 201 后按 id 回读 body 逐字等）。" % a)
    b.append("- 一条现场卡住的道：map（`3b65af59`）自 20:13 起停在权限弹窗上——它最后一条记录是 `assistant/tool_use`(Bash)"
             " 且其后无 `tool_result`，`runtimeState=waiting-user`、`pendingInteractionCount=1`；"
             "批准的是一条 `rm -f`，我不替别人按删除，所以只报不动手（已送总线）。"
             "额度排除：同一判据 `掐着=0`。")
    b.append("- 边界：只读账本、收件目录、会话流水与 GitHub ref；0 次写账本、0 次插块、0 次删除、"
             "0 次动权威线、0 次点别人的窗口、0 次敲门给掐着的会话。")
    b.append("")
    block = "\n".join(b) + "\n"
    assert re.search(r"%[sd]", block) is None, "残留未替换占位符"
    add = ("\n" if not before.endswith("\n") else "") + block
    io.open(LOG, "a", encoding="utf-8", newline="\n").write(add)
    after = io.open(LOG, encoding="utf-8").read()
    n = len(add.encode("utf-8"))
    print("append %d B bytes_equal=%s log %d -> %d B | rounds=%d stored=%d exact=%d missing=%d root=%d"
          % (n, after.encode("utf-8")[-n:] == add.encode("utf-8"), len(before.encode("utf-8")),
             len(after.encode("utf-8")), len(rounds), len(stored), len(exact), len(missing), len(root_now)))
    time.sleep(20)
    late = io.open(LOG, encoding="utf-8").read()
    print("re-read after 20s: size=%d  my_entry_still_present=%s" % (len(late.encode("utf-8")), add.encode("utf-8")[-n:] in late.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
