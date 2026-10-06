# -*- coding: utf-8 -*-
"""recovery_note.py — 一条掐着的车道恢复后，把它该做的事一次算好打成一条令。

用法：python -X utf8 recovery_note.py <会话id前8位>
只读：跑写盘门（--text 模式，不改文件）、读本地 git 的权威线现尖、读它自己的流水最后一条自报。
生成的文本以 CLOSING_LINE.txt 的逐字尾行结尾，并断言：正文里不许残留未替换的 %s/%d。
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
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CAP = "daily usage limit for Chat"
DOOR = "claim_coordinate_check_r4e.py"
REPO = r"D:\moodle\CityNexus"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LOCAL_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
NAMES = {"1d64acf5": "S4（量具/污点尺）", "9759f1ac": "N2", "49fe0d7b": "N3", "3b65af59": "车道 map",
         "a68b0631": "车道 rel", "904a042d": "车道 Q", "bac10f40": "车道 AI", "e4f3490f": "车道 0370",
         "8e5245f0": "车道 0369", "be19052c": "车道 道tokens", "2d2d7428": "车道 qoder-0388/0389",
         "494abfd7": "号令者"}


def auth_tip():
    """先问远端（`git ls-remote`，绕掉本机那个没人听的代理），拿不到就退回本地 remote-tracking ref，并说明用的是哪一口。"""
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=",
                        "ls-remote", "origin", AUTH_REF],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    sha = (r.stdout or "").split()[:1]
    if r.returncode == 0 and sha:
        g = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%ad | %s", "--date=iso-local", sha[0]],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        meta = g.stdout.strip() or "(本地取不到这一枚的时间/标题)"
        return "%s  ← `git ls-remote origin %s`（远端现值）| %s" % (sha[0], AUTH_REF, meta)
    lr = subprocess.run(["git", "-C", REPO, "for-each-ref",
                         "--format=%(objectname) %(committerdate:iso8601) %(subject)", LOCAL_REF],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if lr.stdout.strip():
        return "%s  ← 本地 `git for-each-ref %s`（ls-remote 失败 rc=%d，所以这是**本地视图**，不是远端现值）" % (
            lr.stdout.strip(), LOCAL_REF, r.returncode)
    return "(两条路都没取到：ls-remote rc=%d，本地也没有 %s —— 这一格我不主张)" % (r.returncode, LOCAL_REF)



def door(path):
    r = subprocess.run([sys.executable, os.path.join(LC, DOOR), "--text", path, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    toks = []
    for m in re.finditer(r"^\s*line (\d+) \w+ (\w+) \| ([^|]*?)\|", out, re.M):
        toks.append("第%s行 %s=`%s`" % (m.group(1), m.group(2), m.group(3).strip()))
    n = len(re.findall(r"^\s*line \d+ \w+ \w+ \|", out, re.M))
    return ("GREEN" if r.returncode == 0 else "RED"), n, toks


def last_assistant(p):
    recs = [r for r in io.open(p, "rb")][-400:]
    for raw in reversed(recs):
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            continue
        m = d.get("message") or {}
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
             if isinstance(c, list) else (c or ""))
        if t.strip() and CAP not in t:
            return (d.get("timestamp") or "")[:19], t.replace(chr(10), " ")
    return "", ""


def main():
    key = (sys.argv[1] if len(sys.argv) > 1 else "").strip()[:8]
    if key not in NAMES:
        print("未知会话 id 前缀 %r；我知道这些：%s" % (key, " ".join(sorted(NAMES))))
        return 2
    nm = NAMES[key]
    g = glob.glob(os.path.join(BASE, key + "*.jsonl"))
    if not g:
        print("找不到会话文件")
        return 2
    p = g[0]
    ts, tail = last_assistant(p)
    stem = {"N2": "n2_", "S4（量具/污点尺）": "s4_", "N3": "n3_", "车道 map": "map_",
            "车道 rel": "rel_", "车道 0370": "qoder-0370_", "车道 0369": "qoder-0369_",
            "车道 qoder-0388/0389": "qoder-0388", "车道 AI": "qoder-0387"}.get(nm)
    mine = []
    if stem:
        for f in sorted(glob.glob(os.path.join(INBOX, stem + "*.md"))):
            v, n, toks = door(f)
            if v == "RED":
                mine.append((os.path.basename(f), n, toks, round((time.time() - os.stat(f).st_mtime) / 60.0, 0)))
    now = time.strftime("%H:%M")
    b = []
    b.append("【值守 %s → %s（会话 %s）· 你从日额度里回来了，先把这三件事读完再动手】" % (now, nm, key))
    b.append("1) 权威线现尖（读的是远端还是本地视图，我在同一行末尾标出来了）：")
    b.append("   `%s`" % auth_tip())
    if mine:
        b.append("2) 你留在 `_qoder_ledger_inbox/` 根上、被**写盘门**拒着的块（尺 = `%s`，就是 `ledger_insert_after.py:28` 那一枚）：" % DOOR)
        for f, n, toks, w in mine:
            b.append("   - `%s` 已等 %.0f 分钟，findings=%d：%s" % (f, w, n, "、".join(toks[:6]) or "见门输出"))
        b.append("   口径：**别删数字**，被点名的裸数字在同一行补可解析坐标（`path:line`、`field=value` 或完整 40 位 blob）。旧块改名留痕，新块另投 `<车道>_<HHMM>.md`，首行 `### `。")
    else:
        b.append("2) 我这一步没在你名下找到红块——**这是我认前缀认出来的，不是「不存在」**：我试的前缀是 %s，"
                 "根目录现在全部文件名是 %s。以你自己那一枚块的门输出为准。"
                 % (repr(stem) if stem else "(这条车道我没有可靠前缀，没猜)",
                    " ".join(sorted(os.path.basename(x) for x in glob.glob(os.path.join(INBOX, "*.md"))))[:900]))
    b.append("3) 你掐着之前的最后一句自报（UTC %s）：%s" % (ts or "—", ("「" + tail[:260] + "」") if tail else "(tail 里没读到有正文的自报)"))
    b.append("先按你原来那一单继续；不要接新的空单，除非号令者已经把它写进账本给你。")
    b.append("边界：不动权威线、不写账本、不碰别人的 worktree、不跑 `demo/reset`（03:55 那一发已把手机链广州场景抹平，`_preview.db` 的 `journeys` 只剩 1 行）。")
    b.append("")
    CL_PATH = os.path.join(LC, "CLOSING_LINE.txt")
    raw = io.open(CL_PATH, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", \
        "尾行口令文件不对（%d B）——不发" % len(raw)
    CL = raw.decode("utf-8").strip()
    txt = "\n".join(b) + "\n" + CL + "\n"
    assert txt.strip().split(chr(10))[-1] == CL, "尾行不是口令，不发"
    assert re.search(r"%[sd]", txt) is None, "残留占位符，不发"
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
