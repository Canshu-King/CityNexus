# -*- coding: utf-8 -*-
"""总线一帖：把最老的那格待裁（ORD-0458 甲/乙/丙，从 09-29 12:27 挂到现在）量成尖上的代码事实。

dt（be19052c）的原话是「工单写'接在已有的 pretrip 面板上，不新建对象'，三条路请挑，我不擅自选」。
这一件只把**每条路会撞上什么**测出来，不推荐任何一条——裁权在号令者。
全部读数对**权威尖**取（`git ls-remote` 现读那枚，再 `git show <尖>:<路径>`；不碰工作树、不碰任何人的枝、0 写）。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
REPO = r"D:\moodle\CityNexus"
BRANCH = "mirror/integration-frontend-apple-pass1"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def git(*a):
    p = subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=180)
    return p.returncode, (p.stdout or "")


rc, out = git("ls-remote", "origin", "refs/heads/" + BRANCH)
TIP = out.split()[0] if rc == 0 and out.strip() else ""
assert len(TIP) == 40, "取不到权威尖，拒投"


def show(path):
    rc, s = git("show", "%s:%s" % (TIP, path))
    return s if rc == 0 else ""


LIB = "frontend/src/lib/pretripChecklist.ts"
PANEL = "frontend/src/features/checklist/PretripChecklistPanel.tsx"
SPEC = "frontend/e2e/qoder-0384"  # placeholder replaced below
rc, listing = git("ls-tree", "-r", "--name-only", TIP)
files = [f for f in listing.split("\n") if "pretrip" in f.lower() or "checklist" in f.lower()]
SPEC = next((f for f in files if f.endswith(".spec.ts")), "")
lib_src = show(LIB)
spec_src = show(SPEC)
contract = show("contracts/openapi.yaml")

# 从 lib 的头注释里逐字取那三句设计断言（带行号），不转述
lib_lines = lib_src.split("\n")
quotes = []
for i, l in enumerate(lib_lines, 1):
    if re.search(r"stores nothing|no .mark done.|only if the contract names|an item may appear only if", l):
        quotes.append((i, l.strip()))
assert quotes, "lib 头注释没读到设计断言，拒投（不凭记忆写它的口径）"

spec_head = [(i, l.strip()) for i, l in enumerate(spec_src.split("\n"), 1)
             if re.search(r"not a checkbox|projection of the field", l)][:2]

n_contract = len(re.findall(r"checklist", contract, re.I))
rc_s, schema_out = git("grep", "-c", "-i", "checklist", TIP, "--", "backend/app")
n_schema = u"命令 `git grep -c -i checklist <尖> -- backend/app` 回 rc=%s、输出 %s 行%s" % (
    rc_s, len([l for l in schema_out.split("\n") if l.strip()]),
    u"（内容：" + schema_out.strip().replace("\n", "；")[:180] + u"）" if schema_out.strip() else u"，即这个字面在 backend/app 里没有行可打印——我不把它写成「没有该能力」，只写「词面没有」")
anchors = re.findall(r"contracts/openapi\.yaml:(\d+)", lib_src)
cblob = (re.search(r"contract blob ([0-9a-f]{40})", lib_src) or [None, "?"])[1]

# dt 的原话（含丙的全文）从账本现读，带行号
led = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
dt_line = dt_ask = u""
for i, l in enumerate(led):
    if l.startswith(u"### 车道 dt") and "ORD-0458 前提冲突请裁" in l:
        dt_line = str(i + 1)
        w = [x.strip() for x in led[i:i + 70] if (u"甲" in x or u"乙" in x or u"丙" in x or u"请裁" in x)]
        hm2 = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", l)
        waited = ((time.time() - time.mktime(time.strptime(hm2.group(1), "%Y-%m-%d %H:%M"))) / 3600.0) if hm2 else -1
        dt_ask = u" / ".join(w)[:1200]
        assert dt_ask, "dt 那格的甲乙丙原文没读到，拒投"
        break
assert dt_line, "账本里没读到 dt 那格请裁的原块，拒投"

S = {
    "when": time.strftime("%H:%M:%S"), "tip": TIP, "n_files": str(len(files)),
    "files": u"\n".join(u"  - `%s`" % f for f in files[:8]),
    "libq": u"\n".join(u"  %s: %s" % (i, q[:168]) for i, q in quotes[:4]),
    "specq": u"\n".join(u"  %s: %s" % (i, q[:150]) for i, q in spec_head) or u"  （没命中那句）",
    "n_contract": str(n_contract), "anchors": " ".join(":%s" % a for a in anchors) or "?",
    "cblob": cblob, "schema_grep": (n_schema.strip() or "0 处命中（backend/app 里没有这个字面）"),
    "dt_line": dt_line, "dt_ask": dt_ask, "waited": ("%.1f" % waited) if waited > 0 else "?",
}

TPL = u"""**值守 {when} · 最老的那格待裁我量成代码事实了：ORD-0458 甲/乙/丙（挂 {dt_line} 那块，从 09-29 12:27 到现在）· 我只摆每条路撞上什么，不替你选**

对象是权威尖 `{tip}`（`git ls-remote origin refs/heads/{branch}` 现读；下面每行都出自 `git show <尖>:<路径>`，不碰工作树、不碰任何人的枝、0 写）。

一、工单说的那枚「已有的 pretrip 面板」在尖上确实存在，全套就 {n_files} 枚文件：
{files}

二、这枚面板**自带一条已经落地的设计断言**（`frontend/src/lib/pretripChecklist.ts` 头注释，逐字）：
{libq}
它的 e2e 也这么写（`{spec_file}` 头）：
{specq}
⇒ 也就是说：屏上「勾选」这件事现在**不是**一个控件；清单只有两条，且每条都必须能被契约点名（锚 {anchors}，钉在契约 blob `{cblob}`）。

三、契约面实测：`contracts/openapi.yaml` 里字面 "checklist" 现共 **{n_contract} 处**；`backend/app` 的 grep：{schema_grep}。
⇒ 三条路各撞上的东西，按现测：
- **甲**（只视图态、面板明写"本次不保存"）：0 新对象 0 写路由，与二里那条断言不冲突；但如果"勾选"要做成可点控件，就直接撞 spec 那句「not a checkbox」——**改 spec 那句就是改 ORD-0384 已交付的判据**，那需要你具名放行，车道不能自己改断言换绿。
- **乙**（真持久化勾选与备注）：契约面现在这个字面是 {n_contract} 处，要新增字段与写路由、同笔进 `contracts/openapi.yaml` 与 `frontend/src/generated/api.ts`，并且二的断言要整个翻面（它明写 stores nothing and writes nothing）。
- **丙**（挂到已有对象）：dt 原句在下面逐字给，要挂哪一枚已有对象由你定；我不猜归属。

四、dt 那格请裁的原文（账本第 {dt_line} 行；甲/乙/丙逐行拼回，**丙那句在账本里跨了行、拼接后仍短一截**，全文按行号自取）：
> {dt_ask}

五、这条为什么值得先裁：dt 名下 ORD-0435 已落地、ORD-0452 我已 11:54 量成代码面事实（总线 `5903722590`），剩这一格把她整条钉住 **{waited} 小时**（块头自报 09-29 12:27 到现在，我按那时刻算的）。我这边不催、也不替她改口径；裁语归你。

""".format(branch=BRANCH, spec_file=SPEC, **S) + u"""六、可重跑（只读）：
- `git -C D:/moodle/CityNexus ls-remote origin refs/heads/""" + BRANCH + u"""`
- `git -C D:/moodle/CityNexus show """ + TIP + u""":frontend/src/lib/pretripChecklist.ts`
- `git -C D:/moodle/CityNexus show """ + TIP + u""":contracts/openapi.yaml | grep -ic checklist`

"""

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1745_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d tip=%s files=%s contract_hits=%s" % (len(text.encode("utf-8")), TIP[:12], S["n_files"], S["n_contract"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
