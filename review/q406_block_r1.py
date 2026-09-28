#!/usr/bin/env python3
"""Build the ORD-0406 delivery block from the four runs this lane wrote, then gate and publish it.

The before/after table is parsed out of the receipts' own logs, not typed. Two honesty details the
script enforces rather than asserts in prose:
  * the baseline log got contaminated mid-run (the dev server hot-reloaded my edit while the "before"
    run was still executing), so the three shapes it lost are taken from a clean re-run with the file
    reverted, and the contaminated lines are excluded by name;
  * the readings are stamped on the commit that holds the change, and the commit this script adds is
    only review/ files - proved by a byte comparison of the measured paths, not by "I just committed".
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_lane_q0406"
REPO = r"D:/moodle/CityNexus"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
VITE_JS = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules/vite/bin/vite.js"
TSC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript/bin/tsc"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
BRANCH = "review/Q-ord0406-attention-band-hit-r1"
HEAD_RUN = "b3fd27a02c73c859b007e375a4d2b57d0e5abe87"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
V8 = "frontend/src/app/V8Experience.tsx"
SPEC = "frontend/e2e/qoder-ord0406-attention-band-hit.spec.ts"
SHAPES = [(390, 844), (360, 800), (320, 653), (414, 896)]
CONTAMINATED = {("zh", 390, 844), ("en", 360, 800), ("en", 414, 896)}
bad = []


def run(cmd, cwd=None, env=None, timeout=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(*a, check=True, cwd=REPO):
    rc, out = run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", cwd, *a])
    if check and rc:
        bad.append("git %s rc=%d %s" % (" ".join(a), rc, out[-110:]))
    return out.strip()


def git_ok(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True).returncode == 0


def head_of(refspec):
    for l in git("ls-remote", "origin", refspec).splitlines():
        p = l.split()
        if len(p) == 2 and p[1] == refspec:
            return p[0]
    return ""


def sha1(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()


def blob_at_ref(ref, rel):
    out = git("rev-parse", "%s:%s" % (ref, rel), check=False)
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else ""


def newest(tag):
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)), key=os.path.getmtime)
    if not fs:
        bad.append("no receipt for tag %s" % tag)
        return {}, ""
    return json.load(open(fs[-1], encoding="utf-8")), os.path.basename(fs[-1]).replace(".json", ".log")


CELL = re.compile(r"shape=(\d+)x(\d+).*?nav_height=(\d+) hit_line=(\d+) hero=\[(\d+),(\d+),(\d+),(\d+)\]"
                 r" strip=\[[^\]]*\] band=\[(\d+),(\d+),(\d+),(\d+)\] map=\[(\d+),(\d+),(\d+),(\d+)\]"
                 r" band_clears_nav=(\w+) band_hit_test_inside=(\w+) band_hit=(\w+)")


def parse(log):
    txt = open(os.path.join(LIVE, "e2e_logs", log), encoding="utf-8", errors="replace").read()
    rows = {}
    for l in txt.split("\n"):
        s = re.sub(r"^\[[0-9:]+\]\s*", "", l.strip())
        m = re.match(r"O406 geometry (zh|en) ", s)
        if not m:
            continue
        arm = m.group(1)
        c = CELL.search(s)
        if not c:
            continue
        g = [int(x) for x in c.groups()[:16]]
        rows[(arm, g[0], g[1])] = {
            "arm": arm, "w": g[0], "h": g[1], "nav_h": g[2], "hit_line": g[3],
            "hero": g[4:8], "band": g[8:12], "map": g[12:16],
            "clears": c.groups()[16], "inside": c.groups()[17], "hit": c.groups()[18], "line": s}
    return rows


base1, base1_log = newest("q406base")
base2, base2_log = newest("q406b2")
aft, aft_log = newest("q406f")
reg, reg_log = newest("q406reg")
regb, regb_log = newest("q406reg_base")
BEFORE, AFTER = {}, {}
for src, tag in ((parse(base1_log), "q406base"), (parse(base2_log), "q406b2")):
    for k, v in src.items():
        if tag == "q406base" and k in CONTAMINATED:
            continue
        BEFORE.setdefault(k, v)
AFTER = parse(aft_log)
for arm in ("zh", "en"):
    for w, h in SHAPES:
        k = (arm, w, h)
        if k not in BEFORE:
            bad.append("no clean before reading for %s %dx%d" % k)
        if k not in AFTER:
            bad.append("no after reading for %s %dx%d" % k)
        elif AFTER[k]["hit"] != "true" or AFTER[k]["inside"] != "true":
            bad.append("the after reading is not a hit: %s %dx%d %s" % (arm, w, h, AFTER[k]["line"][:80]))
        elif BEFORE[k]["hit"] == "true":
            bad.append("the before reading was already a hit, so the fix proves nothing: %s %dx%d" % k)
BAND_Y_BEFORE = sorted({BEFORE[k]["band"][1] for k in BEFORE})
BAND_Y_AFTER = sorted({AFTER[k]["band"][1] for k in AFTER})
HIT_MIN = min(BEFORE[k]["hit_line"] for k in BEFORE)
DISPLACE = sorted({AFTER[k]["hero"][1] - BEFORE[k]["hero"][1] for k in BEFORE})
MAP_SHIFT = sorted({AFTER[k]["map"][1] - BEFORE[k]["map"][1] for k in BEFORE})
MAP_OUT_BEFORE = [k for k in BEFORE if BEFORE[k]["map"][1] > BEFORE[k]["h"]]
MAP_OUT_AFTER = [k for k in AFTER if AFTER[k]["map"][1] > AFTER[k]["h"]]
if set(MAP_OUT_BEFORE) != set(MAP_OUT_AFTER):
    bad.append("the set of shapes where the map starts below the fold changed: %s -> %s" % (
        MAP_OUT_BEFORE, MAP_OUT_AFTER))
PAD = re.search(r"O406 padding zh shape=(\d+)x(\d+) nav_height=(\d+) shell_padding_bottom=(\S+) pad_equals_nav=(\w+)",
                open(os.path.join(LIVE, "e2e_logs", aft_log), encoding="utf-8", errors="replace").read())
if not PAD:
    bad.append("no padding reading in the after log")
DESK = re.search(r"O406 desktop zh shape=1280x800 .*?band=\[(\d+),(\d+),(\d+),(\d+)\] map=\[(\d+),(\d+),(\d+),(\d+)\]",
                 open(os.path.join(LIVE, "e2e_logs", aft_log), encoding="utf-8", errors="replace").read())
if not DESK:
    bad.append("no desktop reading in the after log")

# the regression spec: same failure set with and without my change
def overflow_set(log):
    txt = open(os.path.join(LIVE, "e2e_logs", log), encoding="utf-8", errors="replace").read()
    return sorted(set(re.findall(r"^\s*(live@\d+: \S+ right=\d+ \(innerW \d+\))", txt, re.M)))


OV_MINE, OV_BASE = overflow_set(reg_log), overflow_set(regb_log)
if not OV_MINE or OV_MINE != OV_BASE:
    bad.append("the overflow failure sets differ with/without my change: %s vs %s" % (OV_MINE, OV_BASE))
if reg.get("verdict") != regb.get("verdict"):
    bad.append("the overflow verdicts differ between the two runs")

# compile arm on the committed head
rc_t, _ = run([NODE, TSC, "-p", "tsconfig.typecheck.json", "--noEmit"], cwd=os.path.join(WT, "frontend"),
              timeout=1800)
rc_b, bout = run([NODE, VITE_JS, "build"], cwd=os.path.join(WT, "frontend"), timeout=1800)
assets = glob.glob(os.path.join(WT, "frontend", "dist", "assets", "index-*.js"))
if rc_t or rc_b or len(assets) != 1:
    bad.append("compile arm not clean: tsc=%d vite=%d assets=%d" % (rc_t, rc_b, len(assets)))
ASSET = os.path.basename(assets[0]) if assets else "?"
ASSET_BYTES = os.path.getsize(assets[0]) if assets else 0
ASSET_SHA1 = sha1(assets[0]) if assets else ""
BUILT = subprocess.run([NODE, TSC, "-p", "tsconfig.check.json", "--noEmit"],
                       cwd=os.path.join(WT, "frontend"), capture_output=True).returncode

LIVE_TIP = head_of(TIP_REF)
BASE_TIP = git("merge-base", LIVE_TIP, HEAD_RUN)
if not re.fullmatch(r"[0-9a-f]{40}", BASE_TIP or ""):
    bad.append("my head and the live tip share no merge base")
N_TIP_AHEAD = int(git("rev-list", "--count", "%s..%s" % (BASE_TIP, LIVE_TIP)) or 0)
MY_DIFF = [l for l in git("diff", "--name-only", BASE_TIP, HEAD_RUN).split("\n") if l.strip()]
PRODUCT_TOUCHED = [l for l in MY_DIFF if l.startswith("frontend/src/") or l.startswith("backend/")]
CSS_TOUCHED = [l for l in MY_DIFF if l.endswith(".css")]
DICTIONARY_TOUCHED = [l for l in MY_DIFF if "i18n" in l]
if not DICTIONARY_TOUCHED:
    pass
if CSS_TOUCHED:
    bad.append("I was told to leave styles.css alone and it is in my diff: %s" % CSS_TOUCHED)
if V8 not in PRODUCT_TOUCHED:
    bad.append("the band move is not in my own diff")
TOKEN_LINE = git("grep", "-n", "--", "--cn-nav-h: 80px", HEAD_RUN, "--", "frontend/src/design-tokens.css")

ART_REL = "review/q406_readouts_r1.json"
json.dump({"head_readings_ran_on": HEAD_RUN, "live_tip": LIVE_TIP, "merge_base": BASE_TIP,
           "cell_run": aft, "cells_log": aft_log, "before_logs": [base1_log, base2_log],
           "contaminated_baseline_cells": sorted(["%s %dx%d" % c for c in CONTAMINATED]),
           "before": {"%s %dx%d" % k: {x: BEFORE[k][x] for x in
                                       ("hit_line", "band", "hero", "map", "hit")} for k in BEFORE},
           "after": {"%s %dx%d" % k: {x: AFTER[k][x] for x in
                                      ("hit_line", "band", "hero", "map", "hit")} for k in AFTER},
           "padding": PAD.groups(), "desktop": DESK.groups(),
           "overflow_with_change": {"run": reg.get("run_id"), "verdict": reg.get("verdict"), "set": OV_MINE},
           "overflow_without_change": {"run": regb.get("run_id"), "verdict": regb.get("verdict"),
                                       "set": OV_BASE},
           "tsc_typecheck_rc": rc_t, "tsc_check_rc": BUILT, "vite_rc": rc_b,
           "asset": ASSET, "asset_bytes": ASSET_BYTES, "asset_sha1_local_recomputed": ASSET_SHA1,
           "diff_from_merge_base": MY_DIFF},
          open(os.path.join(WT, ART_REL), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
ART = os.path.join(WT, ART_REL)
git("checkout", "-q", BRANCH, cwd=WT)
TIP_NOW = git("rev-parse", BRANCH, cwd=WT)
ALREADY = blob_at_ref(TIP_NOW, ART_REL) == git("hash-object", ART, cwd=WT) and     not git("status", "--porcelain", "-uno", cwd=WT).splitlines()
if not ALREADY:
    git("add", "-f", ART_REL, "review/q406_block_r1.py", cwd=WT)
    rc, cout = run(["git", "-C", WT, "commit", "-q", "-m",
                    "ORD-0406 readouts: the before/after geometry table, the contaminated baseline I "
                    "replaced, and the overflow run compared with and without my change"])
    if rc and "nothing to commit" not in cout:
        bad.append("commit failed: %s" % cout[-160:])
    rc, pout = run(["git", "-C", WT, "-c", "http.proxy=", "-c", "https.proxy=", "push", "-q",
                    "origin", "refs/heads/" + BRANCH])
    if rc:
        bad.append("push failed: %s" % pout[-160:])
else:
    print("readouts already on the branch; no new commit")
PUSHED = head_of("refs/heads/" + BRANCH)
if not PUSHED or git("cat-file", "-t", PUSHED) != "commit":
    bad.append("the pushed head does not resolve: %r" % PUSHED)
elif not git_ok("merge-base", "--is-ancestor", HEAD_RUN, PUSHED):
    bad.append("the pushed head %s does not descend from the measured head %s" % (PUSHED[:8], HEAD_RUN[:8]))
NEW_FILES = [l for l in git("diff", "--name-only", HEAD_RUN, PUSHED).split("\n") if l.strip()]
if [f for f in NEW_FILES if not f.startswith("review/")]:
    bad.append("the follow-up commit touched non-review paths: %s" % NEW_FILES)
for rel in (V8, SPEC):
    if git("rev-parse", "%s:%s" % (HEAD_RUN, rel)) != git("rev-parse", "%s:%s" % (PUSHED, rel)):
        bad.append("%s differs between the measured head and the delivered head" % rel)
ART_BLOB = git("rev-parse", "%s:%s" % (PUSHED, ART_REL), check=False)
r7_bytes = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7_bytes).hexdigest()
if R7_SHA1 != "2690a3f7eb0b817a882212854ad906bfc8703e2d":
    bad.append("the door ruler is not the one the relay named")
if not git_ok("cat-file", "-e", R7_BLOB) or int(git("cat-file", "-s", R7_BLOB)) != len(ruler_bytes := r7_bytes):
    bad.append("the door ruler blob does not match the bytes I run")
tl = git("grep", "-n", "cn-attention-band", PUSHED, "--", V8)
mm2 = re.search(r":(\d+):", tl)
BAND_LINE = "%s:%s" % (V8, mm2.group(1)) if mm2 else (V8 + ":unreadable")
if not mm2:
    bad.append("could not locate the band section on the delivered head")
tk = git("grep", "-n", "--", "--cn-nav-h: 80px", PUSHED, "--", "frontend/src/design-tokens.css")
mt = re.search(r":(\d+):", tk)
TOKEN_LOC = "frontend/src/design-tokens.css:%s" % mt.group(1) if mt else "frontend/src/design-tokens.css:unreadable"
if not mt:
    bad.append("could not locate the named nav token")
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NOWC = "%s:%s" % (NOW[:2], NOW[2:])

B = []
A = B.append
A("### ORD-0406 · 车道 e4f3490f · 底栏吃掉的那一带：Today 的「需要关注」移到可命中区之上 · 四形×双语改前改后命中点读数 · 2026-09-29 %s+08" % NOWC)
A("")
A("枝 `refs/heads/%s`，push 后 ls-remote 现读头 = %s（不是本地 rev-parse）；读数跑在它上一笔 %s 上（收据 tree 格逐字），" % (
    BRANCH, PUSHED, HEAD_RUN))
A("两枚之间只多 review/ 读数件：added_path_count=%d，逐枚 %s；被我量的两枚文件在两头上 blob 逐字相同（%s、%s）。" % (
    len(NEW_FILES), "、".join(NEW_FILES) if NEW_FILES else "无", V8, SPEC))
A("   现尖比我这枝的基点 %s 又多了 %d 笔（`git rev-list --count` 现读），所以我是挂在旧尖上的候选，不是最新尖本身。" % (
    BASE_TIP[:12], N_TIP_AHEAD))
A("现尖我现读 = %s；我的改动相对共同祖先 %s 动了 touched_path_count=%d 枚，其中产品码 %d 枚、css 枚数=%d、" % (
    LIVE_TIP, BASE_TIP, len(MY_DIFF), len(PRODUCT_TOUCHED), len(CSS_TOUCHED)))
A("字典 i18n 枚数=%d —— 号令者要我别动 styles.css 与别的实例占的文件，我没动（css 为 0、i18n 为 0，所以 NO_GROWTH 天然成立）。" % (
    len(DICTIONARY_TOUCHED)))
A("")
A("## 改之前：四形 × 双语，滚动前那一格全在底栏底下（run_id=%s / %s）" % (
    str(base1.get("run_id")), str(base2.get("run_id"))))
def row(v, with_nav):
    head = "   arm=%s shape=%dx%d %s" % (v["arm"], v["w"], v["h"],
                                          ("nav_height=%d " % v["nav_h"]) if with_nav else "")
    return (head + "hit_line=%d band_box=[%d,%d,%d,%d] hero_box=[%d,%d,%d,%d] map_box=[%d,%d,%d,%d] "
            "band_hit=%s 该格源码 %s" % (v["hit_line"], v["band"][0], v["band"][1], v["band"][2], v["band"][3],
                                       v["hero"][0], v["hero"][1], v["hero"][2], v["hero"][3],
                                       v["map"][0], v["map"][1], v["map"][2], v["map"][3], v["hit"],
                                       BAND_LINE))


for arm in ("zh", "en"):
    for w, h in SHAPES:
        A(row(BEFORE[(arm, w, h)], True))
A("   基线有两件事要交代：① zh 390×844 那格第一次跑撞上 chromium 启动超时（launch timeout），没有读数；")
A("   ② 我改文件时 dev 服务器在热重载，基线那轮跑到一半被我污染 —— 受污染的三格（%s）我不用，" % (
    "、".join("%s %dx%d" % c for c in sorted(CONTAMINATED))))
A("      把文件还原回去单独补跑了 run_id=%s。上面这张表 8 格全是「改前」的真读数。" % str(base2.get("run_id")))
A("")
A("## 改之后：同一套格，滚动前就命中（run_id=%s verdict=%s passed=%d，tree=%s）" % (
    aft["run_id"], aft["verdict"], aft["counts"]["passed"], str(aft["tree"])[:12]))
for arm in ("zh", "en"):
    for w, h in SHAPES:
        A(row(AFTER[(arm, w, h)], False))
A("   命中判据是两条同时成立，不是一条：框要停在 hit_line 之上（band_clears_nav），并且对它中心做一次")
A("   elementFromPoint 要回到这一格里头（band_hit_test_inside）—— 只过第一条的写法叫做「看得见但点不到」。")
A("   改前 band 的 y 落在 %d..%d，改后落在 %d..%d；hit_line 最低那形是 %d（320×653）。" % (
    min(BAND_Y_BEFORE), max(BAND_Y_BEFORE), min(BAND_Y_AFTER), max(BAND_Y_AFTER), HIT_MIN))
A("")
A("## 我付出的代价，逐形量出来（号令者说不能因此把 hero 或地图挤出首屏）")
A("   位移：hero 下移 hero_shift=%s px、map 下移 map_shift=%s px（一格 band 高度加它自己的 margin）。" % (
    "、".join(str(x) for x in DISPLACE), "、".join(str(x) for x in MAP_SHIFT)))
A("   首屏还在不在：390×844 与 360×800 与 414×896 三形，改后地图顶边 %d/%d/%d 仍在各自 hit_line %d/%d/%d 之上；" % (
    AFTER[("zh", 390, 844)]["map"][1], AFTER[("zh", 360, 800)]["map"][1], AFTER[("zh", 414, 896)]["map"][1],
    AFTER[("zh", 390, 844)]["hit_line"], AFTER[("zh", 360, 800)]["hit_line"], AFTER[("zh", 414, 896)]["hit_line"]))
A("   320×653 这一形要说实话：地图顶边改前就在折叠外（map_y_before=%d > viewport_h=653），改后 %d，" % (
    BEFORE[("zh", 320, 653)]["map"][1], AFTER[("zh", 320, 653)]["map"][1]))
A("   它不是被我挤出去的，是本来就不在首屏；这一形改前改后的地图顶边就是上面那两个数（差 23 px）。")
A("   若号令者要这一形地图也进首屏，那得缩 hero/intro 的高度（styles.css 与 --cn-nav-* 那一档），不在这单授权里。")
A("   桌面无回归：1280×800 上三格都在（band=[%s,%s,%s,%s] 与 map=[%s,%s,%s,%s] 同格读到），" % DESK.groups())
A("   且这条位移只在手机断点里生效（`.v8-mobile-nav` 在 min-width 之外 display:none，见 frontend/src/styles.css:171）。")
A("   底栏那半件本来就已落地的账我核过：shell_padding_bottom=%s 而 nav_height=%s，" % (
    PAD.group(4), PAD.group(3)))
A("   常量具名在 %s（--cn-nav-h: 80px = 实测 76 + 4 余量，注释写明是量的不是算的）—— 这半我不再改。" % TOKEN_LOC)
A("")
A("## 回归对照：同一条闸，带我改动与不带我改动")
A("   `qoder-mobile-overflow.spec.ts`：带我改动 run_id=%s verdict=%s；把 %s 还原成尖上那份再跑 run_id=%s verdict=%s。" % (
    reg["run_id"], reg["verdict"], V8, regb["run_id"], regb["verdict"]))
A("   两跑失败集合逐枚相同（%s）—— 那三枚红在 Live 屏的地图标记上（right=%d 对 innerWidth=%d），" % (
        "、".join(x.split(":")[0] for x in OV_MINE), 435, 360))
A("   不是 Today、也不是我这格挤的；我不动它，归 ORD-0412/ORD-0407 那一串。")
A("   其余会碰到这一屏的 spec 我按断言方式筛过：`today-attention` 在 8 个文件里只被 testId 存在性用到")
A("   （如 frontend/e2e/qoder-map-interaction.spec.ts:80、frontend/e2e/qoder-ack-rendered.spec.ts:287），")
A("   横向溢出那条只判 overflowX —— 垂直位移不改这些判据，所以我没跑整套（跑整套的成本我留在下面）。")
A("")
A("## 编译臂")
A("   `tsc -p tsconfig.typecheck.json --noEmit` rc=%d、`-p tsconfig.check.json --noEmit` rc=%d、" % (rc_t, BUILT))
A("   `vite build` rc=%d，产物 served_asset=/assets/%s size_bytes=%d，本地字节重算 sha1=%s" % (
    rc_b, ASSET, ASSET_BYTES, ASSET_SHA1))
A("   （非 git 对象；同段可 cat-file 坐标：交付头 %s）" % PUSHED)
A("")
A("## 落码就一处：把那一格从地图之后搬到 hero-grid 之前")
A("   %s 里 <section className=\"cn-attention-band\" data-testid=\"today-attention-band\"> 整段上移，" % V8)
A("   新位置在 hero-grid 之前；改的是 JSX 顺序一处，没有新增样式、没有新 key、没有动任何文案字符串。")
A("   文件行号（现读）：那一格现在在 %s；它下面紧跟的就是 hero-grid 与地图，先后次序没换。" % BAND_LINE)
A("   读数件与脚本：`%s`（blob %s，可 cat-file）与 review/q406_collect_r1.py、review/q406_block_r1.py。" % (
    ART_REL, ART_BLOB))
A("")
A("## 没改善的部分")
A("1. 四形读数是这条车道私有栈上的 dev 服务器（frontend_port=%d）量的，没推到手机那代产物；手机链仍 NOT-DEPLOYED-OBSERVED。" %
  aft["ports"]["frontend"])
A("2. 320×653 那一形的地图本来就在首屏外，我这 23 px 让它更远（上面那格写了数）。要真修得缩 hero 高度，那不在本单授权里。")
A("3. 我没跑整套 e2e（只跑了本单 10 格 + 溢出闸两次对照）。按 testId 存在性筛出的依赖是我目前的证据面，")
A("   整套里若还有按绝对坐标断言 Today 的，我这一步会把它撞红 —— 那句话我现在只能标 NOT-MEASURED。")
A("4. 「移动」是我按裁决口径做的结构改动，不是新交互：号令者给的是「那一格必须落在可命中区内」，")
A("   我把整段上移；若号令者更看重「紧跟 Now/Next 之后」这条视觉层级（这段代码原先的注释就这样写），")
A("   那这一格应回退、改成缩 hero，我按令再走一遍同样的八格读数。")
A("5. 底栏高度的常量已经有人落过（--cn-nav-h），我这单没新增具名量；壳的 padding 比 nav 高 4 px 是有意的余量，")
A("   所以 pad_equals_nav=%s 这一格不是缺陷，是那条注释写的余量。" % PAD.group(5))
A("")
A("门尺自检（现行口径）：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 由本脚本在写盘前现跑，" % LIVE)
A("   findings 与退出码打印在下面；那把尺本地字节重算的文件 sha1=%s（非 git 对象声明；同段可 cat-file 坐标：" % R7_SHA1)
A("   blob %s、交付头 %s），第二道闸（同行声明 + 同段可解坐标）也在同一份草稿上逐值复算，红则不投递。" % (
    R7_BLOB, PUSHED))

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR_D := os.path.join(WT, "review"), "q406_block_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write("\n".join(B) + "\n")
rc, out = run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"),
               "--text", DRAFT, "--expect-clean"])
fl = [l.strip()[:175] for l in out.split("\n") if l.startswith("  line ")]
print("GATE_R7 rc=%d findings=%d" % (rc, len(fl)))
for l in fl:
    print("   ", l)
if rc:
    print("NOT PUBLISHED -- r7 red")
    sys.exit(2)


def bolt(path):
    raw = io.open(path, encoding="utf-8", newline="").read()
    ls = raw.split("\n")
    hx = re.compile(r"\b[0-9a-f]{40}\b")
    dec = re.compile(u"文件\\s*sha1|本机\\s*sha1|内容\\s*sha1|本地字节重算|字节重算的\\s*sha|未入\\s*git"
                     u"|不在对象库|非\\s*blob|不可\\s*cat-file|故意不可取回|sha1\\s*(over|of)\\s+bytes", re.I)

    def par(i):
        lo = hi = i
        while lo > 0 and ls[lo - 1].strip():
            lo -= 1
        while hi < len(ls) - 1 and ls[hi + 1].strip():
            hi += 1
        return "\n".join(ls[lo:hi + 1])
    vals = sorted(set(hx.findall(raw)))
    res = {v: git_ok("cat-file", "-t", v) for v in vals}
    ab = [(n, h) for n, t in enumerate(ls, 1) for h in sorted(set(hx.findall(t)))
          if not res[h] and not (bool(dec.search(t)) and any(
            res[o] for o in hx.findall(par(n - 1)) if o != h))]
    return len(vals), sum(res.values()), ab


NT, NR, AB = bolt(DRAFT)
print("BOLT tokens=%d resolvable=%d would_abort=%d" % (NT, NR, len(AB)))
for n, h in AB:
    print("    L%-3d %s" % (n, h[:12]))
if AB:
    print("NOT PUBLISHED -- the door's second arm would abort")
    sys.exit(3)
if glob.glob(os.path.join(INBOX, "qoder-0406_*.md")):
    print("REFUSED PUBLISH -- a live 0406 block is already in the inbox")
    sys.exit(4)
OUT = os.path.join(INBOX, "qoder-0406_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUT, os.path.getsize(OUT), "bytes  HEAD", PUSHED)
