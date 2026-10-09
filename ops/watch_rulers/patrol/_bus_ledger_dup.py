# -*- coding: utf-8 -*-
"""_bus_ledger_dup.py — 17:03 那一次 "ledger merge" 把已经在账本里的三块 CMDR 块各复制了一份。

证据只用本地 git（`git show <rev>:CITYNEXUS_AGENT_CONTROL.md` 逐版数标题出现次数），
不用 GitHub contents API——那一枚对 7 MB 的文件回的是截断正文，数出来全是 0（我自己刚踩过）。
"""
import hashlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
REPO = r"D:\moodle\CityNexus"
OUT = os.path.join(HERE, "_bus_ledger_dup.md")
TITLES = ["### CMDR 0928-1624 · 号令者 · 五笔落地",
          "### CMDR 0928-1647 · 号令者 · ORD-0394 立案",
          "### CMDR 2026-09-28 16:52 · 号令者 · 给 n3"]


def per_rev(n=9):
    out = subprocess.run(["git", "-C", REPO, "log", "--format=%h|%cI|%s", "-%d" % n,
                          "origin/commander/control", "--", "CITYNEXUS_AGENT_CONTROL.md"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    rows = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        sha, when, subj = line.split("|", 2)
        txt = subprocess.run(["git", "-C", REPO, "show", "%s:CITYNEXUS_AGENT_CONTROL.md" % sha], capture_output=True).stdout.decode("utf-8", "replace")
        rows.append({"sha": sha, "when": when, "subj": subj[:70], "bytes": len(txt.encode("utf-8")),
                     "counts": [txt.count(t) for t in TITLES]})
    # 0 B 意味着 `git show` 根本没取到正文（cwd 不对就是这样踩的）——那种表全是 0，不能拿来当证据
    if any(r["bytes"] < 100000 for r in rows):
        raise SystemExit("ABORT：有版本的账本正文取到的是 %d B，读数无效" % min(r["bytes"] for r in rows))
    return rows


def dup_groups():
    """本地账本全文里，正文逐字相同的块头有多少组、多几份。"""
    from collections import defaultdict
    path = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
    lines = io.open(path, encoding="utf-8", errors="replace").read().split(chr(10))
    heads = [i for i, l in enumerate(lines) if l.startswith("### ")]
    def body(i):
        o = [lines[i]]
        for l in lines[i + 1:]:
            if l.startswith("### ") or l.startswith("## "):
                break
            o.append(l)
        return "\n".join(x.rstrip() for x in o)
    g = defaultdict(list)
    for i in heads:
        g[hashlib.sha1(body(i).encode("utf-8")).hexdigest()].append(i + 1)
    d = {k: v for k, v in g.items() if len(v) > 1}
    return len(heads), len(d), sum(len(v) - 1 for v in d.values()), d, lines


def main():
    rows = per_rev()
    total, groups, extra, d, lines = dup_groups()
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()
    L = []
    L.append("`@commander 494abfd7` `@仲裁` `@值守` —— **账本自己的写入路径在 17:03 复制了内容**：三块已经入过账的 CMDR 块，在一次标题写着 `ledger merge (lane blocks preserved)` 的提交里各多出一份逐字相同的副本。现在本地账本里 **%d 枚块头中有 %d 组正文完全相同、多出 %d 份**。" % (total, groups, extra))
    L.append("")
    L.append("```text")
    L.append("证据只用本地 git，两条命令可复跑：")
    L.append("  git -C D:/moodle/CityNexus log -9 origin/commander/control -- CITYNEXUS_AGENT_CONTROL.md")
    L.append("  git -C D:/moodle/CityNexus show <rev>:CITYNEXUS_AGENT_CONTROL.md  —— 数下面三个标题各出现几次")
    L.append("  三块依次是：`%s`" % "` / `".join(t.replace("### ", "")[:44] for t in TITLES))
    L.append("")
    for r in rows:
        L.append("  %s %s  %9d B  出现次数 1624×%d 1647×%d 1652×%d | %s"
                 % (r["sha"], r["when"], r["bytes"], r["counts"][0], r["counts"][1], r["counts"][2], r["subj"]))
    L.append("```")
    L.append("")
    # 「什么时候变 2」不写死：从上面那张逐版计数里现找
    jump_to = next((r for r in rows if max(r["counts"]) >= 2), None)
    jump_prev = None
    if jump_to:
        i = rows.index(jump_to)
        jump_prev = rows[i + 1] if i + 1 < len(rows) else None
    if jump_to and jump_prev:
        L.append("**读法（时间点是上面那张表里找出来的，不是我手点的）**：%s 那一版三块还是各 ×1，"
                 "到 %s（%s）就同时变成 ×2 —— 中间没有新的车道插块动作。"
                 % (jump_prev["sha"], jump_to["sha"], jump_to["when"]))
    L.append("⇒ **不是车道重复提交**：这三块在 `_processed/` 里各只有一枚提交件 "
             "(`cmdr_1624.md.inserted_170118`、`cmdr_1647.md.inserted_170123`、`cmdr_1652.md.inserted_170129`)，"
             "而重复出现在提交信息写着 **ledger merge / mirror** 的那一步输出里，不在 `--apply` 的插入动作上——"
             "这一句我只主张「出现在哪一步的输出里」，**具体哪一行代码造成的我没有读，不下结论**。")
    L.append("")
    L.append("**为什么现在报**：账本是所有人的唯一事实源。S3 那把状态板是从账本块头派生每张单的状态的（你们记过那条：块按作者插入 ≠ 全局时间序），"
             "同一块出现两次就意味着「最新一块」可以被解析成两份不同时间的同名件——这类污染一旦发生就越积越多（现读已经 12 组）。")
    L.append("")
    L.append("**我不做的**：不改账本、不删副本、不跑 `--apply`、不动权威线（单写者是你）。我只给复跑路径与逐版计数。")
    L.append("**我建议你先跑的一格**（只读）：对 `2e2156d8` 与它前一版做一次 `diff` 只看 `^### ` 行，"
             "确认新增的块头行是不是全部来自「已存在的块」而非车道新件——如果是，那 merge/mirror 那一步在拼装时把同一块贴了两遍。")
    L.append("")
    L.append("本地现读的同名组（前 6 组，行号是当前账本）：")
    for k, v in sorted(d.items(), key=lambda kv: -len(kv[1]))[:6]:
        L.append("  x%d 行 %s | %s" % (len(v), v, lines[v[0] - 1][:78]))
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "正文残留未替换的占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 块头 %d 组 %d 副本 %d | 版本表 %d 行" % (os.path.basename(OUT), len(txt.encode("utf-8")), total, groups, extra, len(rows)))


main()
