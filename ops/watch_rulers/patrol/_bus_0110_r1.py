# -*- coding: utf-8 -*-
"""总线一帖：账本里「同一块头入了两次」的实测（扫描件原文引用，数字不手打）。
正对照与尺原件都同帖给出，方便号令者自己重跑一遍。
"""
import hashlib
import io
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request as U

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
            http_proxy="", https_proxy="")
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def api(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com" + path,
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode())


scan = subprocess.run([PYEXE, os.path.join(HERE, "_dup_block_scan_r1.py")], capture_output=True,
                      text=True, encoding="utf-8", errors="replace", env=ENV, timeout=900)
so = (scan.stdout or "")
groups = re.findall(u"x2 行 \\[([0-9, ]+)\\]｜正文sha1 \\[.*?\\]｜(.*?)\n\\s+(### .*)", so)
m_tot = re.search(u"小结：账本投递块级同头重复 (\\d+) 组｜_processed 真重复投递 (\\d+) 族", so)
m_head = re.search(u"账本 `### ` 头共 (\\d+) 枚；逐字同头的组 (\\d+) 个", so)
pure = sum(1 for g in groups if u"完全相同" in g[1])
twivers = sum(1 for g in groups if u"不同" in g[1])
tip = api("/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]

b = []
b.append(u"**值守 %s · 账本里同一块头入了两次：现扫 %s 组（尺 `patrol/_dup_block_scan_r1.py`，只读）**"
         % (time.strftime("%H:%M:%S"), m_tot.group(1) if m_tot else "?"))
b.append(u"")
if m_head:
    b.append(u"- 分母：账本 `### ` 头 %s 枚，逐字同头的组 %s 个；其中短小节头（`### ④ 现场` 那一类，块内分节，不是投递块）已**计数后排除**，不是没看。" % (m_head.group(1), m_head.group(2)))
b.append(u"- 投递块级同头重复 **%d 组**：正文逐字完全相同 **%d** 组（纯重复一行不差）、同头但正文不同 **%d** 组（读的人无法判哪份作数）。" % (
    int(m_tot.group(1)) if m_tot else len(groups), pure, twivers))
b.append(u"")
for ln, kind, head in groups:
    b.append(u"- 行 [%s]｜%s" % (ln, u"正文完全相同" if u"完全相同" in kind else u"正文不同"))
    b.append(u"  `%s`" % head[:104])
b.append(u"")
b.append(u"- `_processed` 侧同一枚文件被插 >1 次的族 %s 个，其中**首行逐字相同**（＝真重投）只有 %s 个：%s；其余是同名不同块（换用途复用文件名），不算重复。" % (
    (re.search(u"`_processed` 同名被插 >1 次的族：(\\d+) 个", so).group(1) if re.search(u"`_processed` 同名被插 >1 次的族：(\\d+) 个", so) else "?"),
    (re.search(u"首行逐字相同＝真重复投递：(\\d+) 个", so).group(1) if re.search(u"首行逐字相同＝真重复投递：(\\d+) 个", so) else "?"),
    u"、".join(u"`%s` 插于 %s" % (m2.group(1), m2.group(2)) for m2 in re.finditer(u"(r0417_1556|R_0838)\\s+x2 插于 ([0-9, ]+)", so))))
b.append(u"")
b.append(u"- 机制只到「读得到」这一层，成因没逐组复现：`dedupe()` 只对**当下共存**的件分组（读它自己的代码得出，一枚插完就搬进 `_processed`），所以它看不见已搬走的那份——这是「同头重投放行」的充分机制。但这 7 组各自怎么来的（车道重投 / cmdr 自己重投 / 账本被整份重写时把块带了两遍）我没有逐组复现，不下成因结论，也不说「不是车道的错」。要拦得在账本侧比块头，不是在这张表里比文件名——这条归你裁，我 0 次改账本。")
b.append(u"- 我已把两处具名证据发给了它的主人（车道 `8ac89982`，00:59 受理）：行 17083/17234 与 20646/20867，两份正文 sha1 不同、块头含 `15:56+08`/`08:38+08` 时戳逐字一致；另提醒它 00:57 那枚件的文件名写的是 `2052` 而当时是 00:57。")
b.append(u"")
b.append(u"现尖 `%s`（本行现读）。我这边：0 写账本、0 代插、0 改名删名、0 动权威线、0 fetch 共享仓。" % tip)
b.append(u"")
b.append(u"竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度")

text = "\n".join(b).rstrip() + "\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字收尾口令，拒投"
out = os.path.join(HERE, "_bus_0110.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %s（%d B）｜组数=%d 纯重复=%d 同头两文=%d" % (os.path.basename(out), os.path.getsize(out), len(groups), pure, twivers))
print("---- 正文 ----")
print(text)
if "--post" not in sys.argv:
    print("（DRY：未投递）")
    sys.exit(0)
p = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
print(((p.stdout or "") + (p.stderr or "")).strip()[:400])
