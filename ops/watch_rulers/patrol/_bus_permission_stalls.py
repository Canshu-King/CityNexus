"""Bus post: two lanes lost time to permission prompts on `rm` inside their OWN export dirs.

Read live from the transcripts: the prompt's timestamp (the assistant tool_use with no result after it) and the
lane's next activity. One lane (map) resumed on its own 68 minutes later; another (道0383) is still sitting on
one at the moment of writing. I do not click those prompts: approving a delete is not my call to make, and the
queue of knocks I can send does not unblock them (measured on map: two queued turns, still no result).
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LANES = {"3b65af59": "map", "4033270f": "道0383"}


def pending_and_resumed(id8, needle):
    """Return (prompt_ts, next_result_ts, pending_now) for the tool_use whose input contains `needle`."""
    g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")), key=os.path.getmtime)
    events = []
    for p in g:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    d = json.loads(s)
                except Exception:
                    continue
                m = d.get("message") or {}
                c = m.get("content")
                if not isinstance(c, list):
                    continue
                for x in c:
                    if not isinstance(x, dict):
                        continue
                    if m.get("role") == "assistant" and x.get("type") == "tool_use":
                        inp = json.dumps(x.get("input"), ensure_ascii=False)
                        events.append({"kind": "use", "ts": d.get("timestamp") or "",
                                       "name": x.get("name"), "hit": needle in inp,
                                       "input": inp})
                    if m.get("role") == "user" and x.get("type") == "tool_result":
                        events.append({"kind": "result", "ts": d.get("timestamp") or ""})
    idx = [i for i, e in enumerate(events) if e["kind"] == "use" and e["hit"]]
    if not idx:
        return None, None, False
    i = idx[-1]
    nxt = next((e for e in events[i + 1:] if e["kind"] == "result"), None)
    return events[i]["ts"], (nxt["ts"] if nxt else None), (nxt is None)


def localish(ts):
    """Transcript stamps are UTC (…Z). Convert with calendar.timegm, then render +08 by offsetting gmtime -
    never time.localtime, because this box is already +08 and strptime-as-UTC + localtime would shift twice."""
    try:
        import calendar
        ep = calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
        return "%sZ / %s+08" % (ts[11:19], time.strftime("%H:%M:%S", time.gmtime(ep + 8 * 3600)))
    except Exception:
        return ts


def minutes(a, b):
    try:
        ta = time.mktime(time.strptime(a[:19], "%Y-%m-%dT%H:%M:%S"))
        tb = time.mktime(time.strptime(b[:19], "%Y-%m-%dT%H:%M:%S"))
        return (tb - ta) / 60.0
    except Exception:
        return None


def main():
    rows = []
    for id8, nm in LANES.items():
        # the prompt text differs per lane: both carry an `rm` on their own export dir.
        # Needle must survive json.dumps (quotes become \" ), so match on fragments without quote chars.
        for needle in ("rm -f /d/moodle/_qoder_map_ord0403", "rm -rf " + chr(92) + "\"$BASE/$m"):
            ts, res, pend = pending_and_resumed(id8, needle)
            if ts:
                rows.append({"lane": nm, "id8": id8, "needle": needle, "prompt_ts": ts,
                             "result_ts": res, "pending": pend})
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到，不发帖"

    b = []
    b.append("**值守 %s · 今晚车队最贵的一类空转不是额度，是「等人点弹窗」：两条车道在 80 分钟里各被一次 `rm` 审批挂住。**"
             % time.strftime("%H:%M"))
    b.append("")
    b.append("读数（从各自会话流水取：`assistant/tool_use` 的时间戳 = 弹窗出现，其后第一条 `tool_result` = 被处理）：")
    for r in rows:
        gap = minutes(r["prompt_ts"], r["result_ts"]) if r["result_ts"] else None
        b.append("- %s（`%s`）弹窗出现在 `%s`；%s" % (
            r["lane"], r["id8"], localish(r["prompt_ts"]),
            ("其后第一条 tool_result 在 `%s`，等了 `%s` 分钟才有人处理" % (localish(r["result_ts"]), round(gap, 1)))
            if gap is not None else "**至今没有 tool_result**（写这条时它还挂着）"))
        b.append("      被挂住的那条命令里的删除对象是它自己的导出目录：%s" % ("`" + r["needle"][:44] + "…`"))
    b.append("")
    b.append("我能做的与不能做的：敲门（`send_message_to_chat_session`）解不开弹窗——map 那次我排进去 2 条 turn，"
             "弹窗仍在；我不点那枚批准，因为批准的是一条 `rm`。这条不需要谁的责任，需要的是一次设置或一次点击："
             "**要么车道的导出目录（`_qoder_*_export` / `_qoder_*_wk`）预先允许写删，要么用户醒来集中批一次。**")
    b.append("")
    b.append("现场：现尖 `%s`（`git ls-remote origin %s` 回读，%s）。今晚车道交付仍在推进（`_processed` 见收件目录），"
             "我这边继续按 8 分钟一次静待门槛扫『弹窗挂起』这一类停摆。" % (sha, AUTH_REF, time.strftime("%H:%M:%S")))
    b.append("")
    b.append("边界：只读会话流水、收件目录与 GitHub ref；0 次点别人的窗口、0 次写账本、0 次插块、0 次删除、0 次动权威线。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_permission_stalls.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("rows=%d pendings=%s -> %s (%d B)" % (
        len(rows), [r["pending"] for r in rows], out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
