#!/usr/bin/env python3
"""ORD-0415 (ruling: option yi) delivery: the rule module leaves the product tree.

The block's load-bearing claim is not a grep count alone: both generations are built here and their
entry bundles are compared byte for byte, which is what proves the module was never in the shipped
artifact. Everything else is read back off the branch and the receipts.
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
SNAP = r"D:/moodle/_qoder_lane_0415b_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
NODE = r"C:/Program Files/nodejs/node.exe"
TSC = os.path.join(NM_SRC, "typescript", "bin", "tsc")
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BRANCH = "review/Q-ord0415-label-rule-out-of-product-r1"
BASE = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
GEN_BASE = "8d038b21f09477b933cff3b1c7b09845c542373b"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
OLD = "frontend/src/lib/mapLabels.ts"
NEW = "frontend/e2e/_mapLabelRules.ts"
S0403 = "frontend/e2e/qoder-map-ord0403-named-control-and-labels.spec.ts"
S0412 = "frontend/e2e/qoder-map-ord0412-label-scope.spec.ts"
S0415 = "frontend/e2e/qoder-ord0415-label-string-origin.spec.ts"
JM = "frontend/src/components/JourneyMap.tsx"
bad = []


def run(cmd, cwd=None, timeout=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=e, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(*a, check=True, cwd=REPO):
    rc, out = run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", cwd, *a])
    if check and rc:
        bad.append("git %s rc=%d %s" % (" ".join(a), rc, out[-120:]))
    return out.strip()


def git_ok(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True).returncode == 0


def blob_at(ref, rel):
    out = git("rev-parse", "%s:%s" % (ref, rel), check=False)
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else ""


def head_of(refspec):
    for l in git("ls-remote", "origin", refspec).splitlines():
        p = l.split()
        if len(p) == 2 and p[1] == refspec:
            return p[0]
    return ""


def hits(ref, rel, pattern):
    return [l for l in git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False).splitlines()
            if l.strip()]


def line_of(ref, rel, pattern):
    out = git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for %r in %s" % (pattern, rel))
        return "%s:?" % rel
    return "%s:%s" % (rel, m.group(1))


def receipts(tag):
    out = []
    for f in sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)), key=os.path.getmtime):
        out.append(json.load(open(f, encoding="utf-8")))
    return out


def cases(r):
    return sorted(re.findall(r"›\s*(\S+\.spec\.ts):\d+:\d+ ›\s*(.+?)\s*$", io.open(
        r["log"], encoding="utf-8", errors="replace").read(), re.M))


TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
if not git_ok("cat-file", "-e", TIP):
    bad.append("the live tip is not retrievable: %r" % TIP)
HEAD = git("rev-parse", "HEAD", cwd=WT)
if not git_ok("merge-base", "--is-ancestor", BASE, HEAD):
    bad.append("my branch is not built on the base the ruling names")
N_LAG = int(git("rev-list", "--count", "%s..%s" % (BASE, TIP)) or 0)
MT_RC, MT_OUT = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, HEAD])
ALL_TOUCHED = [l for l in git("diff", "--name-only", BASE, HEAD, cwd=WT).splitlines() if l.strip()]
TOUCHED = [t for t in ALL_TOUCHED if not t.startswith("review/")]
# with rename detection the deleted path folds into the new one, so the expected set is four paths
if sorted(TOUCHED) != sorted([NEW, S0403, S0412, S0415]):
    bad.append("unexpected touched set: %s" % TOUCHED)
if [t for t in ALL_TOUCHED if t.startswith("review/") and not t.startswith("review/q415_")]:
    bad.append("unexpected review paths: %s" % ALL_TOUCHED)
NOREN = git("diff", "--no-renames", "--name-status", BASE, HEAD, cwd=WT).splitlines()
DELETED = [l for l in NOREN if l.startswith("D") and OLD in l]
ADDED = [l for l in NOREN if l.startswith("A") and NEW in l]
if not DELETED or not ADDED:
    bad.append("the move is not a deletion in the product tree plus an addition on the gate side: %s" % NOREN)
REN = [l.split()[0] for l in git("diff", "--find-renames", "--name-status", BASE, HEAD, cwd=WT).splitlines() if NEW in l]
if [t for t in TOUCHED if t.startswith("backend/") or (t.startswith("frontend/src/") and t != OLD)]:
    bad.append("paths outside the ruling touched: %s" % TOUCHED)
# the criterion the ruling states, measured on my head and on the base
REFS_OLD_HEAD = hits(HEAD, "frontend/src", "mapLabelTextField")
REFS_OLD_BASE = hits(BASE, "frontend/src", "mapLabelTextField")
REFS_ANY_HEAD = hits(HEAD, "frontend/src", "mapLabels")
if len(REFS_OLD_HEAD) != 0:
    bad.append("the criterion is not met: frontend/src still mentions mapLabelTextField: %s" % REFS_OLD_HEAD)
if len(REFS_ANY_HEAD) != 0:
    bad.append("frontend/src still references the module path at all: %s" % REFS_ANY_HEAD)
if git("rev-parse", "%s:%s" % (HEAD, OLD), check=False) and re.fullmatch(
        r"[0-9a-f]{40}", git("rev-parse", "%s:%s" % (HEAD, OLD), check=False)):
    bad.append("the module is still in the product tree on my head")
NEW_BLOB = blob_at(HEAD, NEW)
MOVED_IDENTICAL = blob_at(BASE, OLD) == NEW_BLOB  # only the header comment was added, so these differ
# the importers, on my head
IMP_HEAD = hits(HEAD, "frontend/e2e", '"./_mapLabelRules"')
IMP_STALE = hits(HEAD, "frontend", '"../src/lib/mapLabels"')
if len(IMP_HEAD) < 3 or IMP_STALE:
    bad.append("importer accounting wrong: new=%d stale=%d" % (len(IMP_HEAD), len(IMP_STALE)))

# ---------- receipts: the gates, with the base generation beside them ----------
M1 = {os.path.basename(str(r.get("target"))): r for r in receipts("q415m1")}
B1 = {os.path.basename(str(r.get("target"))): r for r in receipts("q415b1")}
B2 = {os.path.basename(str(r.get("target"))): r for r in receipts("q415b2")}
if M1.get("qoder-map-ord0412-label-scope.spec.ts", {}).get("verdict") != "GREEN":
    bad.append("the ord0412 gate is not green after the move")
if M1.get("qoder-ord0415-label-string-origin.spec.ts", {}).get("verdict") != "GREEN":
    bad.append("my own readings spec is not green after the move")
G0403 = M1.get("qoder-map-ord0403-named-control-and-labels.spec.ts")
if not G0403:
    bad.append("no ord0403 receipt after the move")
BASE0403 = (B2.get("qoder-map-ord0403-named-control-and-labels.spec.ts"),
            B1.get("qoder-map-ord0403-named-control-and-labels.spec.ts"))
if not all(BASE0403):
    bad.append("missing the ord0403 base generations")
F_MOVE = [c[1] for c in cases(G0403)]
F_BASE = [[c[1] for c in cases(r)] for r in BASE0403]
for r, f in zip(BASE0403, F_BASE):
    if f and f != F_MOVE:
        bad.append("the ord0403 red set differs at run %s: %s vs %s" % (r["run_id"], f, F_MOVE))
OVERLAP = sorted({int(m) for m in re.findall(r'"withNotice":(\d+)', io.open(
    G0403["log"], encoding="utf-8", errors="replace").read())})
WIDTHS = sorted({int(m) for m in re.findall(r"reach-(\d+)", io.open(
    G0403["log"], encoding="utf-8", errors="replace").read())})
if not OVERLAP:
    bad.append("no tile-notice overlap reading in the ord0403 log")

# ---------- compile arm on both generations ----------
os.makedirs(SNAP, exist_ok=True)
nm = os.path.join(SNAP, "frontend", "node_modules")
if not os.path.isdir(nm):
    shutil.copytree(NM_SRC, nm, copy_function=os.link, symlinks=True)
NLINK = os.stat(os.path.join(nm, "typescript", "package.json")).st_nlink
if NLINK < 2:
    bad.append("node_modules is not hard-linked: nlink=%d" % NLINK)
BUILD = {}
for label, ref in (("base", BASE), ("mine", HEAD)):
    p1 = subprocess.Popen(["git", "-C", REPO, "archive", "--format=tar", ref], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["tar", "-x", "-C", SNAP], stdin=p1.stdout)
    p1.stdout.close()
    if p2.wait(300):
        bad.append("tar failed for %s" % label)
        continue
    for rel, want in ((OLD, label == "base"), (NEW, label == "mine")):
        p = os.path.join(SNAP, *rel.split("/"))
        if not want and os.path.exists(p):
            os.remove(p)
        if want and not os.path.exists(p):
            bad.append("the export of %s lacks %s" % (label, rel))
    fe = os.path.join(SNAP, "frontend")
    one = {"ref": ref, "src_lib_mapLabels_exists": os.path.exists(os.path.join(SNAP, *OLD.split("/"))),
           "e2e_rules_exists": os.path.exists(os.path.join(SNAP, *NEW.split("/")))}
    for proj in ("tsconfig.check.json", "tsconfig.typecheck.json"):
        rc, o = run([NODE, TSC, "-p", proj, "--noEmit"], cwd=fe, timeout=2400)
        one[proj] = {"rc": rc, "error_lines": len([l for l in o.splitlines() if "error TS" in l])}
        if rc:
            bad.append("%s %s rc=%d" % (label, proj, rc))
    rc, o = run([NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"], cwd=fe, timeout=2400)
    if rc:
        bad.append("%s vite rc=%d %s" % (label, rc, o[-200:]))
    adir = os.path.join(fe, "dist", "assets")
    assets = sorted(f for f in os.listdir(adir) if f.startswith("index-") and f.endswith(".js")) if rc == 0 else []
    raw = open(os.path.join(adir, assets[0]), "rb").read() if len(assets) == 1 else b""
    one["vite"] = {"rc": rc, "assets": assets, "bytes": len(raw),
                   "sha1_local_recomputed": hashlib.sha1(raw).hexdigest() if raw else ""}
    one["bundle_tokens"] = {"get_title_literal": b'"get","title"' in raw,
                            "openfreemap_token": b"openfreemap" in raw,
                            "canvas_label_strings_name": b"canvas-label-strings" in raw,
                            "provider_attribution_source_name": b"basemap/provider attribution" in raw}
    BUILD[label] = one
if BUILD.get("base", {}).get("vite", {}).get("sha1_local_recomputed") != \
        BUILD.get("mine", {}).get("vite", {}).get("sha1_local_recomputed"):
    bad.append("the entry bundle changed between the generations; the tree-shake claim is wrong")

# ---------- artifact + commit, only after every check above ----------
if bad:
    print("REFUSING BEFORE THE READOUTS COMMIT -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
ART = "review/q415_rule_out_of_product_r1.json"
json.dump({"tip": TIP, "base": BASE, "branch": BRANCH, "head": HEAD, "commits_since_base": int(
    git("rev-list", "--count", "%s..%s" % (BASE, HEAD)) or 0), "lag_behind_tip": N_LAG,
    "merge_tree": {"rc": MT_RC, "conflict_lines": len([l for l in MT_OUT.splitlines() if ":" in l])},
    "touched": {t: blob_at(HEAD, t) for t in TOUCHED},
    "criterion": {"refs_in_frontend_src_on_base": REFS_OLD_BASE,
                  "refs_in_frontend_src_on_head": REFS_OLD_HEAD,
                  "path_refs_in_frontend_src_on_head": REFS_ANY_HEAD,
                  "importers_of_new_path": IMP_HEAD, "stale_importers": IMP_STALE,
                  "old_module_blob_on_base": blob_at(BASE, OLD), "new_module_blob_on_head": NEW_BLOB},
    "gates": {"after_move": M1, "base_gen_before_0406": BASE0403[0], "base_gen_at_my_head": BASE0403[1],
              "ord0403_failing_cases": F_MOVE, "tile_notice_overlap_px2": OVERLAP,
              "widths": WIDTHS},
    "build": BUILD},
    open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, "review", "q415_out_of_product_r1.py"))
git("add", "-f", ART, "review/q415_out_of_product_r1.py", cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0415 readouts: the criterion measured on both generations, the three gates, "
              "and the entry bundle compared byte for byte"])
if rc and "nothing to commit" not in co:
    print("COMMIT FAILED -- %s" % co[-200:])
    sys.exit(1)
rc, po = run(["git", "-C", WT, "-c", "http.proxy=", "-c", "https.proxy=", "push", "-q",
              "origin", "refs/heads/" + BRANCH])
if rc:
    print("PUSH FAILED -- %s" % po[-200:])
    sys.exit(1)
PUSHED = head_of("refs/heads/" + BRANCH)
if not PUSHED or git("cat-file", "-t", PUSHED) != "commit":
    bad.append("the pushed head does not resolve")
elif not git_ok("merge-base", "--is-ancestor", HEAD, PUSHED):
    bad.append("the pushed head lost the measured head")
elif [l for l in git("diff", "--name-only", HEAD, PUSHED).splitlines() if l.strip() and not l.startswith("review/")]:
    bad.append("the readouts commit touched non-review paths")
ART_BLOB = blob_at(PUSHED, ART)
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    bad.append("the door ruler is not the byte-for-byte one the relay named")
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = "%s:%s" % (NOW[:2], NOW[2:])
GB = [l for l in run(["df", "-h", "/d"])[1].splitlines() if l.strip()][-1].split()[3]

B = []
A = B.append
A("### ORD-0415 后半 · 道0370（会话 e4f3490f）· 号令者 08:27 裁「不接线，把纸面规则请出产品树」· 乙案落地 · 2026-09-29 %s+08" % NW)
A("")
A("## 交付坐标")
A("   新枝 `refs/heads/%s`（不覆盖任何已推 ref；我那条读数枝 %s 原样留着，头 %s ）" % (
    BRANCH, "review/Q-ord0415-label-string-origin-r1", "01c3d411c76b074cf0925d4b83425f924ddd2fa4"))
A("   push 后 `git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/%s` 现读头 = %s ；" % (BRANCH, PUSHED))
A("   `git cat-file -t` = commit，基点 = 号令者 08:27 那块点名的 %s （`git merge-base` 现读为其祖先）。" % BASE)
A("   写这块前再读现尖 = %s ，已在我基点之上 %d 笔；合流我按只读口径预测：`git merge-tree --write-tree %s %s` 退出码=%d ；" % (
    TIP, N_LAG, TIP, PUSHED, MT_RC))
A("   我这 %d 笔只动 %d 枚路径，逐枚：" % (int(git("rev-list", "--count", "%s..%s" % (BASE, PUSHED)) or 0),
                       len([l for l in git("diff", "--name-only", BASE, PUSHED).splitlines() if l.strip()])))
for t in [l for l in git("diff", "--name-only", BASE, PUSHED).splitlines() if l.strip()]:
    A("      %s blob %s" % (t, blob_at(PUSHED, t)))
A("   产品树里被动的只有那一枚移出：`%s` -> `%s`；不分改名时是两条（D=%d 枚、A=%d 枚），启用改名检测时状态=%s ；" % (
    OLD, NEW, len(DELETED), len(ADDED), "/".join(sorted(set(REN))) or "无"))
A("   backend/ 前缀命中=%d 枚，`frontend/src` 下除这一枚删除别无他动（`git diff --name-status %s %s` 现读逐枚就是上面那几行）。" % (
    len([l for l in git("diff", "--name-only", BASE, PUSHED, cwd=WT).splitlines() if l.startswith("backend/")]), BASE, PUSHED))
A("")
A("## 判据一 · 「`frontend/src` 下对 mapLabelTextField 的引用数=0」")
A("   在基点 %s 上：`git grep -n -F -e mapLabelTextField %s -- frontend/src` 命中 %d 行（逐枚 %s ）——那就是它自己的定义；" % (
    BASE[:12], BASE[:12], len(REFS_OLD_BASE), REFS_OLD_BASE[0].split(":")[2] + ":" + REFS_OLD_BASE[0].split(":")[3] if REFS_OLD_BASE else "无"))
A("   在我交付头 %s 上：同一命令命中 %d 行；再加一条更宽的（任何 `mapLabels` 字样在 frontend/src 下）也命中 %d 行；" % (PUSHED[:12], len(REFS_OLD_HEAD), len(REFS_ANY_HEAD)))
A("   文件本身在头树上不可解（`git rev-parse %s:%s` 不是 40 位），在新位可解：`%s` = %s 。" % (PUSHED, OLD, NEW, NEW_BLOB))
A("   三处 importer 全部指向新位（`git grep -F -e '\"./_mapLabelRules\"' %s -- frontend/e2e` 现读命中 %d 行）：逐枚 %s ；" % (
    PUSHED[:12], len(IMP_HEAD), " ".join("%s:%s" % (l.split(":")[1], l.split(":")[2]) for l in IMP_HEAD)))
A("   残留旧路径引用命中=%d 行（同法现数）。头部只加了一段说明为什么搬（含「谁把它搬回 src/lib 就该由闸报红」的约定）。" % len(IMP_STALE))
A("")
A("## 判据二 · 「frontend/e2e 那两把 spec 仍跑绿」——这一半我没有满足，成因不在我这一步，逐数交出")
A("   `qoder-map-ord0412-label-scope.spec.ts`：run_id=%s verdict=%s passed=%d tree=%s ，日志 %s ；" % (
    M1["qoder-map-ord0412-label-scope.spec.ts"]["run_id"], M1["qoder-map-ord0412-label-scope.spec.ts"]["verdict"],
    M1["qoder-map-ord0412-label-scope.spec.ts"]["counts"]["passed"],
    str(M1["qoder-map-ord0412-label-scope.spec.ts"]["tree"])[:12], M1["qoder-map-ord0412-label-scope.spec.ts"]["log"]))
A("   其中 `scope-declared` 那一格现在多了一条断言：`existsSync(\"src/lib/mapLabels.ts\")` 必须为假（判据 %s ）。" % line_of(PUSHED, S0412, "existsSync(\"src/lib/mapLabels.ts\")"))
A("   我那枚读数件 `%s` 也仍跑绿：run_id=%s verdict=%s passed=%d（它也 import 这一份表）。" % (
    S0415, M1["qoder-ord0415-label-string-origin.spec.ts"]["run_id"],
    M1["qoder-ord0415-label-string-origin.spec.ts"]["verdict"], M1["qoder-ord0415-label-string-origin.spec.ts"]["counts"]["passed"]))
A("   `qoder-map-ord0403-named-control-and-labels.spec.ts`：带我这次搬动 run_id=%s verdict=%s passed=%d failed=%d 日志 %s ；" % (
    G0403["run_id"], G0403["verdict"], G0403["counts"].get("passed", -1), G0403["counts"].get("failed", -1), G0403["log"]))
A("   红的是同四条 `reach — the control is hittable and does not collide @%s`（用例名逐枚 %s ），报的都不是 import/规则那一格；" % (
    "、".join(str(w) for w in WIDTHS), "、".join(F_MOVE)))
A("   `labels`（吃这张禁表的那格）与 `control-state`、`marker-to-card` 都在这条 run 里过了（passed=%d 里含它们，见上面日志）——搬动没把共用的表弄断。" % G0403["counts"].get("passed", -1))
A("   同一把闸在我之外的两代基线上跑，失败集合逐字相同：基点 %s 带旧位文件那一次 run_id=%s verdict=%s failed=%d ；" % (
    BASE[:12], BASE0403[1]["run_id"], BASE0403[1]["verdict"], BASE0403[1]["counts"].get("failed", -1)))
A("   再往前到 ORD-0406 那一搬落地之前（%s，band 还在地图之后）run_id=%s verdict=%s failed=%d 日志 %s 。" % (
    GEN_BASE[:12], BASE0403[0]["run_id"], BASE0403[0]["verdict"], BASE0403[0]["counts"].get("failed", -1), BASE0403[0]["log"]))
A("   ⇒ 三条 run 的失败用例名一致 ⇒ 「两把 spec 仍跑绿」这一半被一枚**先前就在**的地图屏缺陷挡住了，不是这次搬动造成的，我也没去改它的判据换绿。")
A("   那枚缺陷的读数：`[data-testid='map-viewport-reset']`（标签 \"Fit to my journey\"）与瓦片提示的重叠面积四形都 = %s px²，" % "、".join(str(x) for x in OVERLAP))
A("   控件盒 x/y/w/h 见 %s 那格 reach-* 行（四形宽 %s 都 `hitSelf=true`，`withHint` 读数集合=%s 、`withStack` 集合=%s ）；" % (
    ART, "、".join(str(w) for w in WIDTHS), json.dumps(sorted({int(m) for m in re.findall(r'"withHint":(-?\d+)', io.open(G0403["log"], encoding="utf-8", errors="replace").read())})),
    json.dumps(sorted({int(m) for m in re.findall(r'"withStack":(-?\d+)', io.open(G0403["log"], encoding="utf-8", errors="replace").read())}))))
A("   归属：那是地图面板的布局，不在我名下也不在禁改墙上，请号令者派给持 `MapPanel`/`styles.css` 的车道；判据源 %s 。" % line_of(PUSHED, S0403, "must not sit under the tile notice"))
A("")
A("## 我为什么支持乙案：产品产物本来就没有它")
A("   同一台、同一份 node_modules（`os.link` 借，`typescript/package.json` 的 st_nlink=%d ），两代各跑一次编译臂：" % NLINK)
for label in ("base", "mine"):
    bb = BUILD[label]
    A("      gen=%s 导出里 %s=%s 、%s=%s ；cmd=npx tsc -p tsconfig.check.json --noEmit rc=%d error_lines=%d ；cmd=npx tsc -p tsconfig.typecheck.json --noEmit rc=%d error_lines=%d ；cmd=npx vite build rc=%d" % (
        label, OLD, bb["src_lib_mapLabels_exists"], NEW, bb["e2e_rules_exists"],
        bb["tsconfig.check.json"]["rc"], bb["tsconfig.check.json"]["error_lines"],
        bb["tsconfig.typecheck.json"]["rc"], bb["tsconfig.typecheck.json"]["error_lines"], bb["vite"]["rc"]))
    A("      产物 /assets/%s size_bytes=%d，本地字节重算文件 sha1=%s（非 git 对象声明；同段可 cat-file 的坐标：交付头 %s ）" % (
        "".join(bb["vite"]["assets"]), bb["vite"]["bytes"], bb["vite"]["sha1_local_recomputed"], PUSHED))
A("   两代的入口产物名与字节**逐字相同**（同一枚 sha1），所以那枚模块本来就被 tree-shake 掉了，不在发货产物里；")
A("   它在 `frontend/src/lib/` 下只是让人以为运行时有一条玻璃标注规则。另三枚 token 也现读为假：`\"get\",\"title\"`=%s 、`canvas-label-strings`=%s 、`basemap/provider attribution`=%s ；" % (
    BUILD["mine"]["bundle_tokens"]["get_title_literal"], BUILD["mine"]["bundle_tokens"]["canvas_label_strings_name"],
    BUILD["mine"]["bundle_tokens"]["provider_attribution_source_name"]))
A("   `openfreemap` 字样=%s 仍在产物里——那是地图自己的归属句，不是这张禁表（%s 记的正是这两面不能混）。" % (
    BUILD["mine"]["bundle_tokens"]["openfreemap_token"], line_of(PUSHED, NEW, "ORD-A basemap provider attribution must stay readable")))
A("   画在玻璃上的字仍由 `%s` 那句字面量决定（现读该行 %s ），这一点乙案没改，也不该由我改。" % (JM, line_of(PUSHED, JM, '"text-field"')))
A("")
A("## 没改善的部分")
A("1. 「两把 spec 仍跑绿」我只拿到一把半：ord0412 全绿、ord0403 里与规则相关的格子全绿，`reach` 四格红在先前两代就在（数在上面）。")
A("   要我把那四格也弄绿，得动地图面板布局或瓦片提示——那是别人的文件与另一张单的口径，我不在这单里偷改。")
A("2. 我没有删掉那枚模块，只搬。删是裁语给的另一个选项，留着是因为两把闸共用这张表；若号令者要删，我改把表内联进闸（一次搬运，代价是把「一处定义」变成两处）。")
A("3. 玻璃上真实栅格化的字符串仍没量到：`%s` 里 `not_measured` 那一格照旧（maplibre 不在容器上留把手，我不为测量往产品里加 window 钩子）。" % ART)
A("4. 我没跑整套 e2e，只跑了这三把（+ 先前那把 ORD-0415 读数闸）；`review/` 下我这条枝的仪表与件不算产品。")
A("5. 盘：D 盘剩余 %s（`df -h /d` 现读）；本车道端口按 pid 关并 netstat 复查。两代导出复用了同一枚 `%s`，没另开第二枚目录。" % (GB, SNAP))
A("6. 我这条枝与已入账的 `Q-ord0438-progress-contract-r1`（头 %s）互不覆盖，两枝各自挂在同一基点之上，读的人按枝名取。" % "099f6223b1ed41c27d7ef2a9f6bd9474fef50a74")
A("")
A("门尺自检：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0，退出码与 findings 由本进程写盘前现跑；" % LIVE)
A("   那把尺本地字节重算文件 sha1=%s（与值守给的 40 位逐字相同；非 git 对象声明，同段可 cat-file 的坐标：入库 blob %s ，" % (R7_SHA1, R7_BLOB))
A("   `git cat-file -s %s` 得 byte_count=%d 与我运行的字节数相同；交付头 %s 、读数件 blob %s ）。" % (R7_BLOB, len(r7b), PUSHED, ART_BLOB))
A("   第二道闸在同一份草稿上逐值复算：只扫逐字 40 位，免除要同一行写明不可取回且同段有另一枚能 cat-file 的 40 位，")
A("   path:line 不算数；abort 清单非空就不投递。")

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR, "q415_out_of_product_r1_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write("\n".join(B) + "\n")
print("DRAFT", DRAFT, os.path.getsize(DRAFT), "bytes HEAD", PUSHED)
rc, out = run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"),
               "--text", DRAFT, "--expect-clean"])
print("GATE_R7 rc=%d" % rc)
for l in [x.strip()[:190] for x in out.split("\n") if x.startswith("  line ") or "overall" in x]:
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
    print("    L%-3d %s" % (n, h[:16]))
if AB:
    print("NOT PUBLISHED -- second arm would abort")
    sys.exit(3)
if glob.glob(os.path.join(INBOX, "qoder-0415b_*.md")):
    print("REFUSED PUBLISH -- a live block for this order is already in the inbox")
    sys.exit(4)
OUTP = os.path.join(INBOX, "qoder-0415b_%s.md" % NOW)
io.open(OUTP, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUTP, os.path.getsize(OUTP), "bytes")
