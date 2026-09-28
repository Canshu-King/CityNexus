#!/usr/bin/env python3
"""ORD-0406 close-out: compile arm on a hardlinked export, the readouts artifact, a new branch name,
both doors, then the ledger block.

The compile arm runs on a `git archive` export of the branch's own head so the bytes compiled are the
committed bytes, with node_modules borrowed as hard links (shutil.copytree + os.link, which is what
`cp -al` does) rather than a copy and rather than a junction. One exit code per command, on its own
line, as the relay asked.
"""
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

WT = r"D:/moodle/_qoder_lane_q0406"
REPO = r"D:/moodle/CityNexus"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
SCR = r"D:/moodle/_qoder_lane_q0370_scratch"
SNAP = r"D:/moodle/_qoder_lane_0406_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
TSC = os.path.join(NM_SRC, "typescript", "bin", "tsc")
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
BRANCH = "review/Q-ord0406-attention-band-hit-r2"
TIP = "8d038b21f09477b933cff3b1c7b09845c542373b"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
V8 = "frontend/src/app/V8Experience.tsx"
V8_BEFORE_BLOB = "b431d26a94aebe1edac0c57f293f2ed442647f5f"
TOK = "frontend/src/design-tokens.css"
STY = "frontend/src/styles.css"
SPEC = "frontend/e2e/qoder-ord0406-attention-band-hit.spec.ts"
SPEC2 = "frontend/e2e/qoder-ord0426-drawer-last-row-hit.spec.ts"
PORTSPEC = "review/e4f_e2e_r1.py"
EV = "frontend/review/evidence/q406"
SHAPES = [(390, 844), (360, 800), (320, 653), (414, 896)]
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


def sha1(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()


def blob_at(ref, rel):
    out = git("rev-parse", "%s:%s" % (ref, rel), check=False)
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else ""


def head_of(refspec):
    for l in git("ls-remote", "origin", refspec).splitlines():
        p = l.split()
        if len(p) == 2 and p[1] == refspec:
            return p[0]
    return ""


def line_of(ref, rel, pattern):
    """"ref:rel:LINE" for the first grep hit -- every coordinate the block prints is a live read."""
    out = git("grep", "-n", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for %r in %s on %s" % (pattern, rel, ref[:8]))
        return "%s:?" % rel
    return "%s:%s" % (rel, m.group(1))


def receipt(tag):
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)), key=os.path.getmtime)
    if not fs:
        bad.append("no receipt for %s" % tag)
        return {}, ""
    return json.load(open(fs[-1], encoding="utf-8")), os.path.basename(fs[-1]).replace(".json", ".log")


LIVE_TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
HEAD = git("rev-parse", "HEAD", cwd=WT)
if not git_ok("merge-base", "--is-ancestor", TIP, HEAD):
    bad.append("my branch is not built on the tip the relay named")
if not git_ok("cat-file", "-e", LIVE_TIP):
    git("fetch", "-q", "origin", "refs/heads/mirror/integration-frontend-apple-pass1:refs/remotes/origin/mirror/integration-frontend-apple-pass1", cwd=WT)
if not git_ok("cat-file", "-e", LIVE_TIP):
    bad.append("the live tip 40-hex I want to quote is not retrievable: %s" % LIVE_TIP)
N_TIP_AHEAD = int(git("rev-list", "--count", "%s..%s" % (TIP, LIVE_TIP)) or 0)
BEFORE, AFTER = {}, {}
for arm in ("zh", "en"):
    for w, h in SHAPES:
        f = "%s_%dx%d.json" % (arm, w, h)
        for phase, store in (("before", BEFORE), ("after", AFTER)):
            p = os.path.join(WT, EV, phase, f)
            if not os.path.exists(p):
                bad.append("missing evidence file %s" % p)
                continue
            store[(arm, w, h)] = json.load(open(p, encoding="utf-8"))
for k in [(a, w, h) for a in ("zh", "en") for w, h in SHAPES]:
    if k not in BEFORE or k not in AFTER:
        continue
    if BEFORE[k]["hit"] is not False:
        bad.append("the before cell is not red: %s" % (k,))
    if AFTER[k]["hit"] is not True:
        bad.append("the after cell is not green: %s" % (k,))
    if AFTER[k]["scrollY"] != 0 or BEFORE[k]["scrollY"] != 0:
        bad.append("a reading was taken after scrolling: %s" % (k,))
    if AFTER[k]["hitTestInside"] is not True or BEFORE[k]["hitTestInside"] is not False:
        bad.append("the centre hit-test does not straddle: %s" % (k,))
    if len(AFTER[k]["bandRangeRects"]) < 2 or len(BEFORE[k]["bandRangeRects"]) < 2:
        bad.append("the band does not wrap on this cell, so the two-dimension claim is unsupported: %s" % (k,))
    if AFTER[k]["band"] is None or BEFORE[k]["band"] is None or AFTER[k]["map"] is None:
        bad.append("a box is missing: %s" % (k,))
    if AFTER[k]["hero"]["y"] >= AFTER[k]["map"]["y"] or BEFORE[k]["hero"]["y"] >= BEFORE[k]["map"]["y"]:
        bad.append("the hero/map order changed on this cell: %s" % (k,))
BEFORE_BOT = sorted({v["rangeBottom"] for v in BEFORE.values()})
AFTER_BOT = sorted({v["rangeBottom"] for v in AFTER.values()})
HITLINES = sorted({v["hitLine"] for v in BEFORE.values()})
BAND_BOX_BOT = sorted({v["band"]["y"] + v["band"]["h"] for v in BEFORE.values()})
HERO_SHIFT = sorted({AFTER[k]["hero"]["y"] - BEFORE[k]["hero"]["y"] for k in BEFORE})
MAP_SHIFT = sorted({AFTER[k]["map"]["y"] - BEFORE[k]["map"]["y"] for k in BEFORE})
MAP_OUT = sorted({"%s %dx%d" % (k[0], k[1], k[2]) for k in AFTER if AFTER[k]["map"]["y"] > AFTER[k]["innerHeight"]})
MAP_OUT_BEFORE = sorted({"%s %dx%d" % (k[0], k[1], k[2]) for k in BEFORE
                         if BEFORE[k]["map"]["y"] > BEFORE[k]["innerHeight"]})
MAP_UNDER_BAR = sorted({"%s %dx%d" % (k[0], k[1], k[2]) for k in AFTER if AFTER[k]["map"]["y"] > AFTER[k]["hitLine"]})
if MAP_OUT != MAP_OUT_BEFORE:
    bad.append("the set of shapes where the map starts below the fold changed: %s vs %s" % (
        MAP_OUT_BEFORE, MAP_OUT))
DESK_B = json.load(open(os.path.join(WT, EV, "before", "zh_1280x800_desktop.json"), encoding="utf-8"))
DESK_A = json.load(open(os.path.join(WT, EV, "after", "zh_1280x800_desktop.json"), encoding="utf-8"))
PAD_A = json.load(open(os.path.join(WT, EV, "after", "zh_390x844_padding.json"), encoding="utf-8"))
PAD_B = json.load(open(os.path.join(WT, EV, "before", "zh_390x844_padding.json"), encoding="utf-8"))
if int(PAD_A["shellPaddingBottom"].rstrip("px")) < PAD_A["navHeight"]:
    bad.append("the shell no longer reserves the bar's height")
AFT_R, AFT_LOG = receipt("q406a3")
BEF_R, BEF_LOG = receipt("q406b4")
GATE_R, GATE_LOG = receipt("q426g3")
REG_R, REG_LOG = receipt("q406rega")
REGB_R, REGB_LOG = receipt("q406regb")
OLD_AFT, _ = receipt("q406a2")
OLD_BEF, _ = receipt("q406b3")
if AFT_R.get("verdict") != "GREEN":
    bad.append("the after run is not GREEN")
if BEF_R.get("verdict") != "RED":
    bad.append("the before run is not RED, so the criterion does not bite")
if GATE_R.get("verdict") != "RED" or REGB_R.get("verdict") != "RED" or REG_R.get("verdict") != "RED":
    bad.append("a reporting-only run lost its expected verdict")
TREES = sorted({str(r.get("tree")) for r in (AFT_R, BEF_R, GATE_R, REG_R, REGB_R)})
if TREES != [HEAD]:
    bad.append("the runs I quote are not all on the head I publish: %s vs %s" % (TREES, HEAD))
DIRTY = [l for l in git("status", "--porcelain", cwd=WT).split("\n") if l.strip() and not l.startswith("??")]
if DIRTY:
    bad.append("tracked paths are modified right now, so the receipts do not name these bytes: %s" % DIRTY)
WT_BLOB = git("hash-object", os.path.join(WT, "frontend", "src", "app", "V8Experience.tsx"), cwd=WT)
if WT_BLOB == V8_BEFORE_BLOB:
    bad.append("the worktree still holds the reverted file; the after run would be a lie")

# ---------- compile arm on a hardlinked export of the branch ----------
os.makedirs(SNAP, exist_ok=True)
p1 = subprocess.Popen(["git", "-C", REPO, "archive", "--format=tar", HEAD], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["tar", "-x", "-C", SNAP], stdin=p1.stdout)
p1.stdout.close()
if p2.wait(300):
    bad.append("tar extract failed")
nm = os.path.join(SNAP, "frontend", "node_modules")
if not os.path.isdir(nm):
    shutil.copytree(NM_SRC, nm, copy_function=os.link, symlinks=True)
hard = os.path.join(nm, "typescript", "package.json")
NLINK = os.stat(hard).st_nlink if os.path.exists(hard) else 0
if NLINK < 2:
    bad.append("node_modules is not hard-linked into the snap: nlink=%d" % NLINK)
PRODP = [l for l in git("diff", "--name-only", TIP, HEAD).split("\n") if l.strip()]
VERIFY = []
for rel in PRODP + [V8]:
    sn = os.path.join(SNAP, *rel.split("/"))
    if not os.path.exists(sn):
        bad.append("the export is missing %s" % rel)
        continue
    hb = hashlib.sha1()
    raw = open(sn, "rb").read()
    hb.update(("blob %d\0" % len(raw)).encode() + raw)
    want = blob_at(HEAD, rel)
    VERIFY.append((rel, hb.hexdigest(), want, hb.hexdigest() == want))
for rel, got, want, ok in VERIFY:
    if not ok:
        bad.append("the exported bytes differ from the branch for %s: %s vs %s" % (rel, got, want))
ARCH_BLOB = dict((r, g) for r, g, w, o in VERIFY).get(V8, "")
SELF = "review/q406_block_r2.py"
NLINK_ASSERT = "%s:%d" % (SELF, 1 + next(i for i, l in enumerate(io.open(
    os.path.join(WT, "review", "q406_block_r2.py"), encoding="utf-8").read().splitlines())
    if "node_modules is not hard-linked" in l))
TSCONFS = sorted(l for l in git("ls-tree", "--name-only", "HEAD:frontend", cwd=WT).split("\n")
                 if l.startswith("tsconfig"))
BUILD = []
for label, cmd in (("npx tsc -p tsconfig.check.json --noEmit", [NODE, TSC, "-p", "tsconfig.check.json", "--noEmit"]),
                   ("npx tsc -p tsconfig.typecheck.json --noEmit",
                    [NODE, TSC, "-p", "tsconfig.typecheck.json", "--noEmit"])):
    rc, o = run(cmd, cwd=os.path.join(SNAP, "frontend"), timeout=2400)
    BUILD.append((label, rc, len([l for l in o.split("\n") if "error TS" in l])))
    if rc:
        bad.append("%s rc=%d %s" % (label, rc, o[-200:]))
rc, vo = run([NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"],
             cwd=os.path.join(SNAP, "frontend"), timeout=2400)
BUILD.append(("npx vite build", rc, 0))
if rc:
    bad.append("vite build rc=%d %s" % (rc, vo[-200:]))
assets = glob.glob(os.path.join(SNAP, "frontend", "dist", "assets", "index-*.js"))
ASSET = os.path.basename(assets[0]) if len(assets) == 1 else "?"
ASSET_BYTES = os.path.getsize(assets[0]) if len(assets) == 1 else 0
ASSET_SHA1 = sha1(assets[0]) if len(assets) == 1 else ""
if len(assets) != 1:
    bad.append("expected one built asset, found %d" % len(assets))
FREE = run(["df", "-B1", "/d"])[1].split("\n")[-1].split()
GB = "%.1f GB free on D" % (int(FREE[3]) / 1073741824.0) if len(FREE) > 3 and FREE[3].isdigit() else "?"

GATE_OUT = open(os.path.join(LIVE, "e2e_logs", GATE_LOG), encoding="utf-8", errors="replace").read()
m = re.search(r"O426 gate zh 390x844 (\{.*?\})", GATE_OUT)
G = json.loads(m.group(1)) if m else {}
if not G or G.get("at_end", 99) > 2:
    bad.append("the drawer gate reading is missing or the list was not at its end")
COVERED = G["last_row_bottom"] - G["hit_line"]

ART_REL = "review/q406_readouts_r2.json"
json.dump({"branch": BRANCH, "branch_head_at_export": HEAD, "tip_measured": TIP, "live_tip": LIVE_TIP,
           "before_evidence": {("%s %dx%d" % k): BEFORE[k] for k in BEFORE},
           "after_evidence": {("%s %dx%d" % k): AFTER[k] for k in AFTER},
           "desktop": {"before": DESK_B, "after": DESK_A}, "padding": {"before": PAD_B, "after": PAD_A},
           "runs": {"after": AFT_R, "before": BEF_R, "gate0426": GATE_R,
                    "overflow_with_change": REG_R, "overflow_reverted": REGB_R},
           "logs": {"after": AFT_LOG, "before": BEF_LOG, "gate0426": GATE_LOG,
                    "overflow_with_change": REG_LOG, "overflow_reverted": REGB_LOG},
           "build": [{"cmd": c, "rc": r, "error_lines": e} for c, r, e in BUILD],
           "export": {"snap": SNAP, "node_modules_nlink": NLINK, "exported_v8_blob": ARCH_BLOB,
                      "asset": ASSET, "asset_bytes": ASSET_BYTES, "asset_sha1_local_recomputed": ASSET_SHA1},
           "drawer_last_row_0426_reading_only": G},
          open(os.path.join(WT, ART_REL), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
git("add", "-f", ART_REL, "review/q406_block_r2.py", cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0406 readouts r2: per-cell evidence, the compile arm on a hardlinked export, "
              "and the drawer last-row reading I am only reporting"])
if rc and "nothing to commit" not in co:
    bad.append("commit failed: %s" % co[-160:])
if bad:
    print("REFUSING BEFORE PUSH -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
rc, po = run(["git", "-C", WT, "-c", "http.proxy=", "-c", "https.proxy=", "push", "-q",
              "origin", "refs/heads/" + BRANCH])
if rc:
    print("PUSH FAILED -- %s" % po[-200:])
    sys.exit(1)
PUSHED = head_of("refs/heads/" + BRANCH)
if not PUSHED or git("cat-file", "-t", PUSHED) != "commit":
    bad.append("the pushed head does not resolve: %r" % PUSHED)
elif not git_ok("merge-base", "--is-ancestor", HEAD, PUSHED):
    bad.append("the pushed head %s does not contain the measured head %s" % (PUSHED[:8], HEAD[:8]))
TOUCHED = [l for l in git("diff", "--name-only", TIP, PUSHED).split("\n") if l.strip()]
N_BACKEND = len([p for p in TOUCHED if p.startswith("backend/")])
if N_BACKEND:
    bad.append("backend paths are in my diff")
for p in TOUCHED:
    if not blob_at(PUSHED, p):
        bad.append("no blob for touched path %s" % p)
ART_BLOB = blob_at(PUSHED, ART_REL)
HEAD_BLOB = blob_at(PUSHED, V8)
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED:
    bad.append("the door ruler is not the one the relay named: %s" % R7_SHA1)
if not git_ok("cat-file", "-e", R7_BLOB) or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    bad.append("the door ruler blob does not match the bytes I run")
BAND_LINE = line_of(PUSHED, V8, 'className="cn-attention-band"')
JUDGE_RANGE = line_of(PUSHED, SPEC, "the band's last painted line ends at")
JUDGE_HIT = line_of(PUSHED, SPEC, "a hit-test at the band's centre must land back inside it")
JUDGE_PAD = line_of(PUSHED, SPEC, "the scroll container has to reserve")
TOKEN_LINE = line_of(PUSHED, TOK, "--cn-nav-h: 80px")
SHELL_PAD_LINE = line_of(PUSHED, STY, "padding-bottom: var(--cn-nav-clearance")
DRAWER_PAD = line_of(PUSHED, STY, "#v8-nav-drawer {")
GATE_ASSERT = line_of(PUSHED, SPEC2, "the row must end above the fixed bar")
PORT_LINE = line_of(PUSHED, PORTSPEC, "LOW, HIGH = ")
NAV_H_COUNT = len([l for l in git("grep", "-n", "-e", "cn-nav-h", PUSHED, "--", STY, check=False).split("\n")
                   if l.strip()])
OV_RE = r"(live@\d+: \S+ right=\d+)"
OV_MINE = sorted(set(re.findall(OV_RE, open(os.path.join(LIVE, "e2e_logs", REG_LOG),
                                            encoding="utf-8", errors="replace").read())))
OV_BASE = sorted(set(re.findall(OV_RE, open(os.path.join(LIVE, "e2e_logs", REGB_LOG),
                                            encoding="utf-8", errors="replace").read())))
if not OV_MINE or OV_MINE != OV_BASE:
    bad.append("the overflow sets differ: %s vs %s" % (OV_MINE, OV_BASE))
OV_MAX = max(int(re.search(r"right=(\d+)", x).group(1)) for x in OV_MINE)
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = "%s:%s" % (NOW[:2], NOW[2:])

B = []
A = B.append
A("### ORD-0406 · 道0370（会话 e4f3490f）· Today「需要关注」那一格移进可命中区 · 四形×双语改前改后逐格 · 2026-09-29 %s+08" % NW)
A("")
A("## 交付坐标")
A("   新枝名 `refs/heads/%s`（origin 上此前没有同名枝，`git ls-remote origin \"refs/heads/review/*0406*\"` 现读只有 r1 那一枚，所以这不是覆盖）。" % BRANCH)
A("   push 后我自己再 `git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/%s` 回读头 = %s" % (BRANCH, PUSHED))
A("   （`git cat-file -t %s` = commit；上面所有产品读数的字节都在它的父 %s 里，`git merge-base --is-ancestor` 现读成立；" % (PUSHED, HEAD))
A("   这一枚 %s 只多了读数件 `%s`（枝上 blob %s，可 cat-file）与本生成器。）" % (PUSHED[:8], ART_REL, ART_BLOB))
A("   基点 = 号令者当时给的现尖 %s；写这块之前我又读了一次 = %s，比我挂的基点多 %d 笔，所以我这是候选枝、权威线我没动。" % (TIP, LIVE_TIP, N_TIP_AHEAD))
A("   相对基点动了 touched_file_count=%d 枚，逐枚（`git diff --name-only %s %s` 现读 + 各自枝上 blob）：" % (
    len(TOUCHED), TIP[:8], PUSHED[:8]))
for p in TOUCHED:
    A("      %s blob %s" % (p, blob_at(PUSHED, p)))
A("   上面 backend/ 前缀计数=%d 枚（`git diff --name-only %s %s` 现读），frontend/src/styles.css 与 frontend/src/i18n/LocaleContext.tsx" % (
    N_BACKEND, TIP, PUSHED))
A("   都不在这 %d 枚清单里（那两处归 ORD-0419 与别的实例），所以本单没有新增中文文案、也没有新字典键，双语两臂读的是同一批既有键。" % len(TOUCHED))
A("")
A("## 值守 05:29 的第①件（改前）：滚动之前那一格的两条绘制行都在底栏以下（run_id=%s verdict=%s passed=%d failed=%d，tree=%s）" % (
    BEF_R["run_id"], BEF_R["verdict"], BEF_R["counts"].get("passed", -1), BEF_R["counts"].get("failed", -1),
    BEF_R["tree"]))
for arm in ("zh", "en"):
    for w, h in SHAPES:
        v = BEFORE[(arm, w, h)]
        A("   arm=%s viewport=%dx%d nav_height=%d hit_line=%d band_box_y=%d band_box_bottom=%d band_lines=%d "
          "band_range_bottom=%d centre_hit_inside=%s band_hit=%s scroll_y=%d 判据 %s 证据 %s/before/%s_%dx%d.json" % (
              arm, w, h, v["navHeight"], v["hitLine"], v["band"]["y"], v["band"]["y"] + v["band"]["h"],
              len(v["bandRangeRects"]), v["rangeBottom"], v["hitTestInside"], v["hit"], v["scrollY"],
              JUDGE_RANGE, EV, arm, w, h))
A("   八格 band_hit=%s、hit_line 四形分别 %s、band 最后一条绘制行底边落在 %d..%d（元素框底边是 %d..%d，比绘制行更晚暴露问题）。" % (
    "、".join(str(BEFORE[k]["hit"]) for k in BEFORE), "、".join(str(x) for x in HITLINES),
    min(BEFORE_BOT), max(BEFORE_BOT), min(BAND_BOX_BOT), max(BAND_BOX_BOT)))
A("   两臂的收据 tree 格是同一枚 %s（= 我要发的产品提交），唯一差别是工作区里 %s 这一枚文件：" % (TREES[0], V8))
A("   改前那轮跑之前我把它 `git checkout %s -- %s` 还原成基点那枚 blob，还原后本地 `git hash-object` = %s ，" % (TIP[:8], V8, V8_BEFORE_BLOB))
A("   与 `git rev-parse %s:%s` 逐字相同；跑完立刻 `git checkout HEAD -- %s` 还原（现读工作区 hash-object = %s ，" % (TIP, V8, V8, WT_BLOB))
A("   与 `git rev-parse %s:%s` = %s 逐字相同，`git status --porcelain` 对被跟踪路径为空）。" % (PUSHED, V8, HEAD_BLOB))
A("   这八格 + 桌面 + 内距是第二次独立运行：改后臂 run_id=%s 与 %s，改前臂 run_id=%s 与 %s。" % (
    OLD_AFT["run_id"], AFT_R["run_id"], OLD_BEF["run_id"], BEF_R["run_id"]))
A("   两轮的日志分别是 %s 与 %s 与 %s 与 %s；" % (
    OLD_AFT["log"], AFT_R["log"], OLD_BEF["log"], BEF_R["log"]))
A("   两轮产出的 20 枚证据 JSON 逐字节相同（判据：第一轮的证据已提交在被引用的那枚 tree %s 上，" % TREES[0])
A("   第二轮跑完 `git status --porcelain` 对被跟踪路径为空。")
A("   这就不用 03:56 那次基线了：那次跑到一半我改了文件、dev 服务器热重载，en 414 那两行其实是改后的数。")
A("")
A("## 值守 05:29 的第①件（改后）：同一套八格，滚动前就命中（run_id=%s verdict=%s passed=%d，tree=%s，日志 %s）" % (
    AFT_R["run_id"], AFT_R["verdict"], AFT_R["counts"]["passed"], AFT_R["tree"], AFT_LOG))
for arm in ("zh", "en"):
    for w, h in SHAPES:
        v = AFTER[(arm, w, h)]
        A("   arm=%s viewport=%dx%d hit_line=%d band_box_y=%d band_lines=%d band_range_bottom=%d "
          "centre_hit_inside=%s band_hit=%s hero_y=%d map_y=%d scroll_y=%d 判据 %s 证据 %s/after/%s_%dx%d.json" % (
              arm, w, h, v["hitLine"], v["band"]["y"], len(v["bandRangeRects"]), v["rangeBottom"],
              v["hitTestInside"], v["hit"], v["hero"]["y"], v["map"]["y"], v["scrollY"], JUDGE_HIT,
              EV, arm, w, h))
A("   八格 band_hit=%s、band_range_bottom=%d..%d 全部小于各自 hit_line；中心 elementFromPoint 回到这一格自己（%s）。" % (
    "、".join(str(AFTER[k]["hit"]) for k in AFTER), min(AFTER_BOT), max(AFTER_BOT), JUDGE_HIT))
A("   判据是两条同时成立，不是只看框高：最后一条绘制行（`Range.getClientRects()`）底边 <= hit_line（%s）" % JUDGE_RANGE)
A("   并且对它中心做 elementFromPoint 要回到这一格（%s）。八格这一格文案都折成 band_lines=2 行（改前改后都是 2 枚 client rect），" % JUDGE_HIT)
A("   只看元素框会把「框过线、字还压着」判成绿，所以两个维度逐格都留在证据文件里。")
N3F = "review/n3_0407_evidence_r1/controls_before_79ca877c.json"
N3 = json.loads(subprocess.run(["git", "-C", WT, "show", "%s:%s" % (PUSHED, N3F)],
                               capture_output=True, text=True, encoding="utf-8").stdout)
N3_LINES = [i + 1 for i, l in enumerate(io.open(os.path.join(WT, N3F), encoding="utf-8").read().splitlines())
            if '"hit_floor_px"' in l]
N3_CELL_ATT = len([c for scr in N3["screens"].values() for c in scr["cells"] if "attention" in c.lower()])
A("   对照号令者点名的冻结口径（车道 N3 的 %s:%d，枝上 blob %s）：它的 hit_floor_px=%d 与我同一形 viewport=%s 的 hit_line=%d 相等；" % (
    N3F, N3_LINES[0], blob_at(PUSHED, N3F), N3["hit_floor_px"], N3["viewport"], BEFORE[("zh", 390, 844)]["hitLine"]))
A("   那份冻结清单里含 attention 的格数=%d（它列的键面是 map-empty-body / bookings-no-stay / live-no-proposal 这类，blob %s）；" % (
    N3_CELL_ATT, blob_at(PUSHED, N3F)))
A("   所以 Today 这一格的命中点读数是第一次有人取，不是我引用别人已有的数；被引件自报 tree_head=%s （`git cat-file -t` 现读 = commit）。" % N3["tree_head"])
A("")
A("## 号令者的要件「不改 hero 与地图的先后次序」与这一改的代价")
A("   hero_shift=%s px、map_shift=%s px（八格同一数：那一条 band 的行高 + 它的下边距）。" % (
    "、".join(str(x) for x in HERO_SHIFT), "、".join(str(x) for x in MAP_SHIFT)))
A("   次序逐格现读：改前与改后都是 hero_y < map_y（八格×两阶段全部成立，脚本对它做了断言），我没有把地图提到 hero 之前。")
A("   代价要说实话：320×653 那一形地图改前就在折叠外（zh map_y=%d > innerHeight=%d），改后 map_y=%d —— 不是我挤出去的，" % (
    BEFORE[("zh", 320, 653)]["map"]["y"], BEFORE[("zh", 320, 653)]["innerHeight"], AFTER[("zh", 320, 653)]["map"]["y"]))
A("   但我把它又推远 %s px，且改后 map_y 仍 > hit_line=%d。集合没变大：map_out_shapes_before=%s map_out_shapes_after=%s。" % (
    "、".join(str(x) for x in MAP_SHIFT), AFTER[("zh", 320, 653)]["hitLine"],
    "、".join(MAP_OUT_BEFORE) or "无", "、".join(MAP_OUT) or "无"))
A("   地图顶边落在底栏带下的形：after_map_under_bar=%s（两形本来就整块在折叠外，要救得缩 hero/intro 高度，不在本单授权里）。" % (
    "、".join(MAP_UNDER_BAR)))
A("   桌面无回归（zh 1280×800，%s）：band 从 y=%d 移到 y=%d，最后一条绘制行底边 %d -> %d，hero_y=%d 紧随其后；" % (
    line_of(PUSHED, SPEC, "all three surfaces still render"), DESK_B["band"]["y"], DESK_A["band"]["y"],
    DESK_B["rangeBottom"], DESK_A["rangeBottom"], DESK_A["hero"]["y"]))
A("   桌面这一格 desktop_nav_height=%d（`.v8-mobile-nav` 在这一形不渲染），所以它的 hit_line=%d 不可用、我没有拿它当绿证，只比位置与重叠。" % (
    DESK_A["navHeight"], DESK_A["hitLine"]))
A("   底栏内距那一半我不再动，因为它已经在基点上：shell_padding_bottom=%s 对 nav_height=%s（证据 %s/after/zh_390x844_padding.json，" % (
    PAD_A["shellPaddingBottom"], PAD_A["navHeight"], EV))
A("   判据 %s；常量具名 %s，80 = 实测 76 + 4 余量；壳的具名规则在 %s）。" % (JUDGE_PAD, TOKEN_LINE, SHELL_PAD_LINE))
A("")
A("## 值守 05:29 的第②件：硬链导出重跑 tsc 与 vite build，退码逐件一行（导出根 %s）" % SNAP)
A("   导出 = `git archive --format=tar %s | tar -x -C %s`；node_modules 用 os.link 逐文件借过来（等同 `cp -al`，" % (HEAD, SNAP))
A("   不是拷贝也不是 junction）：`typescript/package.json` 的 st_nlink=%d（>=2 才是链接），来源是 %s 。" % (NLINK, NM_SRC))
A("   编译没有 tsconfig 的默认工程可指：`frontend/` 下被跟踪的 tsconfig 只有 %s（`git ls-tree --name-only HEAD:frontend` 现读），" % "、".join(TSCONFS))
A("   所以 `npx tsc --noEmit` 这一句在本仓库没有默认工程可解析，我跑的是两枚具名工程 + 一次 vite build，退码逐件在下面一行行写。")
A("   导出树与枝上字节逐枚核过（本地 `git hash-object` 口径 vs `git rev-parse %s <path>`）：verify_pair_count=%d 枚全部相等，" % (HEAD, len(VERIFY)))
A("   其中 %s 的导出 hash-object = %s = `git rev-parse %s:%s` = `git rev-parse %s:%s` 三处逐字相同 ⇒ 编的是枝上字节、不是我的工作区字节。" % (
    V8, ARCH_BLOB, HEAD, V8, PUSHED, V8))
for label, rc, errs in BUILD:
    A("   cmd=%s rc=%d error_lines=%d" % (label, rc, errs))
A("   产物唯一：/assets/%s size_bytes=%d，本地字节重算文件 sha1=%s（非 git 对象、不在对象库里；" % (ASSET, ASSET_BYTES, ASSET_SHA1))
A("   同段可 cat-file 的坐标：交付头 %s 与该文件在枝上的 blob %s 是两回事，这里给头 %s）。" % (PUSHED, ART_BLOB, PUSHED))
A("")
A("## 回归对照：同一条溢出闸，带我改动与不带")
A("   `qoder-mobile-overflow.spec.ts` 这条闸（不是我写的）：带我改动 run_id=%s verdict=%s tree=%s 日志 %s ；" % (
    REG_R["run_id"], REG_R["verdict"], REG_R["tree"], REG_R["log"]))
A("   把 %s 单独还原成基点 blob 后重跑 run_id=%s verdict=%s tree=%s 日志 %s 。两跑的 tree 同一枚 %s ，" % (
    V8, REGB_R["run_id"], REGB_R["verdict"], REGB_R["tree"], REGB_R["log"], REGB_R["tree"]))
A("   唯一差别就是我这一步的有无（还原后 hash-object = %s ，与 `git rev-parse %s:%s` 逐字相同）。" % (V8_BEFORE_BLOB, TIP, V8))
A("   两跑失败集合逐枚相同（failure_shape_count=%d：%s），right 最大 %d —— 红在 Live 屏的 maplibre 标记上，" % (
    len(OV_MINE), "、".join(OV_MINE), OV_MAX))
A("   不是 Today、也不是我这 %s px 挤的（两跑唯一差别就是那 %s px 的有无）。" % (
    "、".join(str(x) for x in MAP_SHIFT), "、".join(str(x) for x in MAP_SHIFT)))
A("")
A("## 顺路量到、**但不是我这单修的**：抽屉末行仍被底栏压住（归 ORD-0426 / 车道 N3）"
  )
A("   我为 ORD-0426 写了常驻闸（列表滚到底后末行要能被命中），跑在我这条枝上：run_id=%s verdict=%s passed=%d failed=%d 日志 %s 。" % (
    GATE_R["run_id"], GATE_R["verdict"], GATE_R["counts"].get("passed", -1), GATE_R["counts"].get("failed", -1), GATE_LOG))
A("   读数（zh 390×844，已滚到底 at_end=%d scrolled=%d rows=%d）：末行 %r last_row_bottom=%d 对 hit_line=%d → 下沿被压 %d px；" % (
    G["at_end"], G["scrolled"], G["rows"], G["last_row_text"], G["last_row_bottom"], G["hit_line"], COVERED))
A("   判据那一行 %s（`last_row_bottom <= hit_line` 才是这次报红的断言；上一条 centre hit 断言是绿的：hit_inside=%s hit_tag=%s）。" % (
    GATE_ASSERT, G["hit_inside"], G["hit_tag"]))
A("   成因位置：抽屉自己的滚动容器下内距是 scroller_padding_bottom=%s，不是底栏高度 %d px（规则在 %s：width min(300px,84vw) + padding 18px 14px 24px；" % (
    G["scroller_padding_bottom"], G["nav_height"], DRAWER_PAD))
A("   串 `cn-nav-h` 在 %s 的命中行数=%d，它只定义在 %s）。所以那条单说的「padding 那一半已落」落的是 `.v8-product-shell`，不是抽屉的滚动容器。" % (
    STY, NAV_H_COUNT, TOKEN_LINE))
A("   另一枚数也支持「滚动容器被窄了一截」：scroller_client_width=%d 对 client_width=%d。" % (
    G["scroller_client_width"], G["client_width"]))
A("   我不改它（单、文件、插入次序都不是我的），原样交给 N3/号令者裁。")
A("")
A("## 落码就一处")
A("   %s：整段 `<section className=\"cn-attention-band\" data-testid=\"today-attention-band\">`（六十九行连着它的子节点）" % V8)
A("   从 `MapPanel` / `cn-hero-strip` 之后移到 `.v8-hero-grid` 之前（现读该格在 %s）。没有新样式、没有新 key、没有动文案；" % BAND_LINE)
A("   原先那句「要紧的事要说在 Now/Next 之后」的注释我改写成被量掉的说明（这一改的现场理由是 y=1037 对 hit_line=724）。")
A("   仪表：新 spec `%s`（八格逐格一份证据文件 + 桌面 + 内距格）与 `%s`（抽屉末行那条，我按 RED 如实交）。" % (SPEC, SPEC2))
A("   读数件 `%s`（枝上 blob %s，可 cat-file）；本生成器 `review/q406_block_r2.py`（枝上 blob %s）。" % (
    ART_REL, ART_BLOB, blob_at(PUSHED, "review/q406_block_r2.py")))
A("")
A("## 没改善的部分")
A("1. 八格读数来自车道私有栈的 dev 服务器（frontend_port=%s，端口带具名格 %s），没有推到手机握的那代产物上；手机链那一格仍 NOT-DEPLOYED-OBSERVED。" % (
    AFT_R["ports"]["frontend"], PORT_LINE))
A("2. 320×653 两形的地图本来在首屏外，我这一步把它再推远 %s px；要真修得缩 hero/intro 高度，不在这单授权里。" % (
    "、".join(str(x) for x in MAP_SHIFT)))
A("3. 我只跑了本单的八格 + 桌面 + 内距，加那条溢出闸两次对照，没跑整套 e2e。整套里若有按绝对坐标断言 Today 的，" )
A("   这一改可能撞红 —— 这条我标 NOT-MEASURED（不是「没问题」）。要我在私有栈上跑整套 e2e 说一句，我跑并另生一枚读数件。")
A("4. 「把这一格往上搬」是我按裁决口径做的结构改动。若号令者更要那条形（首屏里 hero 之后紧跟要紧的事），")
A("   正确做法是缩 hero 高度而不是搬这一格；说一句我就回退重跑八格。")
A("5. 抽屉末行那格红我没修（不是我的单、不是我的文件），只把数与两处规则位置交给 N3/号令者。")
A("6. 桌面那一形的验收口径只有位置与重叠（desktop_nav_height=%d 使 hit_line 无定义），不是命中点。" % DESK_A["navHeight"])
A("7. 本回合我自己废掉一次：第一次跑这具生成器时 node_modules 的借法用了 `xcopy /E /H /K`，它一枚依赖文件也没带过来")
A("   （判据那一行 %s 当场报 nlink 读数=0，即 typescript/package.json 在导出里根本不存在），所以那一轮的 tsc/vite 退码全是无依赖造成的假红。" % NLINK_ASSERT)
A("   那一轮在 push 之前就 REFUSE，但它已经先落了一枚带废读数的本地提交 47b259b0c37a58772fff9eaec3465ada6cca951c （`git cat-file -t` 现读 = commit）；")
A("   那枚从没推过 origin，我用 `git reset --mixed %s` 把它退回未提交状态（工作区文件一枚没丢），所以现在这条枝上带的就是重跑这一次的数。" % HEAD)
A("   悬空对象仍在本地对象库里，要复核那一次的假红可以 `git cat-file -p 47b259b0c37a58772fff9eaec3465ada6cca951c` ，改法见同文件 %s 。" % SELF)
A("8. 盘：%s（`df -B1 /d` 写这块之前现读）；本车道起的进程我用完按 pid 各自关并 `netstat -ano` 复查。" % GB)
A("")
A("门尺自检（值守 05:29 口径）：`claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0，退出码与 findings 由本进程写盘前现跑；" )
A("   那把尺本地字节重算文件 sha1=%s（与值守给的 40 位逐字相同；这是非 git 对象声明，" % R7_SHA1)
A("   同段可 cat-file 的坐标：入库 blob %s ，`git cat-file -s %s` 得 byte_count=%d 与我运行的字节数相同；交付头 %s）。" % (
    R7_BLOB, R7_BLOB, len(r7b), PUSHED))
A("   第二道闸我在同一份草稿上逐值复算：只扫逐字 40 位，免除要同一行写明不可取回、且同段有另一枚能 cat-file 的 40 位；")
A("   path:line 在那道闸里不算数。上面 %s 与 %s 两枚都可 cat-file，所以只有 asset_sha1 那一处走声明；abort 清单非空就不投递。" % (R7_BLOB, ART_BLOB))

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR, "q406_block_r2_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write("\n".join(B) + "\n")
print("DRAFT", DRAFT, os.path.getsize(DRAFT), "bytes  HEAD", PUSHED)
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
    print("NOT PUBLISHED -- second arm would abort")
    sys.exit(3)
if glob.glob(os.path.join(INBOX, "qoder-0370_*.md")):
    print("REFUSED PUBLISH -- a live qoder-0370 block is in the inbox")
    sys.exit(4)
OUT = os.path.join(INBOX, "qoder-0370_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
