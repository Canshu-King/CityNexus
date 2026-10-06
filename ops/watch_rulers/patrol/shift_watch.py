# -*- coding: utf-8 -*-
"""shift_watch.py — 这一班的循环仪表：一次跑完「谁活着 + 新到的收件块过不过门 + 新车道最后说了什么」。

只读：跑写盘门（--text 模式）、读会话流水尾部、读本地 git。不发消息、不插账本、不改任何文件。
状态存在 shift_watch_state.json 里（只存我自己看过的文件名与时间，便于「新增」判定）。
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
sys.path.insert(0, HERE)
import quota_now  # noqa: E402

INBOX = r"D:\moodle\_qoder_ledger_inbox"
DOOR = os.path.join(LC, "claim_coordinate_check_r4e.py")
STATE = os.path.join(HERE, "shift_watch_state.json")
CAP = "daily usage limit for Chat"
NEW_LANE = "4033270f"
KEY_PREFIXES = {"0383": "4033270f 车道（ORD-0383 切片 1）"}


def load():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {"seen": {}}


def save(st):
    io.open(STATE, "w", encoding="utf-8", newline="\n").write(json.dumps(st, ensure_ascii=False, indent=1))


def door(path):
    r = subprocess.run([sys.executable, DOOR, "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    toks = []
    for m in re.finditer(r"^\s*line (\d+) \w+ (\w+) \| ([^|]*?)\|", out, re.M):
        toks.append("第%s行 %s=`%s`" % (m.group(1), m.group(2), m.group(3).strip()))
    n = len(re.findall(r"^\s*line \d+ \w+ \w+ \|", out, re.M))
    return ("GREEN" if r.returncode == 0 else "RED"), n, toks


def lane_tail():
    g = glob.glob(os.path.join(quota_now.BASE, NEW_LANE + "*.jsonl"))
    if not g:
        return "(找不到新车道的流水)", None
    size = os.path.getsize(g[0])
    with io.open(g[0], "rb") as f:
        f.seek(max(0, size - 600000))
        raw = f.read().decode("utf-8", "replace")
    last = ""
    for line in raw.split(chr(10)):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        t = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text")) if isinstance(c, list) else (c or "")
        if t.strip() and CAP not in t:
            last = "%s: %s" % ((d.get("timestamp") or "")[:19], t.replace(chr(10), " ")[:300])
    return last, size


def main():
    st = load()
    if "--seed" in sys.argv:
        for f in glob.glob(os.path.join(INBOX, "*.md")):
            st["seen"].setdefault(os.path.basename(f), {"at": time.strftime("%H:%M:%S"), "verdict": "SEEDED", "findings": None})
        save(st)
        print("已把现有 %d 枚块标成 SEEDED（不当作新增）" % len(st["seen"]))
        return
    dead = []
    live = []
    for key, nm in quota_now.NAMES.items():
        g = glob.glob(os.path.join(quota_now.BASE, key + "*.jsonl"))
        if not g:
            continue
        lr, ca, caps = quota_now.scan(g[0])
        idle = (time.time() - os.stat(g[0]).st_mtime) / 60.0
        (dead if (ca and ca >= lr) else live).append((nm, key, idle, lr))
    print("[%s] 掐着 %d / 共 %d   可动: %s" % (time.strftime("%H:%M:%S"), len(dead), len(dead) + len(live),
                                            ", ".join("%s(idle %.1f)" % (nm, idle) for nm, key, idle, lr in sorted(live, key=lambda x: x[2]))))
    tail, size = lane_tail()
    print("  新车道 %s 流水 %s B，最后一个想法：%s" % (NEW_LANE, size, tail or "(tail 里没有)"))
    files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    new = [f for f in files if os.path.basename(f) not in st["seen"]]
    print("  收件目录 %d 枚，本轮新增 %d 枚" % (len(files), len(new)))
    for f in new:
        v, n, toks = door(f)
        st["seen"][os.path.basename(f)] = {"at": time.strftime("%H:%M:%S"), "verdict": v, "findings": n}
        print("    NEW %s %d B → 门 %s / findings=%d %s"
              % (os.path.basename(f), os.path.getsize(f), v, n, "、".join(toks[:5])))
        if v == "RED":
            print("      ⇒ 若这是 %s 的块，把上面这几枚 token 直接送回去让它补坐标（别删数字）"
                  % ", ".join(KEY_PREFIXES.values()))
    save(st)


main()
