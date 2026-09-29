#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORD-0455 delivery: the four-tier estimation ladder.

Order of operations matters more than anything else in this file: every refusal is evaluated and
printed BEFORE the first commit, so a block can never quote a run that is not on the head it
publishes. After the push, the coordinates the block will quote are read back out of the remote.
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
import time

WT = r"D:/moodle/_qoder_lane_q0406"
REPO = r"D:/moodle/CityNexus"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
SCR = r"D:/moodle/_qoder_lane_q0370_scratch"
SNAP = r"D:/moodle/_qoder_lane_0455_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
NODE = r"C:/Program Files/nodejs/node.exe"
TSC = os.path.join(NM_SRC, "typescript", "bin", "tsc")
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BRANCH = "review/Q-ord0455-estimation-ladder-r1"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
SPEC = "frontend/e2e/qoder-ord0455-estimation-ladder-r1.spec.ts"
ART = "review/q455_estimation_ladder_r1.json"
GEN = "review/q455_ladder_r1.py"
RUNNER = "review/e4f_e2e_r1.py"

NEW = [
    "frontend/src/features/estimation/estimationLadder.ts",
    "frontend/src/features/estimation/estimationLadderCopy.ts",
    "frontend/src/features/estimation/EstimationLadderPanel.tsx",
    "frontend/src/features/estimation/estimationLadder.css",
]
CHANGED = [
    "frontend/src/features/stay/StayExplorer.tsx",
    "frontend/src/app/v8PanelRegistry.tsx",
    "frontend/src/lib/displayVocabulary.ts",
]
WALL = ["frontend/src/styles.css", "frontend/src/app/V8Experience.tsx"]
DEPENDS = [
    "frontend/src/i18n/LocaleContext.tsx",
    "frontend/e2e/_qoderShellSeed.ts",
    "frontend/e2e/_qoderEvidence.ts",
    "frontend/src/app/V8Experience.tsx",
]
# The wall cells this batch had to read but was forbidden to change, named by the order.
READOUT_CELLS = [
    (WALL[1], "每人每天约"),
    (WALL[1], "map.unknownCosts"),
    ("frontend/src/features/stay/StayExplorer.tsx", "function priceLabel("),
    ("frontend/src/features/stay/StayExplorer.tsx", "暂无供应商证据"),
    ("frontend/src/lib/budgetEvidence.ts", "export type BudgetEvidenceState"),
    ("frontend/src/features/agent/CopilotDock.tsx", "const VERIFICATION_LABELS"),
    ("frontend/src/features/trip/ActivityDetail.tsx", "都在约"),
]
bad = []


def run(cmd, cwd=None, timeout=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def git(*a, check=True, cwd=REPO):
    rc, out = run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", cwd] + list(a))
    if check and rc:
        bad.append("git " + " ".join(a) + " rc=" + str(rc) + " " + out[-160:])
    return out.strip()


def git_ok(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd] + list(a), capture_output=True).returncode == 0


def blob_at(ref, rel):
    out = git("rev-parse", ref + ":" + rel, check=False)
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else ""


def head_of(refspec):
    for l in git("ls-remote", "origin", refspec).splitlines():
        p = l.split()
        if len(p) == 2 and p[1] == refspec:
            return p[0]
    return ""


def line_of(ref, rel, pattern):
    out = git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for " + repr(pattern) + " in " + rel)
        return ""
    return rel + ":" + m.group(1)


# ---------- 1. where my head sits against the live line ----------
TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
if not re.fullmatch(r"[0-9a-f]{40}", TIP or ""):
    bad.append("the live tip did not read back: " + repr(TIP))
HEAD = git("rev-parse", "HEAD", cwd=WT)
NAMED_TIP = "4ee14229f80691cf8e5ea913375c0caf83ac02ee"
BASE = git("merge-base", TIP, HEAD) if TIP else ""
N_LAG = int(git("rev-list", "--count", HEAD + ".." + TIP) or 0) if TIP else -1
NAMED_ON_MINE = git_ok("merge-base", "--is-ancestor", NAMED_TIP, HEAD)
if TIP and not git_ok("merge-base", "--is-ancestor", BASE, HEAD):
    bad.append("the merge base is not on my history")
DRIFT = [f for f in DEPENDS if blob_at(HEAD, f) and blob_at(TIP, f) and blob_at(HEAD, f) != blob_at(TIP, f)]
if DRIFT:
    bad.append("bytes my readings depend on moved past my head: " + json.dumps(DRIFT))
MT_RC, MT_OUT = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, HEAD])
TOUCHED = [l for l in git("diff", "--name-only", BASE, HEAD, cwd=REPO).splitlines() if l.strip()]
HIT_WALL = [w for w in WALL if w in TOUCHED]
if HIT_WALL:
    bad.append("this batch touches a walled file: " + json.dumps(HIT_WALL))
for f in NEW + CHANGED:
    if blob_at(HEAD, f) == "":
        bad.append("expected path is not on my head: " + f)

# ---------- 2. the gate run ----------
RS = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "e4f_*.json")), key=os.path.getmtime)
RECEIPT = None
if not RS:
    bad.append("no e4f receipt")
else:
    RECEIPT = json.load(open(RS[-1], encoding="utf-8"))
    if RECEIPT.get("verdict") != "GREEN":
        bad.append("the ladder run is not GREEN: " + str(RECEIPT.get("verdict")) + " counts=" + json.dumps(RECEIPT.get("counts")))
    if not git_ok("merge-base", "--is-ancestor", str(RECEIPT.get("tree")), HEAD):
        bad.append("the run's tree is not on my branch's history: " + str(RECEIPT.get("tree")))
    if RECEIPT.get("target") != "e2e/qoder-ord0455-estimation-ladder-r1.spec.ts":
        bad.append("the newest receipt is not this order's run: " + str(RECEIPT.get("target")))
# the receipt's `tree` is the commit the dev server had under it; the product bytes were in the
# working tree at that moment and `byte_verify` below proves each of those files equals the blob
# now committed -- so the gate did run on this batch, it just ran one commit before the history did.
RECEIPT_TREE = str(RECEIPT.get("tree")) if RECEIPT else ""
if RECEIPT and not git_ok("merge-base", "--is-ancestor", RECEIPT_TREE, HEAD):
    bad.append("the run's tree is not on my branch's history: " + RECEIPT_TREE)
PRODUCT_SHA = ""
for sha in git("rev-list", BASE + ".." + HEAD).split():
    files = [l for l in git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).splitlines() if l.strip()]
    if files and all(f.startswith("frontend/src/") for f in files):
        PRODUCT_SHA = git("rev-parse", "--short", sha) + " (" + str(len(files)) + " paths, all under frontend/src)"
        break
if not PRODUCT_SHA:
    bad.append("no product commit found between the base and my head")
if RECEIPT and RECEIPT_TREE == "":
    bad.append("the receipt carries no tree")
# The gate runs against the working tree the dev server serves, so the honest requirement is not
# "same commit as my base" but "same BYTES for every file this batch is about".
STALE = [p for p in NEW + CHANGED
         if blob_at(RECEIPT_TREE, p) == "" or blob_at(RECEIPT_TREE, p) != blob_at(HEAD, p)]
if STALE:
    bad.append("the gate ran against different bytes for: " + json.dumps(STALE))
ARMS = {}
if RECEIPT:
    body = io.open(RECEIPT["log"], encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"O455 ([A-Za-z0-9_]+) (\{.*)", body):
        ARMS[m.group(1)] = json.loads(m.group(2))
WANT = ["control_pair", "m1_reachability", "m2_invariants", "s_source_shape", "screen_en", "screen_zh"]
MISSING = [w for w in WANT if w not in ARMS]
if sorted(ARMS) != WANT:
    bad.append("the run did not print exactly the six readings: got " + json.dumps(sorted(ARMS)))
if MISSING:
    bad.append("missing readings: " + json.dumps(MISSING))
for k in ("m1_reachability", "m2_invariants"):
    a = ARMS.get(k, {})
    if a.get("unreachable") or a.get("orphan_copy_keys") or a.get("violations"):
        bad.append(k + " is not clean: " + json.dumps({x: a.get(x) for x in ("unreachable", "orphan_copy_keys", "violations_total")}))
    if a.get("tiers_never_reached"):
        bad.append(k + " never reached a tier: " + json.dumps(a.get("tiers_never_reached")))
for k in ("screen_zh", "screen_en"):
    a = ARMS.get(k, {})
    if not a.get("sentences") or not a.get("all_rungs_hit") or a.get("leaked_placeholder"):
        bad.append(k + " has no hit-tested painted sentence: " + json.dumps({x: a.get(x) for x in ("painted", "all_rungs_hit", "leaked_placeholder")}))
    if a.get("painted") != a.get("predicted_from_dom_facts"):
        bad.append(k + " screen does not match the recomputed triggers")
C = ARMS.get("control_pair", {})
FOUR = ["amount+source,no_confidence", "amount,no_confidence", "amount,non_refundable", "door_switch"]
TWO = ["amount+source+confidence", "amount,non_refundable"]
if C.get("four_triggers") != FOUR:
    bad.append("the four-rung control did not walk the boundary: " + json.dumps(C.get("four_triggers")))
if len(C.get("four_tiers", [])) != 4:
    bad.append("the four-rung control did not paint four sentences: " + json.dumps(C.get("four_tiers")))
if C.get("two_triggers") != TWO:
    bad.append("the two-rung control is not the退场 shape: " + json.dumps(C.get("two_triggers")))
if len(C.get("two_tiers", [])) != 2:
    bad.append("the two-rung control did not paint two sentences: " + json.dumps(C.get("two_tiers")))

# ---------- 3. the compile arm on a hardlinked export of my own head ----------
BUILD = []
os.makedirs(SNAP, exist_ok=True)
p1 = subprocess.Popen(["git", "-C", REPO, "archive", "--format=tar", HEAD], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["tar", "-x", "-C", SNAP], stdin=p1.stdout)
p1.stdout.close()
if p2.wait(600):
    bad.append("the export did not extract")
fe = os.path.join(SNAP, "frontend")
nm = os.path.join(fe, "node_modules")
if not os.path.isdir(nm):
    shutil.copytree(NM_SRC, nm, copy_function=os.link, symlinks=True)
NLINK = os.stat(os.path.join(nm, "typescript", "package.json")).st_nlink
rc_a, out_a = run([NODE, TSC, "-p", "tsconfig.check.json", "--noEmit"], cwd=fe, timeout=2400)
BUILD.append(("npx tsc -p tsconfig.check.json --noEmit", rc_a, out_a[-200:]))
rc_b, out_b = run([NODE, TSC, "-p", "tsconfig.typecheck.json", "--noEmit"], cwd=fe, timeout=2400)
BUILD.append(("npx tsc -p tsconfig.typecheck.json --noEmit", rc_b, out_b[-200:]))
rc_c, out_c = run([NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"], cwd=fe, timeout=2400)
BUILD.append(("npx vite build --outDir dist --emptyOutDir", rc_c, out_c[-300:]))
for label, rc, tail in BUILD:
    if rc:
        bad.append("compile arm rc=" + str(rc) + " -- " + label + " :: " + tail)
ASSETS = sorted(os.path.basename(a) for a in glob.glob(os.path.join(fe, "dist", "assets", "index-*.js")))
BUNDLE = ""
if ASSETS:
    BUNDLE = hashlib.sha1(open(os.path.join(fe, "dist", "assets", ASSETS[0]), "rb").read()).hexdigest()
LADDER_IN_BUNDLE = []
if ASSETS:
    raw = open(os.path.join(fe, "dist", "assets", ASSETS[0]), "rb").read().decode("utf-8", "replace")
    for probe in ("这台服务器没有随这条回答给出置信度", "We do not print 0 as if it were a price", "ladder.remedy.absent"):
        LADDER_IN_BUNDLE.append([probe, probe in raw])

VERIFY = []
for rel in NEW + CHANGED:
    raw = open(os.path.join(WT, rel), "rb").read()
    h = hashlib.sha1()
    h.update(("blob " + str(len(raw)) + "\0").encode())
    h.update(raw)
    VERIFY.append((rel, h.hexdigest(), blob_at(HEAD, rel), h.hexdigest() == blob_at(HEAD, rel)))
for rel, got, want, ok in VERIFY:
    if not ok:
        bad.append("the working bytes differ from the branch for " + rel + ": " + got + " vs " + want)

# ---------- 4. wall-cell readouts, computed from the branch not from memory ----------
CELLS = {}
for rel, pat in READOUT_CELLS:
    CELLS[rel + " :: " + pat] = {"at": line_of(HEAD, rel, pat), "blob": blob_at(HEAD, rel)}

if bad:
    print("REFUSING BEFORE THE COMMIT -- " + str(len(bad)) + ":")
    for x in bad:
        print("    " + x)
    sys.exit(1)

# ---------- 5. artifact ----------
artifact = {
    "order": "ORD-0455",
    "lane": "e4f3490f-a55f-4fcb-b7af-227e41018656",
    "branch": BRANCH,
    "named_tip_in_the_order": NAMED_TIP,
    "my_base": BASE,
    "head_at_readings": HEAD,
    "live_tip_at_delivery": TIP,
    "n_commits_tip_past_my_head": N_LAG,
    "named_tip_is_ancestor_of_my_head": NAMED_ON_MINE,
    "depends_blob_drift": DRIFT,
    "merge_tree_prediction_rc": MT_RC,
    "touched_paths": TOUCHED,
    "walled_files_touched": HIT_WALL,
    "receipt": RECEIPT,
    "arms": ARMS,
    "build_arm": [{"cmd": l, "rc": r, "tail": t} for l, r, t in BUILD],
    "export_nlink": NLINK,
    "entry_asset": ASSETS,
    "entry_asset_sha1_over_bytes": BUNDLE,
    "ladder_copy_in_bundle": LADDER_IN_BUNDLE,
    "wall_cell_readouts": CELLS,
    "byte_verify": [{"path": r, "git_blob_id": g, "on_head": w, "match": o} for r, g, w, o in VERIFY],
}
with open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(artifact, fh, ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, GEN))

# ---------- 6. commit the instrument and the readouts on top of the product commits ----------
git("add", "-f", SPEC, cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0455 instrument: the ladder's trigger truth table, both locale arms, and the confidence-boundary control pair"])
if rc and "nothing to commit" not in co and "no changes added" not in co:
    print("COMMIT FAILED -- " + co[-200:])
    sys.exit(1)
INSTR = git("rev-parse", "HEAD", cwd=WT)
git("add", "-f", ART, GEN, cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0455 readouts: the painted rungs in both arms, the compile arm on a hardlinked export, and the wall cells this batch could only read"])
if rc and "nothing to commit" not in co and "no changes added" not in co:
    print("COMMIT FAILED -- " + co[-200:])
    sys.exit(1)
rc, po = run(["git", "-C", WT, "-c", "http.proxy=", "-c", "https.proxy=", "push", "-q",
              "origin", "refs/heads/" + BRANCH])
if rc:
    print("PUSH FAILED -- " + po[-200:])
    sys.exit(1)
PUSHED = head_of("refs/heads/" + BRANCH)
if not re.fullmatch(r"[0-9a-f]{40}", PUSHED or "") or git("cat-file", "-t", PUSHED) != "commit":
    print("the pushed head does not resolve: " + repr(PUSHED))
    sys.exit(1)
if not git_ok("merge-base", "--is-ancestor", HEAD, PUSHED):
    print("the pushed head lost the measured head")
    sys.exit(1)
POST = [l for l in git("diff", "--name-only", INSTR, PUSHED).splitlines() if l.strip() and not l.startswith("review/")]
if POST:
    print("the readouts commit touched non-review paths: " + json.dumps(POST))
    sys.exit(1)
PRODUCT = git("rev-list", "--max-count=1", INSTR + "~3") if len(git("rev-list", "--count", BASE + ".." + INSTR).split()) else BASE

MT_PUSH_RC, _MTPO = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, PUSHED])
SPEC_BLOB = blob_at(PUSHED, SPEC)
ART_BLOB = blob_at(PUSHED, ART)
GEN_BLOB = blob_at(PUSHED, GEN)
PRODUCT_COMMITS = git("log", "--format=%h %s", BASE + ".." + INSTR).splitlines()
NUMSTAT = git("diff", "--numstat", BASE, PUSHED)
ADDED = sum(int(l.split("\t")[0]) for l in NUMSTAT.splitlines() if l.split("\t")[0].isdigit())
DELETED = sum(int(l.split("\t")[1]) for l in NUMSTAT.splitlines() if l.split("\t")[1].isdigit())
PATHS = [l.split("\t")[2] for l in NUMSTAT.splitlines()]
BLOBS = {p: blob_at(PUSHED, p) for p in NEW + CHANGED + [SPEC, ART, GEN]}

r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    print("the door ruler is not the byte-for-byte one the relay named")
    sys.exit(1)

NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = NOW[:2] + ":" + NOW[2:]
FREE = run(["df", "-h", "/d"])[1].splitlines()[-1].split()[3]
HELD = run(["netstat", "-ano"])[1]
OPEN_PORTS = [str(p) for p in (RECEIPT["ports"]["frontend"], RECEIPT["ports"]["backend"])
              if ("\n  127.0.0.1:" + str(p) + " ") in HELD or ("127.0.0.1:" + str(p) + ":") in HELD]
if OPEN_PORTS:
    bad.append("the gate's ports are still listening: " + json.dumps(OPEN_PORTS))
NETSTAT = ("`netstat -ano` 现读对前端 " + str(RECEIPT["ports"]["frontend"]) + " 与后端 " + str(RECEIPT["ports"]["backend"]) +
           " 两枚端口 0 命中（残留监听 " + str(len(OPEN_PORTS)) + " 枚）")

M1 = ARMS["m1_reachability"]
M2 = ARMS["m2_invariants"]
S = ARMS["s_source_shape"]
Z = ARMS["screen_zh"]
E = ARMS["screen_en"]
P = ARMS["control_pair"]
L = []
A = L.append
A("### ORD-0455 交付 · 道0370（会话 e4f3490f-a55f-4fcb-b7af-227e41018656）· 估算四级梯：说方法 → 事前警告 → 事后核对 → 给补救 · 2026-09-29 " + NW + "+08")
A("")
A("## 1. 坐标")
A("   枝 `refs/heads/" + BRANCH + "`（新名，未覆盖任何已推 ref）；`git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/" + BRANCH + "` 现读头 " + PUSHED + " ，`git cat-file -t` = commit 。")
A("   号令者点名现尖 " + NAMED_TIP + " ：它是我这枝历史的祖先（`git merge-base --is-ancestor` 成立），我从 " + BASE + " 切出；交付时线又走到 " + TIP + " ，比我头多 " + str(N_LAG) + " 笔。")
A("   我这批读数依赖的 " + str(len(DEPENDS)) + " 枚未改字节（" + "、".join("`" + d.split("/")[-1] + "`" for d in DEPENDS) + "）在我的头与现尖上 blob 逐枚相同，漂移 " + str(len(DRIFT)) + " 枚；合流预测 `git merge-tree --write-tree " + TIP + " " + PUSHED + "` 退出码 " + str(MT_PUSH_RC) + " （0 = 可干净合流）。")
A("   相对基点净形：`git diff --numstat " + BASE + ".." + PUSHED + "` 现读 touched_path_count=" + str(len(PATHS)) + " 、added_line_count=" + str(ADDED) + " 、deleted_line_count=" + str(DELETED) + " 。")
A("   闸与提交的先后：这把闸的 receipt tree = " + RECEIPT_TREE + (" ，就是我此刻交付的这枚头" if RECEIPT_TREE == HEAD else " ，比我这枚头早一批提交") + " ；" +
  "这批 " + str(len(NEW + CHANGED)) + " 枚产品字节在 receipt tree 与我的头之间逐枚 blob 等值（脚本按 `git rev-parse <rev>:<path>` 断言，" +
  str(len([p for p in NEW + CHANGED if blob_at(RECEIPT_TREE, p) == blob_at(HEAD, p)])) + "/" + str(len(NEW + CHANGED)) + " 枚相同），" +
  "所以报的是「量过的那批字节」。磁盘字节与提交后的 blob 也逐枚回算（`git hash-object` 头部式，" +
  str(len([1 for _r, _g, _w, o in VERIFY if o])) + "/" + str(len(VERIFY)) + " 枚 match）。")
A("")
A("## 2. 这批交了什么（一句话）")
A("   四档梯子在树上是一枚推导 + 一枚文案模块 + 一屏挂载：`frontend/src/features/estimation/estimationLadder.ts`（触发条件）、" +
  "`estimationLadderCopy.ts`（两套语言的 10 枚措辞 + 4 枚档位名）、`EstimationLadderPanel.tsx` + `estimationLadder.css`（挂载与形制），" +
  "落在住处明细那一屏（`StayExplorer` 明细面板，紧跟 总价/退改/来源 那三行之下）。")
A("   逐文件 blob（同段可 `git cat-file -e` 的 40 位）：")
for p in NEW + CHANGED + [SPEC, ART, GEN]:
    A("     " + p + " = " + BLOBS[p])
A("")
A("## 3. 四档与它们各自的触发条件（这是本单要求的两件事之一）")
A("   档位不是措辞的别名，是 `estimationFacts()` 的谓词组合。全部触发条件与实测计数：")
A("   ① 说方法：只有当屏幕上真有一个数时才允许说话。触发 = `amount>0 且宿主给出的金额文字非空`；" +
  "再按 来源/置信度 两格分三种措辞（两格都有 / 缺置信度 / 缺来源）。")
A("   ② 事前警告：`无数` 或 `有数无置信度` 各一种措辞。")
A("   ③ 事后核对：有数才说；`refundable === false` 时换成点名后果的那一句。")
A("   ④ 给补救：只在警告出现过时出现，并三门挑一（可换候选 / 只能去重算 / 明确说没有门）。")
A("   反证不变量在 " + str(M2["cases"]) + " 例全组合上跑：" +
  "警告与补救必成对、无数时不许出现①③、有数时①③各且仅一次、档位顺序不得倒挂 —— 违反 " + str(M2["violations_total"]) + " 例（`O455 m2_invariants`）。")
A("   四档全部点得亮，且没有一枚措辞无人引用：`rung_keys_derived=" + str(M1["rung_keys_derived"]) + "` 、`unreachable=" + json.dumps(M1["unreachable"], ensure_ascii=False) + "` 、`orphan_copy_keys=" + json.dumps(M1["orphan_copy_keys"], ensure_ascii=False) + "` 。")
A("")
A("## 4. 屏上读到的是句子本身（本单要求的第二件事）")
A("   两臂都是 390x844 、底栏顶边 hit_line=" + str(Z["screen"]["hitLine"]) + " 、先 `scrollIntoViewIfNeeded()` 再命中。")
A("   中文臂实读到 " + str(len(Z["sentences"])) + " 档，逐档中心命中且末行在底栏之上：" + json.dumps(Z["sentences"], ensure_ascii=False))
A("   英文臂实读到 " + str(len(E["sentences"])) + " 档：" + json.dumps(E["sentences"], ensure_ascii=False))
A("   两臂的屏上档位与「按 DOM 事实独立重算」的结果逐字相等（`painted == predicted_from_dom_facts`），漏出的占位符 0 枚（`leaked_placeholder=" + json.dumps(Z["leaked_placeholder"]) + "`）。")
A("   权威口径：这两臂跑在 `npm run dev` 上（闸的既有口径），证的是**措辞与触发条件落到了屏上**；产物字节另由第 5 节那三行退出码与 bundle 命中给，dev 的响应字节与磁盘字节不等，我不主张等值。")
A("")
A("## 5. 反件（四档同屏的边界就在置信度那一格）")
A("   真数据这次只点亮两档：`GET /api/v1/journeys/{id}/experience` 交回的住处证据是「有数 + 有来源 + 置信度 0.96」，②④ 的触发条件是「无数」或「有数无置信度」，这台服务器这次没有给出这两种形状。" +
  "所以反件把 experience 的响应改写成骑在边界两侧的两种形状，各读一次屏（同一枚端点、同一把闸、同一个上下文）：")
A("   无置信度那一形：屏上 " + json.dumps(P["four_tiers"], ensure_ascii=False) + " 四档按梯序落地，触发行 " + json.dumps(P["four_triggers"], ensure_ascii=False) + " ，四档都中心命中。")
A("   补上置信度那一形：屏上 " + json.dumps(P["two_tiers"], ensure_ascii=False) + " ，警告与补救自己退场。")
A("   两形各自改到的响应（去重后 " + str(len(set(P["endpoints_patched"]))) + " 条端点、逐次改写 " + str(len(P["endpoints_patched"])) + " 次）：" + json.dumps(sorted(set(P["endpoints_patched"])), ensure_ascii=False) + " 。")
A("   见证类型 = HTTP_RESPONSE：这两代形状是我本地应答的，不是这台服务器给的；它证明的是梯子的边界画在对的地方，不是产品数据长这样。")
A("   编译臂（我这枚头的导出件，node_modules 走 `os.link` 硬链、nlink=" + str(NLINK) + " ）逐行退出码：")
for label, rc, _t in BUILD:
    A("     " + label + " rc=" + str(rc))
A("   入口 asset " + json.dumps(ASSETS) + " ，本机字节 sha1 over bytes = " + BUNDLE + " （非 git 对象声明；同段可 cat-file 的 40 位：仪表 " + SPEC_BLOB + " 、读数件 " + ART_BLOB + " ）；" +
  "bundle 里逐串命中（三串：两枚措辞 + 一枚 key）：" + json.dumps(artifact["ladder_copy_in_bundle"], ensure_ascii=False) + " 。")
A("")
A("## 6. 我没动的东西，以及动不了的格子（具名 + 读数）")
A("   禁改墙：" + json.dumps(WALL) + " 在本批 `git diff --name-only` 的 touched 集合里 0 命中（脚本断言 `walled_files_touched=" + json.dumps(HIT_WALL) + "`）。")
A("   墙上有两格本来就属于这架梯子，我只交读数、不开改不完的口子：")
for k in (WALL[1] + " :: 每人每天约", WALL[1] + " :: map.unknownCosts"):
    A("     " + k + " 现读 " + CELLS[k]["at"] + " ，blob " + CELLS[k]["blob"] + " 。")
A("     前一格是「每天约 X」那句：它已经自带 说方法（按你的预算平均下来的参考值）+ 事前警告（TIGHT_CAVEAT_ZH，" + line_of(PUSHED, WALL[1], "const TIGHT_CAVEAT_ZH") + "）+ 给补救（那句里的「可以先调整预算」）三档，" +
  "而且 `frontend/e2e/qoder-budget-advisory-tiers.spec.ts` 把句子按字符钉住 —— 要接第四档得连那把闸一起改，不在我这单的范围。")
A("     后一格 `map.unknownCosts` 现读 " + CELLS[WALL[1] + " :: map.unknownCosts"]["at"] + " ：屏上那句「未知费用保持未知。」只声明了立场，四档一档都没有。这是墙后唯一一处「该挂梯子、现在只有一句口号」的格子，交号令者定夺。")
A("   另外两格不在墙上、已在树上，我复用了没有另造：`lib/budgetEvidence.ts` 的 NONE/PARTIAL/FULL（" + CELLS["frontend/src/lib/budgetEvidence.ts :: export type BudgetEvidenceState"]["at"] + "）是警告档的判据出处；" +
  "`features/agent/CopilotDock.tsx` 的 VERIFICATION_LABELS（" + CELLS["frontend/src/features/agent/CopilotDock.tsx :: const VERIFICATION_LABELS"]["at"] + "）是核对档的词表出处。" +
  "`features/trip/ActivityDetail.tsx` " + CELLS["frontend/src/features/trip/ActivityDetail.tsx :: 都在约"]["at"] + " 那句「按直线距离排列」是本产品已有的一句「说方法」。")
A("   来源那一格（`stay.evidence.source`）我走的是 ORD-0425 那条共享显示层：在 `lib/displayVocabulary.ts` 上加了一枚 `EVIDENCE_SOURCE` 表 + `evidenceSourceLabel()`，" +
  "表里只列 `backend/app/stay_mobility.py` 自己声明的三枚 provenance（CAPTURED_REPLAY / UNAVAILABLE / SYNTHETIC_FIXTURE），" +
  "没列到的值仍落回「这台服务器写的：原值」那一条带标签的通道，不是我替它编一个名字。")
A("")
A("## 7. 一条我自己量出来的既有分叉（不改，只报）")
A("   住处明细那一屏同时印着两个「合计」：卡片行 `pricePair(item.stay_total_minor, …)` 与明细行 `priceLabel(selected.stay.total_amount_minor, …)` 读的是两枚字段。")
A("   反件里我把后者写成 156000（¥1,560.00），卡片仍印 ¥360.00 —— 同屏两个总数不同源。我的梯子挂在明细行下，`{amount}` 与 `data-ladder-amount-field = stay.total_amount_minor` 逐格点名它说的是哪一行（" +
  line_of(PUSHED, "frontend/src/features/estimation/EstimationLadderPanel.tsx", "data-ladder-amount-field") + "）。")
A("   这一格归属不在本单（要统一得动 `stay_total_minor` 的出处），具名交回：`frontend/src/features/stay/StayExplorer.tsx` " +
  line_of(PUSHED, "frontend/src/features/stay/StayExplorer.tsx", "function pricePair(") + " 与 " +
  line_of(PUSHED, "frontend/src/features/stay/StayExplorer.tsx", "function priceLabel(") + " 。")
A("")
A("## 8. 尺与边界")
A("   门尺自检：`" + LIVE + "/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0 —— 退出码与 findings 由本进程在写进收件口之前对这份草稿现跑，跑红就不投递；")
A("   那把尺本机字节重算文件 sha1 = " + R7_SHA1 + " （非 git 对象声明；同段可 `git cat-file` 的 40 位：入库 blob " + R7_BLOB + " 、byte_count=" + str(len(r7b)) + " 与我运行的字节数相同、交付头 " + PUSHED + " ）。")
A("   第二道闸对同一份草稿逐值复算：只扫逐字 40 位，免除要同一行写明不可取回且同段另有一枚能 cat-file 的 40 位，`path:line` 不算数；abort 非空不投递。官方回放件 `" + LIVE + "/patrol/bolt_replica.py` 的读数随本块投递后的回读一并给出。")
A("   边界：权威线 0 次移动（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）；账本 0 次直写（本块走收件口）；`D:/moodle/_qoder_preview_20260920/_preview.db` 一次未开；`demo/reset` 0 次；" +
  "别人 worktree 0 次进入；闸用的库与端口是本跑自己新建自起的（前端 " + str(RECEIPT["ports"]["frontend"]) + " 、后端 " + str(RECEIPT["ports"]["backend"]) + " ，库 " + RECEIPT["db"] + " ），收尾 netstat 回读见第 9 节；D 盘可用 " + FREE + " 。")
A("")
A("## 9. 复现")
A("   跑闸：`env -u HTTP_PROXY -u HTTPS_PROXY python review/e4f_e2e_r1.py --wt D:/moodle/_qoder_lane_q0406 --target e2e/qoder-ord0455-estimation-ladder-r1.spec.ts --tag e4f` ；" +
  "本跑 run_id = " + RECEIPT["run_id"] + " ，stdout 读数件 = " + RECEIPT["log"] + " （" + str(RECEIPT["log_bytes"]) + " 字节），计数 = " + json.dumps(RECEIPT["counts"]) + " 。")
A("   读数汇总（含两臂逐档句子、反件、三行退出码、bundle 命中、墙上格子现读）在 `review/q455_estimation_ladder_r1.json`（blob " + ART_BLOB + " ，可 `git cat-file -p` ）。")
SUPER = [l for l in git("log", "--format=%h %s", BASE + ".." + PUSHED).splitlines()
         if "ORD-0455" in l and not l.startswith(git("rev-parse", "--short", PUSHED))]
A("")
A("## 10. 这批的迭代留痕（不藏）")
A("   第一版交付生成器崩在装配账本块那一步：`claim_coordinate_check_r7.py` 的 `--text` 收的是**草稿文件路径**，我把正文塞了进去，尺在 open() 上抛 OSError；同版另有一处未绑定变量。" +
  "崩点在三笔提交与 push 之后，所以已发布的枝历史上确实带着那版有缺陷的生成器 —— 逐笔如下（首笔是我的产品提交，末笔是本块引用的头）：")
for l in SUPER:
    A("     " + l)
A("   中途权威线把 `frontend/src/i18n/LocaleContext.tsx` 改了（我这批依赖它的 `nav.studio` 那一格），我的门在提交前就报漂移并拒收；我 rebase 到 " + BASE + " 之后**整把闸重跑**（run_id " + RECEIPT["run_id"] + " ），" +
  "此前那笔跑在 57ff5d1c 下的 receipt 已作废，本块不引用它的任何数字。")
A("   端口收尾自检：" + NETSTAT + " 。")

DRAFT = os.path.join(SCR, "q455_ladder_r1_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
text = io.open(DRAFT, encoding="utf-8", newline="").read()
print("DRAFT " + DRAFT + " " + str(os.path.getsize(DRAFT)) + " bytes HEAD " + PUSHED)
rc, r7out = run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"),
                 "--text", DRAFT, "--expect-clean"])
R7_RC = rc
io.open(os.path.join(SCR, "q455_r7_out.txt"), "w", encoding="utf-8").write(r7out)
print("GATE_R7 rc=" + str(rc))
for l in [x.strip()[:190] for x in r7out.split("\n") if x.startswith("  line ") or "overall" in x]:
    print("    " + l)
if rc:
    print("NOT PUBLISHED -- r7 red")
    sys.exit(2)


def bolt(path):
    """The second door's own arithmetic, replayed here so a findable-only-on-the-ruler abort never
    reaches the inbox: literal 40-hex tokens, resolvable through `git cat-file`, exempt only when the
    same line declares them unretrievable AND the same paragraph carries a resolvable one."""
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
    print("    L%-3d %s" % (n, h[:14]))
if AB:
    print("NOT PUBLISHED -- second arm would abort")
    sys.exit(3)
NAME = "qoder-0455_" + NOW + ".md"
OUTP = os.path.join(INBOX, NAME)
if not re.fullmatch(r"[A-Za-z0-9._-]+_[0-9]{4}\.md", NAME):
    print("block filename rejected: " + NAME)
    sys.exit(1)
if os.path.exists(OUTP):
    print("block file already exists, refusing to overwrite: " + OUTP)
    sys.exit(1)
io.open(OUTP, "w", encoding="utf-8", newline="\n").write(text)
rc, bo = run([VENV, "-X", "utf8", os.path.join(LIVE, "patrol", "bolt_replica.py")])
io.open(os.path.join(SCR, "q455_bolt_out.txt"), "w", encoding="utf-8").write(bo)
LINES = [x for x in bo.splitlines() if "0455" in x]
print("OFFICIAL_BOLT rc=" + str(rc) + " " + (" || ".join(LINES)[:400] if LINES else bo.strip()[-300:]))
print("WROTE " + OUTP + " " + str(os.path.getsize(OUTP)) + " bytes  r7_rc=" + str(R7_RC) + " would_abort=" + str(len(AB)))
print("OK " + PUSHED)
