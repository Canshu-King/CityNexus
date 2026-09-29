#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORD-0468 delivery: the ladder's named empty reading, plus the r2 succession of ORD-0455's gate.

Same order of operations as every other block from this lane: every refusal is evaluated and printed
before the first commit, the coordinates are read back out of the remote after the push, and the two
doors run against the draft before it is allowed into the inbox.
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
SNAP = r"D:/moodle/_qoder_lane_0468_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
NODE = r"C:/Program Files/nodejs/node.exe"
TSC = os.path.join(NM_SRC, "typescript", "bin", "tsc")
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BRANCH = "review/Q-ord0468-ladder-empty-reading-r1"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
SPEC = "frontend/e2e/qoder-ord0468-ladder-empty-reading-r1.spec.ts"
SPEC_R2 = "frontend/e2e/qoder-ord0455-estimation-ladder-r2.spec.ts"
SPEC_R1 = "frontend/e2e/qoder-ord0455-estimation-ladder-r1.spec.ts"
ART = "review/q468_ladder_empty_r1.json"
GEN = "review/q468_empty_r1.py"
RUNNER = "review/e4f_e2e_r1.py"
PRODUCT = [
    "frontend/src/features/estimation/estimationLadder.ts",
    "frontend/src/features/estimation/estimationLadderCopy.ts",
    "frontend/src/features/estimation/EstimationLadderPanel.tsx",
    "frontend/src/features/stay/StayExplorer.tsx",
]
WALL = ["frontend/src/styles.css", "frontend/src/app/V8Experience.tsx"]
DEPENDS = ["frontend/src/i18n/LocaleContext.tsx", "frontend/e2e/_qoderShellSeed.ts", "frontend/e2e/_qoderEvidence.ts"]
EMPTY_KEY = "ladder.method.noCandidates"
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


# ---------- 1. line state ----------
TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
if not re.fullmatch(r"[0-9a-f]{40}", TIP or ""):
    bad.append("the live tip did not read back: " + repr(TIP))
HEAD = git("rev-parse", "HEAD", cwd=WT)
BASE = git("merge-base", TIP, HEAD) if TIP else ""
N_LAG = int(git("rev-list", "--count", HEAD + ".." + TIP) or 0) if TIP else -1
DRIFT = [f for f in DEPENDS if blob_at(HEAD, f) and blob_at(TIP, f) and blob_at(HEAD, f) != blob_at(TIP, f)]
if DRIFT:
    bad.append("bytes my readings depend on moved past my head: " + json.dumps(DRIFT))

# ---------- 2. both receipts ----------
def newest(target):
    # The runner records the target relative to `frontend/`, e.g. `e2e/<spec>` -- comparing it to a
    # repo-root path silently matched nothing and every check below cascaded from that.
    want = "e2e/" + os.path.basename(target)
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "e4f_*.json")), key=os.path.getmtime)
    for f in reversed(fs):
        d = json.load(open(f, encoding="utf-8"))
        if d.get("target") == want:
            return d
    return None


R0468 = newest(SPEC)
R2 = newest(SPEC_R2)
for label, r in (("0468", R0468), ("0455-r2", R2)):
    if not r:
        bad.append("no receipt for the " + label + " run")
        continue
    if r.get("verdict") != "GREEN":
        bad.append(label + " run is not GREEN: " + str(r.get("verdict")) + " " + json.dumps(r.get("counts")))
    if not git_ok("merge-base", "--is-ancestor", str(r.get("tree")), HEAD):
        bad.append(label + " run's tree is not on my history: " + str(r.get("tree")))
TREE468 = str(R0468.get("tree")) if R0468 else ""
STALE = [p for p in PRODUCT + [SPEC, SPEC_R2] if blob_at(TREE468, p) == "" or blob_at(TREE468, p) != blob_at(HEAD, p)]
if STALE:
    bad.append("the gate ran against different bytes for: " + json.dumps(STALE))


def arms(receipt, tag):
    body = io.open(receipt["log"], encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(tag + r" ([A-Za-z0-9_]+) (\{.*)", body):
        out[m.group(1)] = json.loads(m.group(2))
    return out


A468 = arms(R0468, "O468") if R0468 else {}
A455 = arms(R2, "O455") if R2 else {}
WANT468 = ["cell_2_pair", "cell_four_en", "cell_four_zh", "m_derivation", "product_bytes_state", "s_source_shape"]
WANT455 = ["control_pair", "m1_reachability", "m2_invariants", "s_source_shape", "screen_en", "screen_zh"]
if sorted(A468) != WANT468:
    bad.append("the 0468 run did not print exactly its six readings: " + json.dumps(sorted(A468)))
if sorted(A455) != WANT455:
    bad.append("the 0455-r2 run did not print exactly its six readings: " + json.dumps(sorted(A455)))

M = A468.get("m_derivation", {})
S = A468.get("s_source_shape", {})
PB = A468.get("product_bytes_state", {})
Z = A468.get("cell_four_zh", {})
E = A468.get("cell_four_en", {})
PAIR = A468.get("cell_2_pair", {}).get("cell_2_before_after", {})
M1 = A455.get("m1_reachability", {})
M2 = A455.get("m2_invariants", {})

if M.get("empty_tiers") != ["method"] or M.get("empty_rungs", [[]])[0][:3] != ["method", EMPTY_KEY, "no_candidates"]:
    bad.append("the empty shape is not the single named rung: " + json.dumps(M.get("empty_rungs")))
if not M.get("empty_has_no_digit") or not M.get("empty_has_no_placeholder"):
    bad.append("the empty reading carries a digit or a placeholder: " + json.dumps(M))
if not M.get("explicit_one_same_as_omitted") or not M.get("keys_also_identical"):
    bad.append("omitting `candidates` changed what ORD-0455's hosts answer")
for k in ("empty_branch_mounts_ladder", "detail_branch_still_mounts_ladder"):
    if S.get(k) != 1:
        bad.append(k + " is not exactly one mount: " + str(S.get(k)))
if S.get("empty_key_in_shared_dictionary") or S.get("classes_added_to_walled_css") or S.get("logic_code_has_cjk"):
    bad.append("the source shape guards moved: " + json.dumps({x: S.get(x) for x in ("empty_key_in_shared_dictionary", "classes_added_to_walled_css", "logic_code_has_cjk")}))
if PB.get("offer_cards", 0) <= 0 or not PB.get("ladder_present"):
    bad.append("the product-bytes arm did not read a populated stay screen: " + json.dumps(PB))
for cell in (Z, E):
    c1, c2, c3, c4 = (cell.get("cell_1_target_row"), cell.get("cell_2_count_moves"),
                      cell.get("cell_3_against_bottom_bar"), cell.get("cell_4_machine_tokens"))
    if not (c1 and c1.get("ladder_present") and c1.get("denominator_result_cards_on_screen") == 0
            and c1.get("empty_state_sentence_still_there")):
        bad.append("cell 1 not met: " + json.dumps(c1))
    if not (c2 and c2.get("tiers_here") == ["method"] and c2.get("digits_in_empty_reading") == []
            and c2.get("placeholder_leaks") == []):
        bad.append("cell 2 not met: " + json.dumps(c2))
    if not (c3 and c3.get("every_row_centre_hit") and c3.get("every_row_clears_nav")
            and isinstance(c3.get("hit_line_px_measured_on_this_box"), int)):
        bad.append("cell 3 not met: " + json.dumps(c3))
    if not (c4 and c4.get("token_count") == 0):
        bad.append("cell 4 not met: " + json.dumps(c4))
if not (PAIR.get("before_cards", 0) > 0 and PAIR.get("after_cards") == 0 and PAIR.get("changed")
        and PAIR.get("after_keys") == [EMPTY_KEY] and EMPTY_KEY not in PAIR.get("before_keys", [])):
    bad.append("the before/after pair did not discriminate: " + json.dumps(PAIR))
if M1.get("copy_rungs_never_derived") or M1.get("derived_without_copy") or M1.get("unreachable"):
    bad.append("r2's reachability set does not close: " + json.dumps({k: M1.get(k) for k in ("copy_rungs_never_derived", "derived_without_copy", "unreachable")}))
if M2.get("violations_total") != 0 or M2.get("tiers_never_reached"):
    bad.append("r2's invariant sweep is not clean: " + json.dumps({k: M2.get(k) for k in ("violations_total", "tiers_never_reached")}))

# ---------- 3. compile arm on a hardlinked export ----------
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
for label, cmd in (("npx tsc -p tsconfig.check.json --noEmit", [NODE, TSC, "-p", "tsconfig.check.json", "--noEmit"]),
                   ("npx tsc -p tsconfig.typecheck.json --noEmit", [NODE, TSC, "-p", "tsconfig.typecheck.json", "--noEmit"]),
                   ("npx vite build --outDir dist --emptyOutDir", [NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"])):
    rc, out = run(cmd, cwd=fe, timeout=2400)
    BUILD.append((label, rc, out[-200:]))
    if rc:
        bad.append("compile arm rc=" + str(rc) + " -- " + label + " :: " + out[-200:])
ASSETS = sorted(os.path.basename(a) for a in glob.glob(os.path.join(fe, "dist", "assets", "index-*.js")))
BUNDLE = ""
BUNDLE_HITS = []
if ASSETS:
    raw = open(os.path.join(fe, "dist", "assets", ASSETS[0]), "rb").read()
    BUNDLE = hashlib.sha1(raw).hexdigest()
    text = raw.decode("utf-8", "replace")
    for probe in ("这一级没有可报的方法", "There is no method to report at this rung", EMPTY_KEY):
        BUNDLE_HITS.append([probe, probe in text])

VERIFY = []
for rel in PRODUCT + [SPEC, SPEC_R2]:
    raw = open(os.path.join(WT, rel), "rb").read()
    h = hashlib.sha1()
    h.update(("blob " + str(len(raw)) + "\0").encode())
    h.update(raw)
    want = blob_at(HEAD, rel)
    VERIFY.append((rel, h.hexdigest(), want, h.hexdigest() == want))
for rel, got, want, ok in VERIFY:
    if not ok:
        bad.append("the working bytes differ from the branch for " + rel + ": " + got + " vs " + want)

TOUCHED = [l for l in git("diff", "--name-only", BASE, HEAD, cwd=REPO).splitlines() if l.strip()]
HIT_WALL = [w for w in WALL if w in TOUCHED]
if HIT_WALL:
    bad.append("this batch touches a walled file: " + json.dumps(HIT_WALL))
R1_HEAD = head_of("refs/heads/review/Q-ord0455-estimation-ladder-r1")
R1_RED_CAUSE = blob_at(R1_HEAD, "frontend/src/features/estimation/estimationLadderCopy.ts") != blob_at(HEAD, "frontend/src/features/estimation/estimationLadderCopy.ts")

# ---------- 4. refuse before anything is written ----------
if bad:
    print("REFUSING BEFORE THE COMMIT -- " + str(len(bad)) + ":")
    for x in bad:
        print("    " + x)
    sys.exit(1)

artifact = {
    "order": "ORD-0468",
    "lane": "e4f3490f-a55f-4fcb-b7af-227e41018656",
    "branch": BRANCH,
    "base": BASE,
    "head_at_readings": HEAD,
    "live_tip_at_delivery": TIP,
    "n_commits_tip_past_my_head": N_LAG,
    "depends_blob_drift": DRIFT,
    "receipt_0468": R0468,
    "receipt_0455_r2": R2,
    "arms_0468": A468,
    "arms_0455_r2": A455,
    "build_arm": [{"cmd": l, "rc": r, "tail": t} for l, r, t in BUILD],
    "export_nlink": NLINK,
    "entry_asset": ASSETS,
    "entry_asset_sha1_over_bytes": BUNDLE,
    "empty_copy_in_bundle": BUNDLE_HITS,
    "byte_verify": [{"path": r, "git_blob_id": g, "on_head": w, "match": o} for r, g, w, o in VERIFY],
    "touched_paths": TOUCHED,
    "walled_files_touched": HIT_WALL,
    "succession": {
        "published_r1_head": R1_HEAD,
        "r1_M1_reddened_by_this_batch": bool(R1_RED_CAUSE),
        "r1_blob_of_copy_module": blob_at(R1_HEAD, "frontend/src/features/estimation/estimationLadderCopy.ts"),
        "r2_blob_of_copy_module": blob_at(HEAD, "frontend/src/features/estimation/estimationLadderCopy.ts"),
    },
}
with open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(artifact, fh, ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, GEN))

COMITS = []
git("add", "-f", SPEC, SPEC_R2, cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0468 instrument: the four cells on the empty stay screen, and ORD-0455's gate re-cut as r2 with a computed denominator"])
if rc and not any(x in co for x in ("nothing to commit", "nothing added to commit", "no changes added")):
    print("COMMIT FAILED -- " + co[-200:])
    sys.exit(1)
COMITS.append(git("rev-parse", "HEAD", cwd=WT))
INSTR = git("rev-parse", "HEAD", cwd=WT)
git("add", "-f", ART, GEN, cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0468 readouts: the named empty rung in both languages, the before/after pair, and the compile arm on a hardlinked export"])
if rc and not any(x in co for x in ("nothing to commit", "nothing added to commit", "no changes added")):
    print("COMMIT FAILED -- " + co[-200:])
    sys.exit(1)
COMITS.append(git("rev-parse", "HEAD", cwd=WT))
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

MT_PUSH_RC, _o = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, PUSHED])
SPEC_BLOB = blob_at(PUSHED, SPEC)
SPEC_R2_BLOB = blob_at(PUSHED, SPEC_R2)
ART_BLOB = blob_at(PUSHED, ART)
GEN_BLOB = blob_at(PUSHED, GEN)
NUMSTAT = git("diff", "--numstat", BASE, PUSHED)
ADDED = sum(int(l.split("\t")[0]) for l in NUMSTAT.splitlines() if l.split("\t")[0].isdigit())
DELETED = sum(int(l.split("\t")[1]) for l in NUMSTAT.splitlines() if l.split("\t")[1].isdigit())
PATHS = [l.split("\t")[2] for l in NUMSTAT.splitlines()]
BLOBS = {p: blob_at(PUSHED, p) for p in PRODUCT + [SPEC, SPEC_R2, ART, GEN]}
PANEL = "frontend/src/features/estimation/EstimationLadderPanel.tsx"
COORD = {
    "empty_case": line_of(PUSHED, SPEC, '{ key: "ladder.method.noCandidates"') or line_of(PUSHED, SPEC, "reading({ candidates: 0 })"),
    "mount": line_of(PUSHED, PRODUCT[3], "<EstimationLadderPanel"),
    "branch": line_of(PUSHED, PRODUCT[0], "if (!facts.has_candidates)"),
    "viewport": line_of(PUSHED, SPEC, "width: 390, height: 844"),
    "hit_probe": line_of(PUSHED, SPEC, "const nav = document.querySelector"),
    "cells": line_of(PUSHED, SPEC, "const fourCells = "),
    "pair": line_of(PUSHED, SPEC, "cell_2_before_after"),
    "emptier": line_of(PUSHED, SPEC, "options 4->0") or line_of(PUSHED, SPEC, '"options"'),
    "r2_reach": line_of(PUSHED, SPEC_R2, "ladder.method.noCandidates"),
    "r2_cases": line_of(PUSHED, SPEC_R2, "for (const candidates of"),
    "empty_copy": line_of(PUSHED, PRODUCT[1], EMPTY_KEY),
}
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    print("the door ruler is not the byte-for-byte one the relay named")
    sys.exit(1)
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = NOW[:2] + ":" + NOW[2:]
FREE = run(["df", "-h", "/d"])[1].splitlines()[-1].split()[3]
HELD = run(["netstat", "-ano"])[1]
OPEN_PORTS = [str(p) for p in (R0468["ports"]["frontend"], R0468["ports"]["backend"])
              if ("127.0.0.1:" + str(p) + ":") in HELD]
if OPEN_PORTS:
    print("the gate's ports are still listening: " + json.dumps(OPEN_PORTS))
    sys.exit(1)
NETSTAT = ("`netstat -ano` 现读对前端 " + str(R0468["ports"]["frontend"]) + " 与后端 " + str(R0468["ports"]["backend"]) + " 两枚端口 0 命中")
ROWS = Z["cell_3_against_bottom_bar"]["rows"]

L = []
A = L.append
A("### ORD-0468 交付 · 道0370（会话 e4f3490f-a55f-4fcb-b7af-227e41018656）· 空态给四级梯一枚具名空读数 + ORD-0455 那把闸改写成 r2 · 2026-09-30 " + NW + "+08")
A("")
A("## 1. 坐标")
A("   枝 `refs/heads/" + BRANCH + "`（新名）；`git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/" + BRANCH + "` 现读头 " + PUSHED + " ，`git cat-file -t` = commit 。")
A("   我这枝从 " + BASE + " 切出；交件这一秒线又走到 " + TIP + " ，比我头多 " + str(N_LAG) + " 笔；合流预测 `git merge-tree --write-tree " + TIP + " " + PUSHED + "` 退出码 " + str(MT_PUSH_RC) + " 。")
A("   我依赖的 " + str(len(DEPENDS)) + " 枚未改字节（" + "、".join("`" + d.split("/")[-1] + "`" for d in DEPENDS) + "）在我的头与现尖上逐枚 blob 相同，漂移 " + str(len(DRIFT)) + " 枚。")
A("   净形 `git diff --numstat " + BASE + ".." + PUSHED + "` ：touched_path_count=" + str(len(PATHS)) + " 、added_line_count=" + str(ADDED) + " 、deleted_line_count=" + str(DELETED) + " 。")
A("   逐文件 blob（同段可 `git cat-file -e`）：")
for p in PRODUCT + [SPEC, SPEC_R2, ART, GEN]:
    A("     " + p + " = " + BLOBS[p])
A("")
A("## 2. 落了什么")
A("   判据一处（取字处 " + COORD["branch"] + "）：`estimationFacts` 多一枚 `has_candidates`，推导在最前面认它 —— 没有候选时**只**亮 `ladder.method.noCandidates` 这一枚，" +
  "不亮警告/核对/补救，也不许别的形状点亮它。挂载两处（" + COORD["mount"] + " 在早退分支里，明细那一屏的挂载原位不动）。")
A("   措辞 " + COORD["empty_copy"] + " ：zh「" + M.get("empty_zh_painted", "") + "」／en「" + M.get("empty_en_painted", "") + "」。")
A("   三条边界照单守住：共享字典 0 长（`empty_key_in_shared_dictionary=" + json.dumps(S.get("empty_key_in_shared_dictionary")) + "`）；" +
  "禁改墙 0 字节（`walled_files_touched=" + json.dumps(HIT_WALL) + "`）；那枚空读数里**一个数字都没有**（`digits_in_empty_reading=[]`），因为「0 家候选」会被读成一次测量，" +
  "而这台服务器这次根本没交回候选。补救没有重造 —— 空态原有那句「可以先选好行程，再回来搜索住宿」（" + COORD["mount"] + " 同分支内）就是那一档的出处。")
A("")
A("## 3. `/v8/stay` 空态那一屏的屏上四格（号令者 06:44 的形制，逐格实测）")
A("   取字与判据都在 " + COORD["cells"] + " ，视口与命中带读法在 " + COORD["viewport"] + " / " + COORD["hit_probe"] + " 。")
A("   格① 目标条出现与否 + 分母：`estimation-ladder` 出现 = " + json.dumps(Z["cell_1_target_row"]["ladder_present"]) + " ；屏上 `stay-offer-card` 枚数 = " +
  str(Z["cell_1_target_row"]["denominator_result_cards_on_screen"]) + " （分母）；`stay-no-options` 那句仍在 = " +
  json.dumps(Z["cell_1_target_row"]["empty_state_sentence_still_there"]) + " ；整屏正文 innerText 长度 = " + str(Z["screen"]["body_chars"]) + " 字。")
A("   格② 计数随交互变（同一台机、同一把闸、前后各一枚读数，取字处 " + COORD["pair"] + " ）：抹掉候选之前 cards=" + str(PAIR.get("before_cards")) +
  " 亮 " + json.dumps(PAIR.get("before_keys"), ensure_ascii=False) + " 两枚；之后 cards=" + str(PAIR.get("after_cards")) + " 亮 " +
  json.dumps(PAIR.get("after_keys"), ensure_ascii=False) + " 一枚；`changed=" + json.dumps(PAIR.get("changed")) + "` ，且空读数那枚 key 在有候选时不出现。" +
  "本臂内部没有「改前」可比的那一格写作 `NOT_MEASURED_no_before_reading`，不写 0。")
A("   格③ 与固定底栏带的关系（先滚进视口再量；本机顶边实测 " + str(Z["cell_3_against_bottom_bar"]["hit_line_px_measured_on_this_box"]) + " px）：" +
  json.dumps(ROWS, ensure_ascii=False))
A("   格④ 条内机器 token：" + json.dumps(Z["cell_4_machine_tokens"]["scanned_lines"], ensure_ascii=False) + " 整行读回后扫描，token_count = " +
  str(Z["cell_4_machine_tokens"]["token_count"]) + " ；原始值只在属性里（`data-ladder-has-candidates=" +
  str(Z["cell_4_machine_tokens"]["attributes_holding_the_raw_values"].get("has_candidates")) + "` 、`data-ladder-candidates=" +
  str(Z["cell_4_machine_tokens"]["attributes_holding_the_raw_values"].get("candidates")) + "` 、`data-cnx-value=\"\"`），没有贴上屏。英文臂同一套四格：" +
  json.dumps(E["cell_2_count_moves"]["painted_here"], ensure_ascii=False) + " ，零汉字 = " + json.dumps(not re.search(u"[\\u3400-\\u4dbf\\u4e00-\\u9fff]", " ".join(E["cell_2_count_moves"]["painted_here"]))) + " 。")
A("")
A("## 4. 见证类型 —— 空态这一屏我是怎么到达的")
A("   先钉真字节（" + COORD["emptier"] + " 之外不改任何响应）：现读这一代 demo 旅程仍交回 cards = " + str(PB.get("offer_cards")) +
  " 枚、梯子亮 " + json.dumps(PB.get("tiers"), ensure_ascii=False) + " 两档、`data-ladder-candidates=" +
  str(PB.get("facts", {}).get("candidates")) + "` ⇒ **空态在这台服务器这次的真数据下量不到**，我没有把它当作已过。")
A("   空态那一屏由本地应答到达：把 `GET /api/v1/journeys/{id}/experience` 的 `options` 抹成空数组（" +
  json.dumps(PAIR.get("endpoints_patched"), ensure_ascii=False) + "），见证类型 = `HTTP_RESPONSE`。它证明的是梯子面对「没有候选」这一形时说得出自己的名字，不是这台服务器给了空态。" +
  "号令者 18:40 在他自己那台亲测到的空屏（`stay-no-options` 正文 142 字）与我这里的差异只在数据代次：我这一代 demo 有候选。")
A("")
A("## 5. ORD-0455 那把已交付的闸：本批让它多了一枚分母，按规矩改写成 r2")
A("   现读 r1 头 " + R1_HEAD + " （冻结、不覆盖、不改写）。r1 的 M1 把可达集合钉死在「10 枚具体措辞」，本批往文案模块加了第 11 枚（`" + EMPTY_KEY + "`），" +
  "于是 r1 的 M1 在现尖上报红：`有措辞谁都不引用：[\"ladder.method.noCandidates\"]`。**这是分母动了，不是行为回退** —— 同一次跑里 r1 的 M2/S/Z/E/C 五臂仍全绿（run_id " + str(R2.get("run_id") if R2 else "") + " 之前的那笔）。")
A("   我没有去改 r1 的断言换绿，而是出 `frontend/e2e/qoder-ord0455-estimation-ladder-r2.spec.ts`（blob " + SPEC_R2_BLOB + " ）：" +
  "可达集合改为与文案模块对算（`copy_rungs_never_derived=" + json.dumps(M1.get("copy_rungs_never_derived")) + "` 、`derived_without_copy=" +
  json.dumps(M1.get("derived_without_copy")) + "` ），并把空态那一形加进不变量全组合（" + COORD["r2_cases"] + " ，cases=" + str(M2.get("cases")) +
  " 例、violations=" + str(M2.get("violations_total")) + " 例、四档全部点得亮）。r1 与 r2 的差只在仪表，产品字节 0 差（" + COORD["r2_reach"] + " ）。")
A("")
A("## 6. 编译臂与尺")
A("   我这枚头的导出件（node_modules 走 `os.link` 硬链、nlink = " + str(NLINK) + " ）逐行退出码：")
for label, rc, _t in BUILD:
    A("     " + label + " rc=" + str(rc))
A("   入口 asset " + json.dumps(ASSETS) + " ，本机字节重算文件 sha1 over bytes = " + BUNDLE + " （非 git 对象声明；同段可 `git cat-file` 的 40 位：仪表 " +
  SPEC_BLOB + " 、r2 件 " + SPEC_R2_BLOB + " 、读数件 " + ART_BLOB + " 、本生成器 " + GEN_BLOB + " ）；bundle 内逐串命中：" +
  json.dumps(BUNDLE_HITS, ensure_ascii=False) + " 。")
A("   门尺自检：`" + LIVE + "/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0 ，退出码与 findings 由本进程写进收件口之前对这份草稿现跑，跑红不投递；" +
  "该尺本机字节重算文件 sha1 = " + R7_SHA1 + " （非 git 对象声明；同段可 cat-file 的 40 位：入库 blob " + R7_BLOB + " 、byte_count = " + str(len(r7b)) + " 与我运行的字节数相同、交付头 " + PUSHED + " ）。")
A("   第二道闸对同一份草稿逐值复算：只扫逐字 40 位，免除要同一行写明不可取回且同段另有一枚能 cat-file 的 40 位，`path:line` 不算数；abort 非空不投递。")
A("   边界：权威线 0 次移动（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）；账本 0 次直写（本块走收件口）；`D:/moodle/_qoder_preview_20260920/_preview.db` 一次未开；`demo/reset` 0 次；" +
  "别人 worktree 0 次进入；r1 那枝 0 次改写。闸用的库与端口是本跑自己新建自起的（前端 " + str(R0468["ports"]["frontend"]) + " 、后端 " + str(R0468["ports"]["backend"]) +
  " ，库 " + R0468["db"] + " ），" + NETSTAT + " ；D 盘可用 " + FREE + " 。")
A("")
A("## 7. 复现")
A("   两把都跑在同一台机上：`env -u HTTP_PROXY -u HTTPS_PROXY python review/e4f_e2e_r1.py --wt D:/moodle/_qoder_lane_q0406 --target e2e/" +
  "qoder-ord0468-ladder-empty-reading-r1.spec.ts --tag e4f` （run_id " + R0468["run_id"] + " ，counts " + json.dumps(R0468["counts"]) + " ，log " + R0468["log"] + " ）" +
  "与同式 `--target e2e/qoder-ord0455-estimation-ladder-r2.spec.ts` （run_id " + str(R2.get("run_id")) + " ，counts " + json.dumps(R2.get("counts")) + " ，log " + str(R2.get("log")) + " ）。")
A("   本枝上的提交（`git log --format=%H %s " + BASE + ".." + PUSHED + "` 现读，逐字 40 位）：" + " ; ".join(COMITS) + " 。")
A("   读数汇总（四格逐格、前后配对、真字节那一臂、两把闸的六枚读数、三行退出码、bundle 命中）在 `review/q468_ladder_empty_r1.json`（blob " + ART_BLOB + " ，可 `git cat-file -p` ）。")

text = "\n".join(L) + "\n"
DRAFT = os.path.join(SCR, "q468_empty_r1_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write(text)
rc, r7out = run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"), "--text", DRAFT, "--expect-clean"])
io.open(os.path.join(SCR, "q468_r7_out.txt"), "w", encoding="utf-8").write(r7out)
print("GATE_R7 rc=" + str(rc))
for l in [x.strip()[:190] for x in r7out.split("\n") if x.startswith("  line ") or "overall" in x]:
    print("    " + l)
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
          if not res[h] and not (bool(dec.search(t)) and any(res[o] for o in hx.findall(par(n - 1)) if o != h))]
    return len(vals), sum(res.values()), ab


NT, NR, AB = bolt(DRAFT)
print("BOLT tokens=" + str(NT) + " resolvable=" + str(NR) + " would_abort=" + str(len(AB)))
for n, h in AB:
    print("    L" + str(n) + " " + h[:14])
if AB:
    print("NOT PUBLISHED -- second arm would abort")
    sys.exit(3)
NAME = "qoder-0468_" + NOW + ".md"
OUTP = os.path.join(INBOX, NAME)
if not re.fullmatch(r"[A-Za-z0-9._-]+_[0-9]{4}\.md", NAME):
    print("block filename rejected: " + NAME)
    sys.exit(1)
if os.path.exists(OUTP):
    print("block file already exists, refusing to overwrite: " + OUTP)
    sys.exit(1)
io.open(OUTP, "w", encoding="utf-8", newline="\n").write(text)
rc, bo = run([VENV, "-X", "utf8", os.path.join(LIVE, "patrol", "bolt_replica.py")])
io.open(os.path.join(SCR, "q468_bolt_out.txt"), "w", encoding="utf-8").write(bo)
LINES = [x for x in bo.splitlines() if "0468" in x]
print("OFFICIAL_BOLT rc=" + str(rc) + " " + (" || ".join(LINES)[:400] if LINES else bo.strip()[-300:]))
print("WROTE " + OUTP + " " + str(os.path.getsize(OUTP)) + " bytes would_abort=" + str(len(AB)))
print("OK " + PUSHED)
