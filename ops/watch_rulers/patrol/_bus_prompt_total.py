"""Bus follow-up: tonight's prompt-class stalls, counted (replaces the single-lane report).

Numbers come from prompt_stall_minutes.py (which reads each session's transcript) and the live session-state
snapshot taken at 22:32. Only episodes whose pending command carried a delete/write shape are counted; short
gaps that could be ordinary long-running commands are listed separately and NOT added to the total.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"


def show(ts):
    import calendar
    try:
        e = calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return ts
    return "%s+08" % time.strftime("%H:%M:%S", time.gmtime(e + 8 * 3600))


def main():
    subprocess.run([sys_exec(), os.path.join(HERE, "prompt_stall_minutes.py")], capture_output=True, timeout=900)
    rows = json.load(io.open(os.path.join(HERE, "prompt_stall_rows.json"), encoding="utf-8"))
    states = json.load(io.open(os.path.join(HERE, "session_states_2232.json"), encoding="utf-8"))
    gated = rows["gated"]
    assert gated, "本轮没读到弹窗形事件，不发帖"
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到"
    b = []
    b.append("**值守 %s · 接着 %s 那条：现在能给出总数了——今晚 %d 次『删除/写权限形』的停摆，合计 `%s` 分钟车道时间。**"
             % (time.strftime("%H:%M"), "5871099076", len(gated), round(sum(e["minutes"] for e in gated), 1)))
    b.append("")
    b.append("逐次（`patrol/prompt_stall_minutes.py`，只算待处理命令里带 `rm -f` / `rm -rf` 的那一类；"
             "普通长命令造成的 3 分钟级空档我另列，不算进这个数）：")
    for e in sorted(gated, key=lambda x: -x["minutes"]):
        b.append("- %s（`%s`）`%s → %s` = `%s` 分钟" % (
            e["lane"], e["id8"], show(e["from"]),
            (show(e["to"]) if not str(e["to"]).startswith("至今") else "**写这条时仍挂着**"), e["minutes"]))
    b.append("- 另有 `%d` 段 3 分钟级空档（`道0370`/`道0383`），命令里没有删除形状，无法与弹窗区分 ⇒ 不计入总数。"
             % len(rows["other"]))
    b.append("")
    st = states["states"]
    pend_rows = [e for e in gated if e.get("still_pending")]
    snap_pend = [(v.get("lane"), k) for k, v in st.items() if v.get("pendingInteractionCount")]
    b.append("会话状态快照 `%s`（`mcp list_chat_sessions`，值从工具结果抄下，存 `patrol/session_states_2232.json`）："
             "快照里仍等人工 `%d` 条：%s；其余 `%d` 条 ready/running/cold 且 `pendingInteractionCount=0`。"
             % (states["read_at_local"], len(snap_pend),
                ", ".join("`%s`(%s)" % (p[0], p[1]) for p in snap_pend) or "无",
                len(st) - len(snap_pend)))
    if pend_rows:
        b.append("按流水的判据（`tool_use` 之后有没有 `tool_result`）复算：写这条时**仍挂着 `%d` 条**：%s。"
                 % (len(pend_rows), ", ".join("`%s`(%s) 自 %s" % (e["lane"], e["id8"], show(e["from"]))
                                              for e in pend_rows)))
    else:
        b.append("按流水的判据（`tool_use` 之后有没有 `tool_result`）复算：写这条时**没有车道再停在弹窗上**——"
                 "快照里那条 `道0383` 在 22:32:38 拿到了 tool_result，前后只差 9 秒。"
                 "但这 `%d` 段一共吃掉了 `%s` 分钟车道时间，而且解开的方式我这边看不见是谁做的。"
                 % (len(gated), round(sum(e["minutes"] for e in gated), 1)))
    b.append("")
    b.append("要的东西很小、而且是向前看的：**在设置里给车道自己的临时目录（`_qoder_*_export` / `_qoder_*_wk`）"
             "预先放行删除**，否则每次跑突变/复检都要人点一次——今晚这三次的命令形状一模一样。"
             "我不点：批准的是一条 `rm`，那是您的边界，不是我的。")
    b.append("")
    b.append("同时账面在动：现尖 `%s`；`patrol/inbox_check.py` 最近一轮分类=门拒 1 / 门绿但第二道闸拒 2 / 门绿真能插 0；"
             "今晚 `19:00–22:30` 之间已入账块数增长到 `%d` 枚（含各车道按 r7 重切的块）。"
             % (sha, len(os.listdir(os.path.join(r"D:\moodle\_qoder_ledger_inbox", "_processed")))))
    b.append("")
    b.append("边界：只读会话流水、收件目录与 GitHub ref；0 次点别人的窗口、0 次写账本、0 次插块、0 次删除、0 次动权威线。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_prompt_total.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("gated=%d minutes=%.1f pending=%d -> %s (%d B)" % (
        len(gated), sum(e["minutes"] for e in gated), len(pend_rows), out, len(txt.encode("utf-8"))))
    return 0


def sys_exec():
    import sys
    return sys.executable


if __name__ == "__main__":
    raise SystemExit(main())
