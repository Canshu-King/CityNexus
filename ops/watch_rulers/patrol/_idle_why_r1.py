# -*- coding: utf-8 -*-
"""「谁闲着、为什么」一屏（只读，只取每枚流水尾部 220 KB）。

为什么单开：零点后额度不再是约束（0 闸上），但车道跑完一轮就停——它们不是没油，是**没有下一步可接**。
要判断「该不该推、推什么」，得把三件事并排看：
  1) 会话尾部状态：在写 / 闸上 / 静默（判据＝最后一条角色记录是不是额度字样；工具块算在跑）；
  2) 它最近一枚交付块的下落：还在收件口根目录（等门）/ 已进 _processed（入账时间）/ 没有；
  3) 它最后一次正文里有没有「等裁/等授权/等落地」这类等待词（有＝它停在别人的手上，不该推它自己开工）。
输出只是事实，不替你派单：能推的只有「它名下有未接的单」或「它的块被拒且原因具名」这一类，
其余（等号令者裁）推了也只是把消息堆在窗口里。
"""
import io
import json
import os
import re
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
WIN = 220 * 1024
NICKS = {
    "a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
    "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
    "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
    "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道465",
    "e766b154": "新车道472", "494abfd7": "号令者B", "6efab655": "CMDR-A",
}
WAIT_WORDS = (u"等裁", u"等授权", u"等一句", u"等你", u"在你回之前", u"等号令者", u"待裁", u"等落地", u"等门")
CAP = "daily usage limit"


def tail(path):
    sz = os.path.getsize(path)
    fh = io.open(path, "rb")
    if sz > WIN:
        fh.seek(sz - WIN)
        fh.readline()
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    return blob


def classify(blob):
    rows = []
    for line in blob.split(chr(10)):
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    last_kind = "?"
    last_ts = None
    last_text = ""
    for o in rows:
        if o.get("type") not in ("user", "assistant"):
            continue
        c = (o.get("message") or {}).get("content")
        ks = "+".join(sorted({x.get("type", "") for x in c if isinstance(x, dict)})) if isinstance(c, list) else "str"
        if ks:
            last_kind = ks
        last_ts = o.get("timestamp")
        if o.get("type") == "assistant" and isinstance(c, list):
            t = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            if t.strip():
                last_text = t.strip()
    capped = CAP in last_text or CAP in json.dumps(rows[-1] if rows else {}, ensure_ascii=False)
    waiting = [w for w in WAIT_WORDS if w in last_text]
    return last_kind, last_ts, last_text, waiting, capped


def main():
    now = time.time()
    files = {}
    for f in os.listdir(BASE):
        if f.endswith(".jsonl"):
            files[f[:8]] = os.path.join(BASE, f)
    root = [f for f in os.listdir(INBOX) if f.endswith(".md")]
    proc = [f for f in os.listdir(PROC) if ".inserted_" in f]
    print("=== 谁闲着、为什么 %s ===（根目录 %d 枚在等｜00:00 后入账 %d 枚）"
          % (time.strftime("%H:%M:%S"), len(root),
             sum(1 for f in proc if os.path.getmtime(os.path.join(PROC, f)) >= time.mktime((2026, 9, 30, 0, 0, 0, 0, 0, -1)))))
    print("%-10s %-8s %-6s %-9s %-14s %s" % ("花名", "id", "状态", "末写(分)", "它的块", "正文里的等待词/末条摘要"))
    rows = []
    for sid8, nick in NICKS.items():
        p = files.get(sid8)
        if not p:
            continue
        blob = tail(p)
        kind, ts, text, waiting, capped = classify(blob)
        age = (now - os.path.getmtime(p)) / 60.0
        if capped:
            st = u"闸上"
        elif age < 8:
            st = u"在写"
        else:
            st = u"静默"
        mine = [f for f in root if f.startswith(sid8) or f.startswith(nick)]
        # 块归属：收件口/_processed 里带这个会话 id 前 8 位或惯用前缀的件
        pref = sid8
        inroot = [f for f in root if f.startswith(pref) or (nick + "_") == f[:len(nick) + 1]]
        inproc = sorted([f for f in proc if f.startswith(pref)], key=lambda x: os.path.getmtime(os.path.join(PROC, x)))
        blk = (u"根目录等 %d" % len(inroot)) if inroot else (u"已入账 %s" % inproc[-1].split(".inserted_")[1][:4] if inproc else u"无件")
        note = (u"等词:" + u"/".join(waiting)) if waiting else (text[-60:].replace(chr(10), " ") if text else kind)
        rows.append((nick, sid8, st, age, blk, kind, note))
    order = {u"闸上": 0, u"静默": 1, u"在写": 2}
    for r in sorted(rows, key=lambda x: (order[x[2]], -x[3])):
        print("%-10s %-8s %-6s %-9s %-14s %-10s %s" % (r[0], r[1], r[2], "%.1f" % r[3], r[4], r[6], r[5][:14]))
    sil = [r for r in rows if r[2] == u"静默"]
    print()
    print("小结：在写 %d｜静默 %d｜闸上 %d。" % (sum(1 for r in rows if r[2] == u"在写"), len(sil),
                                        sum(1 for r in rows if r[2] == u"闸上")))
    print("静默里『正文带等待词』的（＝停在别人手上，推它没用）：%s"
          % (u"、".join(r[0] for r in sil if r[6].startswith(u"等词")) or "无"))
    print("静默里『块还在根目录等门』的（＝等的是门那一跳，不是它自己）：%s"
          % (u"、".join(r[0] for r in sil if r[4].startswith(u"根目录")) or "无"))
    print("边界：只读流水尾部、收件口与 _processed 的 stat/mtime；0 写账本、0 派单、0 敲门、0 改任何人的文件。")


main()
