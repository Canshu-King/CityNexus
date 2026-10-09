# -*- coding: utf-8 -*-
r"""车队名册自动发现 —— 不再手写车道清单。

为什么必须改：03:21 我用 list_chat_sessions 看了一眼真名册，发现号令者半夜又开了**四条新车道**
（`a17ae861` 工单状态板 / `8e094dec` Q64 前端扫描 / `d9e2c9ae` Hermes 测试移植 / `1d64acf5` S4-ast-taint），
而我所有仪表里写死的还是原来那六条 ⇒ **有活的车道根本不在我的读数里**。写死名册的仪表会随队伍扩大而失效。

判据：`C:\Users\仓鼠王\.qoder\projects\D--moodle\*.jsonl` 里 cwd 属于本项目的会话，
排除我自己（值守 42d1a6fa），按"距上次落盘分钟数"排序输出。标题不在 JSONL 里，
所以标题由 `--titles <list_chat_sessions 的 json>` 可选喂进来。

用法：python fleet_state.py            # 只看 id + idle
      python fleet_state.py --narr    # 附带每条最后一条 assistant 文本尾巴（慢）
"""
import glob
import io
import json
import os
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ME = "42d1a6fa"
PROJECT_CWD = "d:\\moodle"


def sessions(lookback_min=360.0):
    """**不要**用记录里的 cwd 过滤：我第一版这么干，结果把 D/E/F/HJ-P3 和号令者半夜新开的四条工具车道
    全漏了（它们靠前那几条记录里没有 cwd 字段），而目录名 `projects\D--moodle` 本身就是项目范围。
    改成：目录内全部会话 + 只看"最近有没有落盘"，按 mtime 窗口筛。"""
    out = []
    now = time.time()
    for p in glob.glob(os.path.join(BASE, "*.jsonl")):
        sid = os.path.basename(p).split("-")[0]
        if sid.startswith(ME):
            continue
        try:
            st = os.stat(p)
        except Exception:
            continue
        if (now - st.st_mtime) / 60.0 > lookback_min:
            continue
        out.append((sid, p, st.st_size, st.st_mtime))
    return out


def tail_assistant(p, limit=200):
    try:
        with io.open(p, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 900000))
            chunk = f.read()
    except Exception:
        return ""
    last = ""
    for line in chunk.split(b"\n"):
        line = line.strip()
        if not line or b'"assistant"' not in line:
            continue
        try:
            r = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        m = r.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        parts = []
        if isinstance(c, str):
            parts = [c]
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    parts.append(b.get("text", ""))
        t = " ".join(x for x in parts if x).strip()
        if t:
            last = t
    return last.replace("\r\n", " / ").replace("\n", " / ")[:limit]


def main():
    narr = "--narr" in sys.argv
    titles = {}
    for i, a in enumerate(sys.argv):
        if a == "--titles" and i + 1 < len(sys.argv):
            try:
                d = json.load(io.open(sys.argv[i + 1], encoding="utf-8"))
                titles = {s["sessionId"][:8]: s["title"] for s in d.get("sessions", [])}
            except Exception as e:
                print("titles load failed:", e)
    now = time.time()
    rows = []
    for sid, p, sz, mt in sessions():
        idle = (now - mt) / 60.0
        rows.append((idle, sid, sz, mt))
    rows.sort()
    print("[%s] 近 6 小时内有落盘迹象的本项目会话：%d 条（不含值守自己）" % (time.strftime("%H:%M:%S"), len(rows)))
    for idle, sid, sz, mt in rows:
        line = "  %-9s idle=%6.1fm  %8.1f MB  %s" % (sid, idle, sz / 1048576.0,
                                                     titles.get(sid, ""))
        if idle > 20 and narr:
            cand = glob.glob(os.path.join(BASE, sid + "*"))
            if cand:
                line += "\n      尾句: " + tail_assistant(max(cand, key=os.path.getmtime))
        print(line)
    stale = [r for r in rows if r[0] > 20]
    print("idle>20min: %d/%d" % (len(stale), len(rows)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
