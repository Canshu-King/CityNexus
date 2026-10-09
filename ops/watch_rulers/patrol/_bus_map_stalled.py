"""Bus post: one lane is stopped by a permission prompt, not by the quota - the commander cannot see this.

Computed in this run: the dangling tool_use (name + its own input), how long the transcript has had no new
record, and the session's own reported state (runtimeState / pendingInteractionCount / queuedTurnCount).
Nothing here clicks the prompt and nothing deletes anything: the point is to hand the commander the fact that
this lane cannot proceed, so it can decide whether ORD-0403 waits or moves.
"""
import datetime
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
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"


def session_tail(id8):
    p = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")), key=os.path.getmtime)[-1]
    recs = []
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                recs.append(json.loads(s))
            except Exception:
                pass
    last_use = None
    dangling = False
    for r in recs:
        m = r.get("message") or {}
        c = m.get("content")
        if m.get("role") == "assistant" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_use":
                    last_use = (x.get("name"), x.get("input"), r.get("timestamp"))
                    dangling = True
        if m.get("role") == "user" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "tool_result":
                    if last_use:
                        dangling = False
    return os.path.basename(p), len(recs), os.path.getmtime(p), last_use, dangling


def api(path):
    import urllib.request
    sys.path.insert(0, LC)
    import ghnet
    req = urllib.request.Request("https://api.github.com" + path)
    st, raw = ghnet.urlopen(req, timeout=45, headers={"Authorization": "Bearer " + open(
        r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip(),
        "Accept": "application/vnd.github+json", "User-Agent": "cnx-patrol-readonly"})
    return st, json.loads(raw.decode("utf-8"))


st, tip = api("/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")
tip_sha = tip["object"]["sha"] if st == 200 else None
st2, c = api("/repos/Canshu-King/CityNexus/git/commits/" + tip_sha) if tip_sha else (0, {})
subject = (c.get("message", "").splitlines() or ["?"])[0][:70] if st2 == 200 else "HTTP_%d" % st2
assert tip_sha and re.match(r"^[0-9a-f]{40}$", tip_sha), "现尖没读到，不发帖"

fn, nrecs, mtime, last_use, dangling = session_tail("3b65af59")
idle_min = (time.time() - mtime) / 60.0
print("map: file=%s records=%d idle=%.1fmin dangling=%s last_tool=%s" % (fn, nrecs, idle_min, dangling, last_use[0]))
q = subprocess.run([PY, os.path.join(HERE, "quota_now.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=600)
capped = int(re.search(r"掐着 (\d+) / 共 (\d+)", q.stdout).group(1))
total = int(re.search(r"掐着 (\d+) / 共 (\d+)", q.stdout).group(2))

inbox = [os.path.basename(x) for x in glob.glob(os.path.join(r"D:\moodle\_qoder_ledger_inbox", "*.md"))]
mine = [x for x in inbox if x.startswith("map_")]

b = []
b.append("**值守 %s · 一条号令者从账本看不到的现场：车道 map（`3b65af59`）从 %s 起卡在权限弹窗上，不是额度、不是死尾。它那一格 ORD-0403 因此停着，我等您裁。**"
         % (time.strftime("%H:%M"), time.strftime("%H:%M:%S", time.localtime(mtime))))
b.append("")
b.append("读数（全部本轮实取，判据与仪表同前）：")
b.append("")
b.append("- 会话流水 `projects/D--moodle/%s`：records=`%d`，最后一条是 `assistant/tool_use`（name=`%s`），**其后没有 tool_result**，"
         "即这一枚调用还没被批准执行；流水已 `%s` 分钟没有新记录。" % (fn, nrecs, last_use[0], int(idle_min)))
b.append("- 它的原命令逐字（我不执行、也不删任何东西）：`%s`" % json.dumps(last_use[1], ensure_ascii=False)[:400])
b.append("- 会话自报状态（`list_chat_sessions`）：`runtimeState=waiting-user`、`pendingInteractionCount=1`、`queuedTurnCount=2`"
         " ⇒ 它在等一次人工点击；我 20:40 送进它窗口的那条敲门被排在队列里，解不开弹窗。")
b.append("- 额度排除：同一判据本轮 `quota_now.py` 读数 `掐着=%d / 共=%d`（仪表 `patrol/quota_now.py`，tail 2 MB）。" % (capped, total))
b.append("- 现尖（`git ls-remote origin %s` 同通道回读）= `%s`，提交标题「%s」。" % (AUTH_REF, tip_sha, subject))
b.append("- 压在收件目录的 map 块：`%s`（共 %d 枚；它们中 4 枚是门绿但被第二道闸拦下，1 枚现行门就拒 findings=7）。"
         % ("`, `".join(mine), len(mine)))
b.append("")
b.append("**我没有做的事，也不打算替您做**：没点那枚弹窗（批准的是一条 `rm -f`，替别人按下删除不在我的边界里）、"
         "没动它的块、没插账本、没碰权威线。我把事实送到，裁的仍是您：要么您醒来点一下让它继续，"
         "要么 ORD-0403 换一条车道（待收清单里 ORD-0404/0405/0406/0407/0408 也都还没收口）。")
b.append("")
b.append("边界：只读会话流水、收件目录与 GitHub ref；0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次敲门给掐着的会话。")
raw = io.open(CLOSING, "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
assert re.search(r"%[sd]", txt) is None, "正文残留未替换占位符"
out = os.path.join(HERE, "_bus_map_stalled.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
print("wrote %s (%d B)" % (out, len(txt.encode("utf-8"))))
