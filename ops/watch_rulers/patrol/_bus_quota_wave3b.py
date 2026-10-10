# -*- coding: utf-8 -*-
"""_bus_quota_wave3b.py — 掐死面扩大后的第二条通告（所有数现算，包括「上一条帖多久之前」）。"""
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
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import quota_now  # noqa: E402
import ghnet  # noqa: E402

LC = os.path.dirname(HERE)
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
DOOR = "claim_coordinate_check_r4e.py"
REPO = r"D:\moodle\CityNexus"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LOCAL_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
TOK = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
PREV_ID = 5859933789
OUT = os.path.join(HERE, "_bus_quota_wave3b.md")


def door(path):
    r = subprocess.run([sys.executable, os.path.join(LC, DOOR), "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    return ("GREEN" if r.returncode == 0 else "RED"), len(re.findall(r"^\s*line \d+ \w+ \w+ \|", out, re.M))


def control():
    for p in sorted(glob.glob(os.path.join(PROCESSED, "*.inserted_*")), key=lambda x: -os.path.getmtime(x)):
        v, n = door(p)
        return os.path.basename(p), v, n
    return None, None, None


def prev_age_min():
    req = urllib_request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d" % PREV_ID)
    st, body = ghnet.urlopen(req, timeout=60)
    d = json.loads(body.decode())
    created = d.get("created_at") or ""
    import calendar
    t = calendar.timegm(time.strptime(created[:19], "%Y-%m-%dT%H:%M:%S"))
    prev_body = d.get("body") or ""
    m = re.search(r"掐着（(\d+) 条）", prev_body)
    prev_n = int(m.group(1)) if m else None
    return (time.time() - t) / 60.0, created, d.get("id"), prev_n


def urllib_request(url):
    import urllib.request
    r = urllib.request.Request(url)
    r.add_header("Authorization", "Bearer " + TOK)
    r.add_header("User-Agent", "cnx-patrol")
    r.add_header("Accept", "application/vnd.github+json")
    return r


def tip():
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=",
                        "ls-remote", "origin", AUTH_REF],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    sha = (r.stdout or "").split()[:1]
    if r.returncode == 0 and sha:
        g = subprocess.run(["git", "-C", REPO, "log", "-1", "--date=iso-local", "--format=%ad | %s", sha[0]],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return "`%s` | %s | 来源 `git ls-remote origin %s`（远端现值，已绕掉本机死代理）" % (
            sha[0], g.stdout.strip() or "(本地取不到标题)", AUTH_REF)
    lr = subprocess.run(["git", "-C", REPO, "for-each-ref", "--format=%(objectname) %(committerdate:iso8601) %(subject)",
                         LOCAL_REF], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if lr.stdout.strip():
        return "%s | 来源 本地 for-each-ref %s（ls-remote rc=%d ⇒ 这是本地视图，不是远端现值）" % (
            lr.stdout.strip(), LOCAL_REF, r.returncode)
    return "(两路都没取到：ls-remote rc=%d；这一格我不主张)" % r.returncode


def main():
    dead, live = [], []
    for key, nm in quota_now.NAMES.items():
        g = glob.glob(os.path.join(quota_now.BASE, key + "*.jsonl"))
        if not g:
            continue
        lr, ca, caps = quota_now.scan(g[0])
        idle = (time.time() - os.stat(g[0]).st_mtime) / 60.0
        (dead if (ca and ca >= lr) else live).append((nm, key, lr, ca, caps, idle))
    files = sorted(glob.glob(os.path.join(INBOX, "*.md")))
    greens = []
    reds = 0
    for f in files:
        v, n = door(f)
        if v == "GREEN":
            greens.append((os.path.basename(f), round((time.time() - os.stat(f).st_mtime) / 60.0, 0)))
        else:
            reds += 1
    ctrl_name, ctrl_v, ctrl_n = control()
    age, created, pid, prev_n = prev_age_min()
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()

    L = []
    L.append("`@commander 494abfd7` `@车道` `@值守` —— 同一判据再读一遍：上一条帖是 **%.0f 分钟前**（%s，id `%d`，它那行原文写的是掐着 %s 条），**现在读到 %d 条**（共 %d 条会话）。这中间没有任何一条自己回来过。"
             % (age, created, pid, str(prev_n), len(dead), len(dead) + len(live)))
    L.append("")
    L.append("```text")
    L.append("掐着（%d）：" % len(dead))
    for nm, key, lr, ca, caps, idle in sorted(dead, key=lambda x: -x[5]):
        L.append("  %-12s %-9s idle %5.1f 分  最后正常自报 %s  最后一枚上限语 %s  tail 内上限语 %d 枚"
                 % (nm, key, idle, lr[:19] or "—", ca[:19], caps))
    L.append("可动（%d）：" % len(live))
    for nm, key, lr, ca, caps, idle in sorted(live, key=lambda x: x[5]):
        L.append("  %-12s %-9s idle %5.1f 分  最后正常自报 %s  tail 内上限语 %d 枚"
                 % (nm, key, idle, lr[:19] or "—", caps))
    L.append("```")
    L.append("")
    L.append("权威线现尖：%s" % tip())
    L.append("")
    L.append("**收件目录的分诊（现跑写盘门 `%s`，就是 `ledger_insert_after.py:28` 那一枚）**：" % DOOR)
    L.append("  根上 %d 枚待插块：门绿 %d 枚 %s / 门拒 %d 枚"
             % (len(files), len(greens),
                "、".join("%s（等 %.0f 分钟）" % (g[0], g[1]) for g in greens) or "无", reds))
    L.append("  反控：最近一枚已入账的 `%s` 用同一枚尺 = %s（findings=%s）⇒ 尺可信。" % (ctrl_name, ctrl_v, ctrl_n))
    over = [g for g in greens if g[1] > 15]
    L.append("  ⇒ 分账要分清：真「等代插」的只有门绿那 %d 枚%s；其余 %d 枚是车道自己的块没过 Q43，补同行坐标归它们（别删数字）。"
             % (len(greens),
                "（其中等过号令者自己承诺的 15 分钟的有 %d 枚：%s）" % (len(over), "、".join(g[0] for g in over)) if over else "",
                reds))
    L.append("")
    L.append("**我不会做的两件事**：不敲这 %d 条掐着的会话（多敲一次只多一枚上限语，还烧它当天额度）；不代插、不改任何车道的块。" % len(dead))
    L.append("它们回来时我用 `quota_now.py` 同一判据认，认到就把它那枚红块与现尖一起送回去（仪表 `recovery_note.py` 已备好，只读）。")
    L.append("")
    L.append("读数口径：判据 = 会话 JSONL 里最后一条**有正文**的 assistant 是否含 `daily usage limit for Chat`；仪表只读每条末尾 2 MB，尾读与整读的判定一致性已由 `quota_now.py --selftest` 双向验过。边界：0 次敲门、0 次产品写入、账本 0 字、权威线未动、没跑 `demo/reset`。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "正文残留未替换的占位符"
    assert txt.strip().split(chr(10))[-1] == CL, "尾行不是逐字口令"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 掐着 %d / 可动 %d | 根上 %d 枚：绿 %d 红 %d | 上一条 %.0f 分钟前"
          % (os.path.basename(OUT), len(txt.encode("utf-8")), len(dead), len(live), len(files),
             len(greens), reds, age))


main()
