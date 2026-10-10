# -*- coding: utf-8 -*-
"""总线一帖：把 map(3b65af59) 卡在的那半句裁语量成现尖上的代码事实（只读，不替裁）。

现场来自车道流水尾条（12:31 读）：它说绑 maplibre `click` 会让 `qoder-ord0417-tap-names-the-stop.spec.ts:520`
那组从 26 枚控件读成 31 枚（run `ord0453reg1`，8 条红），它不替裁决偷改守卫。
本帖全部读数都对**权威尖**取（`git show <tip>:<path>`，不碰工作树、不碰任何人的枝），
并把「8 条」这一枚数从文件里重算出来，而不是抄她说的那个数。
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
SPEC = "frontend/e2e/qoder-ord0417-tap-names-the-stop.spec.ts"
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


rc, tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
TIP = tip.split()[0] if rc == 0 and tip.strip() else None
assert TIP and len(TIP) == 40, "取不到权威尖，拒投"

def head_of(br):
    """从服务器现读一枚枝尖（ls-remote 只读，不 fetch、不动本地 ref）。"""
    r, o = git("ls-remote", "origin", "refs/heads/" + br)
    return o.split()[0] if r == 0 and o.strip() else "NOT_FOUND_ON_ORIGIN"

PREV = "4e0ad72c90ff1b9bb76718d3ee883dc860f7ab72"
rc, o = git("rev-list", "--count", "%s..%s" % (PREV, TIP))
AHEAD = int(o.strip()) if rc == 0 and o.strip().isdigit() else -1
rc, _o = git("merge-base", "--is-ancestor", PREV, TIP)
assert rc == 0, "旧尖不是新尖的祖先，那句「前进 N 笔」就不能写"

BR_A = "review/map-ord0453-list-third-state"
BR_B = "review/map-ordA-basemap-attribution-visible"
HEAD_A, HEAD_B = head_of(BR_A), head_of(BR_B)

rc, src = git("show", "%s:%s" % (TIP, SPEC))
assert rc == 0 and src, "现尖上没有这枚文件，拒投"
rc, blob = git("rev-parse", "%s:%s" % (TIP, SPEC))
BLOB = blob.strip()
assert re.fullmatch(r"[0-9a-f]{40}", BLOB or ""), "blob 不是 40 位，拒投"
lines = src.split("\n")


def at(pat, want=1):
    hits = [i + 1 for i, l in enumerate(lines) if re.search(pat, l)]
    assert len(hits) >= want, "锚 %s 只找到 %d 处" % (pat, len(hits))
    return hits


n_shapes = at(r"^const SHAPES: Array<\[number, number\]>")
shapes = re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", lines[n_shapes[0] - 1])
n_arms = at(r"^const ARMS = \[")
arms = re.findall(r'\{ locale: "([a-z-]+)", lead: "([^"]+)" \}', src)
n_census = at(r"^async function controlCensus")
census_sel = re.search(r"const sel =\s*\n\s*(\".*?\;)", src)
sel_line = None
for i in range(n_census[0] - 1, min(n_census[0] + 6, len(lines))):
    if "button, a[href]" in lines[i] or lines[i].strip().startswith('"button'):
        sel_line = (i + 1, lines[i].strip())
n_loop = at(r"^for \(const \[w, h\] of SHAPES\)")
n_idle = [i + 1 for i, l in enumerate(lines) if "const idleControls = await controlCensus(page)" in l]
n_live = [i + 1 for i, l in enumerate(lines) if "const liveControls = await controlCensus(page)" in l]
n_assert = at(r"^\s*\)\.toBe\(idleControls\.length\);")
msg_line = [i + 1 for i, l in enumerate(lines) if "the band must not add a control" in l]

combos = len(shapes) * len(arms)
# 门最后一次跳动：从 _processed 的文件名戳现取（mtime 限定今天），不写死
import glob
_st = []
for f in glob.glob(r"D:\moodle\_qoder_ledger_inbox\_processed\*.md.inserted_*"):
    hm = re.search(r"inserted_(\d{6})$", f)
    if hm and time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))) == time.strftime("%Y-%m-%d"):
        _st.append((hm.group(1), os.path.basename(f).split(".md")[0], os.path.getmtime(f)))
# 入账先后只能按戳本身排（stamp 文件的 mtime 是被移动那枚块的写入时刻，12:36 实测会把 120130 排在 121445 之后）
_st.sort(key=lambda x: x[0])
last_stamp, last_name = (_st[-1][0], _st[-1][1]) if _st else ("?", "?")
last_hm = "%s:%s:%s" % (last_stamp[:2], last_stamp[2:4], last_stamp[4:6]) if last_stamp != "?" else "?"
inbox_now = [f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md")]
try:
    _lt = time.strptime(time.strftime("%Y-%m-%d ") + last_stamp, "%Y-%m-%d %H%M%S")
    age_min = (time.time() - time.mktime(_lt)) / 60.0
except Exception:
    age_min = -1


body = u"""**值守一件事实（12:3x）· map 卡在的那半句「点图即展开」我量成了代码面读数 · 裁语归你，我不选**

对象是权威尖 `%s`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，12:3x 现读），
下面每一行都是从这枚尖的文件正文里取的（`git show <尖>:<路径>`，我不碰工作树、不碰任何人的枝）。
被测文件：`%s`，blob `%s`（可 `git cat-file -t` 回验）。
另：尖从我 12:22 那帖的 `4e0ad72c90ff1b9bb76718d3ee883dc860f7ab72` 又进到本帖现读的这枚 —— `git rev-list --count` 得 **%d 笔**，那枚旧尖 `merge-base --is-ancestor` 判为**新尖的祖先**。下面所有行号都对**新尖**取（不是 12:22 那枚），所以别拿上一帖的尖值来对行号。

一、卡住的原文（车道 3b65af59 流水尾条，12:31 我读到的逐字）：
> ORD-0453 的「点图即展开」——绑 maplibre `click` 会让 `qoder-ord0417-tap-names-the-stop.spec.ts:520` 那组从 26 枚控件读成 31 枚（run `ord0453reg1`，8 条红），我不替裁决偷改它。

二、`:520` 那组在尖上到底是什么（我现取的行号）：
- `%s:%d` 是 `for (const [w, h] of SHAPES)` 那一圈几何循环的开头；她引的 `:520` 就在这圈里面（循环头 `:%d`，圈里第一次普查在 `:%s`）。
- `%s:%d` 取点击**前**的控件普查 `idleControls`；`%d` 取点击**后**的 `liveControls`。
- `%s:%d` 的断言是 `toBe(idleControls.length)`，判语原文是「the band must not add a control -- `${idleControls.length} -> ${liveControls.length}`」。
⇒ **「26 读成 31」不是绝对值断言，是增量断言**：那一格要求「点下去之后可达控件数不许变」。普查的取法在 `%s:%d`，选择器是 `%s`，只算有尺寸且中心命中自己的那些元素。

三、「8 条红」这枚数我从文件重算，不抄她的：`SHAPES`（`%s:%d`）实有 %d 形 `%s`，`ARMS`（`%s:%d`）实有 %d 臂 `%s` ⇒ 那圈循环 = %d × %d = **%d 格**。
⇒ 如果绑 `click` 真让普查加控件，红的不是某几格，是**整圈 A5 全红**。这一点让裁语的代价当场可算：要么那一格守卫的适用范围变窄，要么「点图即展开」不新增可达控件。

四、三条 literal 后果我只列不选（选哪条是你的裁量，我不开单也不改守卫）：
- 甲：「点图即展开」由 band 上那枚按钮承担（不在地图本体绑 click）⇒ A5 那圈不动，0 新控件。
- 乙：仍绑地图 click ⇒ 这 %d 格必然全红，改守卫口径是**动了 ORD-0417 那批交付的判据**，按规矩得你具名放行，车道不能自己改断言换绿。
- 丙：那半句继续挂「未裁」，车道这侧 0 产品字节（`%s` 的枝尖我从 origin 现读为 `%s`；她说这枝对现尖 `merge-tree` 回 rc=0、只带门文件那 20 行 —— 这两句是她的自报，我没替她复跑）。

五、她另一枚也在等同样的落地跳：`%s` 头现读 `%s`；她说尖上没有那枝带的那枚 e2e 文件（同名文件计数 0）⇒ 没落。这条我也没替她复跑，只把她的自报和门的位置摆在一起：**收件口现在积 %d 枚（`%s` 等），门最后一次跳是文件名戳 `%s`（距本帖 %s 分钟），所以那两枝等的都是你那一趟 `--apply` 加一次落地。**

%s
""" % (
    TIP, SPEC, BLOB, AHEAD,
    SPEC.split("/")[-1], n_loop[0], n_idle[0] - n_loop[0] if n_idle else "?", str(n_idle[0]),
    SPEC.split("/")[-1], n_idle[0], n_live[0],
    SPEC.split("/")[-1], n_assert[0],
    SPEC.split("/")[-1], n_census[0], (sel_line[1] if sel_line else "（没抓到选择器行）"),
    SPEC.split("/")[-1], n_shapes[0], len(shapes), " ".join("%sx%s" % x for x in shapes),
    SPEC.split("/")[-1], n_arms[0], len(arms), " ".join(a[0] for a in arms),
    len(shapes), len(arms), combos,
    combos,
    BR_A, HEAD_A,
    BR_B, HEAD_B,
    len(inbox_now), last_name, last_hm, "%.0f" % age_min,
    CLOSING,
)
assert body.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"

out = os.path.join(HERE, "_bus_1235_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body + "\n")
print("bytes=%d tip=%s blob=%s combos=%d inbox=%d last=%s@%s" % (
    len(body.encode("utf-8")), TIP[:12], BLOB[:12], combos, len(inbox_now), last_name, last_hm))
if "--dry" in sys.argv:
    print(body)
else:
    p = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=300)
    print((p.stdout or "") + (p.stderr or ""))
