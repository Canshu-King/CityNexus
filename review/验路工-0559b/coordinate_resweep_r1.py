# -*- coding: utf-8 -*-
"""Replace the reconstructed commit string with the one ls-remote actually returned, re-sweep."""

import pathlib
import re
import subprocess

block = pathlib.Path("D:/moodle/_qoder_ledger_inbox") / ("验路工_" + "1847.md")
s = block.read_text(encoding="utf-8")

dead = "8f5c6bbc90c3b3cc2bd944036382bd94403638bb"
good = "8f5c6bbc90c3b3cc2bd9440363803e5465e76c1f"
old = ("- 枝 `refs/heads/review/验路工-0559b-r1`：先提交我那一枚测试件（8f5c6bbc90c3b3cc2bd944036382bd94403638bb "
       "形制的短尖是 8f5c6bbc90），再把现尖并进来（已发布枝不 rebase），合并后枝尖 "
       "766c544758d621bd421e2e0d3e8160d2d7fb7ad7；推后命令原样 "
       "`git ls-remote origin \"refs/heads/review/验路工-0559b-r1\"` 现读与本地 `git rev-parse HEAD` 逐字相同。")
new = ("- 枝 `refs/heads/review/验路工-0559b-r1`：先落我那一枚测试件那笔提交，短尖 8f5c6bbc90，"
       "全串 8f5c6bbc90c3b3cc2bd9440363803e5465e76c1f（那枚是 `git log -1 --format=%h` 与 push 时 "
       "`git ls-remote` 两处逐字对过的），再把现尖并进来（已发布枝不 rebase），合并后枝尖 "
       "766c544758d621bd421e2e0d3e8160d2d7fb7ad7；推后命令原样 "
       "`git ls-remote origin \"refs/heads/review/验路工-0559b-r1\"` 现读与本地 `git rev-parse HEAD` 逐字相同。"
       "顺带自报一形：这一枚我第一遍是按印象写的，写成另一串取不回的四十位，被本块末尾那道扫描抓出来才改对——"
       "扫描命令与判据见 `D:\\moodle\\_yanlugong_0559b_resweep_r1.py:12`。")
if s.count(old) != 1:
    raise SystemExit("SENTENCE_NOT_FOUND count=%d" % s.count(old))
s = s.replace(old, new)
block.write_text(s, encoding="utf-8", newline="\n")

text = block.read_text(encoding="utf-8")
hexes = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", text)))
dead_found = []
for h in hexes:
    r = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "cat-file", "-t", h],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        dead_found.append(h)
print("hexes=", len(hexes), "unresolvable=", dead_found)
print("old_string_still_present=", dead in text)
