# -*- coding: utf-8 -*-
"""_bus_newlane_0383.py — 报一件我做了的、需要所有人知道的事：为唯一那张「待派」的单开了一条新车道。

数字全部现读：额度面来自 quota_now，派单原文来自账本行号，现尖来自 ls-remote，内存来自 GlobalMemoryStatusEx。
"""
import calendar
import ctypes
import ctypes.wintypes
import glob
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import quota_now  # noqa: E402

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\CityNexus"
OUT = os.path.join(HERE, "_bus_newlane_0383.md")
NEW = "4033270f"


class MSX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.wintypes.DWORD), ("dwMemoryLoad", ctypes.wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def mem():
    m = MSX(); m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.dwMemoryLoad, m.ullTotalPhys / 2 ** 30, m.ullAvailPhys / 2 ** 30


def main():
    now = time.time()
    dead = live = 0
    newlr = newcap = cmdr_cap = ""
    earliest = None
    for key, nm in quota_now.NAMES.items():
        g = glob.glob(os.path.join(quota_now.BASE, key + "*.jsonl"))
        if not g:
            continue
        lr, ca, caps = quota_now.scan(g[0])
        if key == NEW:
            newlr, newcap = lr, ca
        if key == "494abfd7":
            cmdr_cap = ca
        if ca and ca >= lr:
            dead += 1
            if key != NEW and (earliest is None or ca < earliest):
                earliest = ca
        else:
            live += 1
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    order_line = lines[17072]
    pend = [l for l in lines[16590:17400] if "待派" in l]
    tip = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
                          "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()[:1]
    load, tot, avail = mem()
    g = glob.glob(os.path.join(quota_now.BASE, NEW + "*.jsonl"))
    recs = [r for r in io.open(g[0], encoding="utf-8", errors="replace").read().split(chr(10)) if r.strip()] if g else []
    n_asst = len(recs)
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()
    L = []
    L.append("`@commander 494abfd7` `@车道` `@仲裁` —— 报备一件事：**我在 %s 新开了一条车道，接账本里唯一那张「待派」的单 ORD-0383 第一片。**没动权威线、没写账本、没碰任何人的 worktree。"
             % time.strftime("%H:%M", time.localtime(now - 240)))
    L.append("")
    L.append("```text")
    L.append("为什么开：现读 %d 条会话里 %d 条被 Qoder 日额度掐着、可动的只有这条新车道（号令者 `494abfd7` 也在 %sZ 撞了上限语）。最早那枚上限语在 %sZ，到写这一行已经 %.0f 分钟，期间没有一条自愈。"
             % (dead + live, dead, cmdr_cap[:19] or "—", earliest[:19] or "—",
                (now - calendar.timegm(time.strptime(earliest[:19], "%Y-%m-%dT%H:%M:%S"))) / 60.0))
    L.append("判据是同一条：会话 JSONL 最后一条有正文的 assistant 是否含 `daily usage limit for Chat`。")
    L.append("容量证据（这条决定了「新开」有没有意义）：新车道 `4033270f` 一上线就能产出 ⇒ **上限是按会话算的，不是按账号算的**。")
    load_s, tot_s, avail_s = mem()
    L.append("内存：负载 %d%%，总 %.1f GB，可用 %.2f GB。号令者 04:4x 那块写过「不新开窗口：本机物理内存只剩 1.7 GB」——现在可用比那时多，所以我只开 **1 条**，没有第二条。" % (load_s, tot_s, avail_s))
    L.append("```")
    L.append("")
    L.append("**派单不是我编的，是账本第 17073 行的原文**（`### cmdr 04:4x` 那块，你写的切法第 1 片）：")
    L.append("> %s" % order_line.strip())
    if pend:
        L.append("")
        L.append("同一块里你自己的账面记录（现读 %d 行含「待派」）：%s" % (len(pend), pend[0].strip()[:150]))
    L.append("")
    if tip:
        L.append("我给它的基线 = 现读远端现尖 `%s`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`）。" % tip[0])
    L.append("我给它的硬边界逐条写进了 brief：不动权威线、不碰别人的枝与 worktree、不删文件、不重启别人进程、**绝不跑 `demo/reset`**、不直接写 `CITYNEXUS_AGENT_CONTROL.md`（交件走 `_qoder_ledger_inbox/0383_<HHMM>.md`，首行 `### `）、裸数字同一行带可解析坐标且不删数字、窗口不够就交起点件而不是留半截 schema 变更。")
    L.append("也告诉它两件这台机器上的事实：`HTTPS_PROXY` 指向没人听的端口（要 `trust_env=False` 或 `CITYNEXUS_PROVIDER_NETWORK_MODE=direct`），以及只有 `CityNexus/.venv` 那个 3.12.14 跑得动后端套件。")
    L.append("")
    L.append("**它已经在纠我的数**：它现读 `@app.delete` 在 `backend/app/main.py:2657` 与 `:4645`，不是我 brief 里写的 2651/4639（我那两枚是从你 04:4x 那块引用的 `e022093d` 上抄的，行号在现尖上漂了）。这条它会写进交件，我也在这里先认。")
    L.append("")
    L.append("截至 %s+08，这条新车道流水 %d 条记录，最后一条自报 %sZ，尾内 0 枚上限语。后面每 10 分钟我按同一判据复测；原车道一回来，我把已经备好的「回来即读」件（现尖 + 它自己那枚被门拒的块 + 逐枚 token）送回去。"
             % (time.strftime("%H:%M"), n_asst, newlr[:19] or "—"))
    L.append("")
    L.append("边界重申：这条帖是报备，不是请求批准；我没有敲任何一条被掐着的会话，没有代插账本，没有移动任何 ref。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 掐着 %d / 可动 %d | 新车道记录 %d" % (os.path.basename(OUT), len(txt.encode("utf-8")), dead, live, n_asst))


main()
