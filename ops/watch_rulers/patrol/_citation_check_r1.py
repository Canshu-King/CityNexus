# -*- coding: utf-8 -*-
"""交件前回读坐标：把块里每一枚 `path:line` 打开，印出那一行的前若干字，判「在不在范围」也判「说不说得上去」。

为什么单独成一枚脚本（03:05）：这一班我用同一段内联检查跑了三次，每次都要重打一遍 bases；
而交接稿里已经写了「用 `_citation_check_r1.py`」——引用一个不存在的脚本，正是我这两天在账本里犯的错。
所以把它落成文件，下一班一条命令能用。

用法：python _citation_check_r1.py <块或草稿的绝对路径> [--need-support 关键字,…]
  --need-support 形如 `_unclaimed_0255.txt:61=无人接的单`：除了行存在，还要求那一行含该子串，缺就算坏。

边界：只读。找不到文件/行号越界=坏；给了支撑词而行里没有=坏（这条专治「行号对、说的话不对」）。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASES = [HERE,
         r"D:\moodle\_qoder_ledger_inbox",
         r"D:\moodle\_qoder_ledger_inbox\_processed",
         r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks",
         r"D:\moodle"]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CIT = re.compile(r"`([^`\s]+?):(\d+)`")


def resolve(name):
    for b in BASES:
        p = os.path.join(b, name)
        if os.path.isfile(p):
            return p
    return None


def main():
    if len(sys.argv) < 2:
        print("用法：python _citation_check_r1.py <块路径> [--need-support f:1=词,f:2=词]")
        return 2
    doc = sys.argv[1]
    txt = io.open(doc, encoding="utf-8", errors="replace").read()
    need = {}
    rest = sys.argv[2:]
    # 两种形制都收：`--need-support 文件:行=子串[,文件:行=子串…]`（空格分开）或 `--need-support=文件:行=子串`。
    # 子串里允许出现 `=`（例如「枝名=否」），所以只按第一个 `=` 切成「位置=内容」。
    chunks = []
    for a in rest:
        if a.startswith("--need-support="):
            chunks.append(a.split("=", 1)[1])
        elif a == "--need-support":
            chunks.append("")
        elif "--need-support" in a and "=" in a:
            chunks.append(a.split("--need-support", 1)[1].lstrip("= ").strip())
        elif ":" in a and "=" in a:
            chunks.append(a)
    for tail in chunks:
        for part in re.findall(r"([^,]+?:\d+=[^,]+)", tail):
            loc, kw = part.split("=", 1)
            name_, ln_ = loc.rsplit(":", 1)
            need[(name_.strip(), int(ln_))] = kw.strip()
    if rest and not need:
        print("警告：给了 --need-support 但一条支撑要求都没解析出来 ⇒ 这一趟只验行号，别当验过支撑")
    cits = [(n, int(l)) for n, l in CIT.findall(txt)]
    bad = 0
    for name, ln in cits:
        f = resolve(name)
        if not f:
            print("坏  %-46s :%-5d 找不到文件" % (name, ln))
            bad += 1
            continue
        ls = io.open(f, encoding="utf-8", errors="replace").read().splitlines()
        if ln > len(ls):
            print("坏  %-46s :%-5d 行号越界（共 %d 行）" % (name, ln, len(ls)))
            bad += 1
            continue
        line = ls[ln - 1]
        kw = need.get((name, ln))
        if kw and kw not in line:
            print("坏  %-46s :%-5d 行在但没有「%s」：%s" % (name, ln, kw, line[:44]))
            bad += 1
            continue
        print("好  %-46s :%-5d %s" % (name, ln, line[:52]))
    print("坐标 %d 枚，坏 %d" % (len(cits), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
