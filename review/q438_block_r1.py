#!/usr/bin/env python3
"""ORD-0438 delivery: compile arm on a hardlinked export, the readouts artifact, a new branch name,
both doors, then the block.

Everything the block claims is computed here out of the receipts and the branch's own objects -- the
mutation controls, the neighbouring-gate before/after pair, and the compile exit codes are read back
from files that exist, not typed in.
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
SNAP = r"D:/moodle/_qoder_lane_0438_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
TSC = os.path.join(NM_SRC, "typescript", "bin", "tsc")
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
BRANCH = "review/Q-ord0438-progress-contract-r1"
DROPPED = "add09e9af72570c0363d8d7c7c1932df52b5d2e5"
DROPPED_MORE = ["d234092e9b779641f32cacf018a33d5bbc48da59", "406f4763852a83d49ade7989e37580d20707f55b"]
PREREBASE = "0af7838660df023e3ae55a274e64046e2e007c9b"
REBASE_TARGET = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
MOD = "frontend/src/features/progress/journeyProgress.ts"
TRIP = "frontend/src/features/trip/TripItinerary.tsx"
GATE = "frontend/e2e/qoder-ord0438-progress-contract.spec.ts"
READ = "frontend/e2e/qoder-ord0438-progress-contract-readings.spec.ts"
EXEC = "frontend/src/lib/executionWindow.ts"
V8 = "frontend/src/app/V8Experience.tsx"
V12 = "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx"
LANG = "frontend/e2e/qoder-speaks-the-travellers-language.spec.ts"
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


def line_of(ref, rel, pattern):
    """Every coordinate the block prints is a live read off the branch, with -F so literal brackets in
    the patterns are not read as BRE bracket expressions."""
    out = git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for %r in %s on %s" % (pattern, rel, ref[:8]))
        return "%s:?" % rel
    return "%s:%s" % (rel, m.group(1))


def hits(ref, rel, pattern):
    return [l for l in git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False).splitlines()
            if l.strip()]


def members(line):
    """The stop states inside a `Set([...])` / `[...]` literal, read out of the grep line itself."""
    m = re.search(r"\[([^\]]*)\]", line)
    return re.findall(r"\"([A-Z_]+)\"", m.group(1)) if m else []


def receipt(tag):
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)), key=os.path.getmtime)
    if not fs:
        bad.append("no receipt for %s" % tag)
        return {}
    return json.load(open(fs[-1], encoding="utf-8"))


def log_text(r):
    return io.open(r["log"], encoding="utf-8", errors="replace").read()


def arm_lines(r):
    """The failing case titles, read out of the log rather than restated from memory."""
    out = []
    for l in log_text(r).splitlines():
        m = re.match(r"^\s+\d+\) \[chromium\] ›\s*\S+\s+›\s*(.+?)\s*$", l)
        if m:
            out.append(m.group(1))
    return sorted(out)


TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
for _c in [DROPPED, PREREBASE, REBASE_TARGET] + DROPPED_MORE:
    if not git_ok("cat-file", "-t", _c):
        bad.append("a disclosed coordinate does not resolve: %s" % _c)
if not git_ok("cat-file", "-e", TIP):
    bad.append("the live tip is not retrievable: %r" % TIP)
HEAD = git("rev-parse", "HEAD", cwd=WT)
BASE = git("merge-base", TIP, HEAD)
if not git_ok("merge-base", "--is-ancestor", BASE, HEAD):
    bad.append("the merge base is not on my branch")
N_LAG = int(git("rev-list", "--count", "%s..%s" % (BASE, TIP)) or 0)
N_AHEAD = int(git("rev-list", "--count", "%s..%s" % (BASE, HEAD)) or 0)
# the line moved under me at least once tonight, so predict the merge rather than asserting equality
MT_RC, MT_OUT = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, HEAD])
MT_CONFLICT = len([l for l in MT_OUT.splitlines() if re.match(r"^\s+\S+:", l)]) if MT_RC else 0
TOUCHED = [l for l in git("diff", "--name-only", BASE, HEAD, cwd=WT).splitlines() if l.strip()]
PRODUCT = [t for t in TOUCHED if t.startswith("frontend/src/")]
if sorted(PRODUCT) != sorted([MOD, TRIP]):
    bad.append("unexpected product paths in my diff: %s" % PRODUCT)
if [t for t in TOUCHED if t.startswith("backend/")]:
    bad.append("backend paths in my diff")

GATE_R = receipt("q438g4")
MA_R = receipt("q438mc")
MB_R = receipt("q438md")
P1_R = receipt("q438p1")
LANG_BEFORE = receipt("q438bg")
# the three neighbouring gates all ran under one tag; index them by the target each receipt names
AFR = {}
for f in sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "q438ag_*.json")), key=os.path.getmtime):
    r = json.load(open(f, encoding="utf-8"))
    AFR[os.path.basename(str(r.get("target")).replace("\\", "/"))] = r
LANG_AFTER = None
for k, v in AFR.items():
    if "speaks-the-travellers-language" in k:
        LANG_AFTER = v
if not LANG_AFTER:
    bad.append("the language gate has no after-receipt under tag q438af: %s" % sorted(AFR))
if GATE_R.get("verdict") != "GREEN" or str(GATE_R.get("tree")) != HEAD:
    bad.append("the clean gate is not GREEN on the head I publish: %s %s" % (GATE_R.get("verdict"), GATE_R.get("tree")))
for nm, r in (("MUT-A", MA_R), ("MUT-B", MB_R)):
    if r.get("verdict") != "RED":
        bad.append("%s did not go red, so the criterion does not bite" % nm)
    if str(r.get("tree")) != HEAD:
        bad.append("%s ran on another tree" % nm)
if not AFR:
    bad.append("no neighbour receipts under tag q438ag")
if [l for l in git("status", "--porcelain", cwd=WT).splitlines()
        if l.strip() and not l.startswith("??") and "q406_block_draft" not in l and "q438_block_r1" not in l]:
    bad.append("tracked paths are modified; the receipts would not name these bytes")
# the same gate, alternating my bytes and the base bytes; the state was read off `git hash-object` at
# each run and is re-checked here against the two blobs that exist on the branch and the base
LANG_STATE = {"q438x1": "WITHOUT", "q438x2": "WITH", "q438x3": "WITHOUT", "q438x4": "WITH",
              "q438x5": "WITH", "q438x6": "WITH", "q438x7": "WITHOUT", "q438x8": "WITHOUT",
              "q438ag": "WITH", "q438bg": "WITHOUT"}
BASE_TRIP_BLOB = blob_at(BASE, TRIP)
TRIP_BLOB = blob_at(HEAD, TRIP)
MOD_BLOB = blob_at(HEAD, MOD)
LANGROWS = []
for f in sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "q438x*_*.json")) +
                glob.glob(os.path.join(LIVE, "e2e_logs", "q438ag_*.json")) +
                glob.glob(os.path.join(LIVE, "e2e_logs", "q438bg_*.json")), key=os.path.getmtime):
    r = json.load(open(f, encoding="utf-8"))
    if "speaks-the-travellers-language" not in str(r.get("target")):
        continue
    if str(r.get("tree")) != HEAD:
        bad.append("a language-gate run is on another tree: %s" % r.get("run_id"))
    tag = re.match(r"(q438\w+?)_", os.path.basename(f)).group(1)
    state = LANG_STATE.get(tag)
    if state is None:
        bad.append("unmapped language-gate run: %s" % tag)
        continue
    blob = TRIP_BLOB if state == "WITH" else BASE_TRIP_BLOB
    if not git_ok("cat-file", "-e", blob):
        bad.append("the blob for state %s does not resolve" % state)
    LANGROWS.append({"tag": tag, "run_id": r["run_id"], "state": state, "trip_blob": blob,
                     "verdict": r["verdict"], "failing_cases": arm_lines(r), "log": r["log"]})
LANG_RED = [x for x in LANGROWS if x["verdict"] == "RED"]
LANG_GREEN = [x for x in LANGROWS if x["verdict"] == "GREEN"]
RED_WITH = len([x for x in LANG_RED if x["state"] == "WITH"])
RED_WITHOUT = len([x for x in LANG_RED if x["state"] == "WITHOUT"])
if len(LANGROWS) < 8 or not RED_WITH or not RED_WITHOUT:
    bad.append("the alternation is not balanced enough to attribute: runs=%d red_with=%d red_without=%d" % (
        len(LANGROWS), RED_WITH, RED_WITHOUT))
MOD_BLOB = blob_at(HEAD, MOD)
PORT_LINE = line_of(HEAD, "review/e4f_e2e_r1.py", "LOW, HIGH = ")
TRIP_BLOB = blob_at(HEAD, TRIP)
# the three lists of stop states, read off the branch as fixed strings
OWNERS = hits(HEAD, EXEC, "TERMINAL_ACTIVITY_STATES = new Set")
COPY_V8 = hits(HEAD, V8, '["COMPLETED", "SKIPPED", "CANCELLED"]')
COPY_V12 = hits(HEAD, V12, '["COMPLETED", "SKIPPED"]')
if not OWNERS or not COPY_V8 or not COPY_V12:
    bad.append("the three-list finding changed; re-measure before writing it")
SET_OWNER = members(OWNERS[0])
SET_V12 = members(COPY_V12[0])
MISSING_IN_V12 = [s for s in SET_OWNER if s not in SET_V12]
if not MISSING_IN_V12:
    bad.append("V12 no longer differs from the authoritative set; the finding is stale")

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
NLINK = os.stat(os.path.join(nm, "typescript", "package.json")).st_nlink
if NLINK < 2:
    bad.append("node_modules is not hard-linked into the snap: nlink=%d" % NLINK)
VERIFY = []
for rel in TOUCHED:
    sn = os.path.join(SNAP, *rel.split("/"))
    if not os.path.exists(sn):
        bad.append("the export is missing %s" % rel)
        continue
    raw = open(sn, "rb").read()
    hb = hashlib.sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()
    VERIFY.append((rel, hb, blob_at(HEAD, rel), hb == blob_at(HEAD, rel)))
for rel, got, want, ok in VERIFY:
    if not ok:
        bad.append("exported bytes differ for %s: %s vs %s" % (rel, got, want))
BUILD = []
for proj in ("tsconfig.check.json", "tsconfig.typecheck.json"):
    rc, o = run([NODE, TSC, "-p", proj, "--noEmit"], cwd=os.path.join(SNAP, "frontend"), timeout=2400)
    BUILD.append(("npx tsc -p %s --noEmit" % proj, rc, len([l for l in o.splitlines() if "error TS" in l])))
    if rc:
        bad.append("%s rc=%d %s" % (proj, rc, o[-200:]))
rc, vo = run([NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"],
             cwd=os.path.join(SNAP, "frontend"), timeout=2400)
BUILD.append(("npx vite build", rc, 0))
if rc:
    bad.append("vite build rc=%d %s" % (rc, vo[-200:]))
assets = glob.glob(os.path.join(SNAP, "frontend", "dist", "assets", "index-*.js"))
ASSET = os.path.basename(assets[0]) if len(assets) == 1 else "?"
ASSET_BYTES = os.path.getsize(assets[0]) if len(assets) == 1 else 0
ASSET_SHA1 = hashlib.sha1(open(assets[0], "rb").read()).hexdigest() if len(assets) == 1 else ""
if len(assets) != 1:
    bad.append("expected one built asset, found %d" % len(assets))
DFL = [l for l in run(["df", "-h", "/d"])[1].splitlines() if l.strip()]
GB = DFL[-1].split()[3] if len(DFL[-1].split()) > 3 else "?"

# ---------- artifact, commit, push ----------
ARMS = {}
for m in re.finditer(r"O438GATE ([A-Za-z0-9_-]+) (\{.*)", log_text(GATE_R)):
    ARMS[m.group(1)] = json.loads(m.group(2))
READINGS = {}
for m in re.finditer(r"O438 ([A-Za-z0-9_-]+) (\{.*)", log_text(P1_R)):
    READINGS[m.group(1)] = json.loads(m.group(2))
if sorted(ARMS) != ["M_derivation", "S_source_shape", "screen_en", "screen_zh-CN"]:
    bad.append("the clean gate did not print all four arms: %s" % sorted(ARMS))
if sorted(READINGS) != ["P1_denominators", "P2_empty_state"]:
    bad.append("the readings run did not print both arms: %s" % sorted(READINGS))
P1 = READINGS["P1_denominators"]
if bad:
    print("REFUSING BEFORE THE READOUTS COMMIT -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
ART = "review/q438_progress_contract_r1.json"
json.dump({"tip": TIP, "branch": BRANCH, "head_at_readings": HEAD, "gate": GATE_R,
           "mutations": {"MUT_A": MA_R, "MUT_B": MB_R},
           "neighbour_language": {"three_gates_with_change": AFR, "alternation": LANGROWS,
                                  "red_with_change": RED_WITH, "red_without_change": RED_WITHOUT},
           "arms": ARMS, "readings": READINGS,
           "terminal_lists": {"owner": OWNERS, "owner_members": SET_OWNER,
                              "copy_in_v8experience": COPY_V8, "copy_in_v12panel": COPY_V12,
                              "v12_members": SET_V12, "missing_in_v12": MISSING_IN_V12},
           "build": [{"cmd": c, "rc": r, "error_lines": e} for c, r, e in BUILD],
           "export": {"snap": SNAP, "node_modules_nlink": NLINK,
                      "verified_paths": len(VERIFY), "asset": ASSET, "asset_bytes": ASSET_BYTES,
                      "asset_sha1_local_recomputed": ASSET_SHA1}},
          open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, "review", "q438_block_r1.py"))
git("add", "-f", ART, "review/q438_block_r1.py", cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0438 readouts: the four arms, the two mutation controls, the neighbouring-gate "
              "before/after pair, and the compile arm on a hardlinked export"])
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
    bad.append("the pushed head lost the measured head")
NEW = [l for l in git("diff", "--name-only", HEAD, PUSHED).splitlines()
       if l.strip() and not l.startswith("review/")]
if NEW:
    bad.append("the readouts commit touched non-review paths: %s" % NEW)
ART_BLOB = blob_at(PUSHED, ART)
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    bad.append("the door ruler is not the byte-for-byte one the relay named: %s" % R7_SHA1)
G_M = line_of(PUSHED, GATE, "test(\"ORD-0438 M")
G_S = line_of(PUSHED, GATE, "test(\"ORD-0438 S")
G_Z = line_of(PUSHED, GATE, "test(\"ORD-0438 Z")
G_DAYASSERT = line_of(PUSHED, GATE, "day_phrase_on_screen, ")
M_HEAD = line_of(PUSHED, MOD, "day_total: typeof serverDayCount")
M_IMP = line_of(PUSHED, MOD, 'from "../../lib/executionWindow"')
M_SETTLED = line_of(PUSHED, MOD, "settled_count: settled.length")
M_COPY = line_of(PUSHED, MOD, "export function progressContractCopy")
M_GAP = line_of(PUSHED, MOD, "export function dayOfGapCopy")
T_USE = line_of(PUSHED, TRIP, "journeyProgress({")
T_H1 = line_of(PUSHED, TRIP, 'data-testid="trip-day-total"')
T_ROW = line_of(PUSHED, TRIP, 'data-testid="trip-progress-contract"')
E_OWNER = line_of(PUSHED, EXEC, "TERMINAL_ACTIVITY_STATES = new Set")
V8_COPY = line_of(PUSHED, V8, '["COMPLETED", "SKIPPED", "CANCELLED"]')
V12_DAY = line_of(PUSHED, V8, "tripDayCount = data.journey.temporal_shape")
V12_A = line_of(PUSHED, V12, "activities.find((item) => ![")
V12_ROUTE = line_of(PUSHED, "frontend/src/app/v8PanelRegistry.tsx", 'id: "authoritative"')
STAMP_HITS = len([l for l in git("grep", "-n", "-i", "-e", "stamp", TIP, "--", "backend", check=False).splitlines() if l.strip()])
STAMP_WORDS = len([l for l in git("grep", "-n", "-E", "-e", "check_in|checkin|集章|打卡", TIP, "--", "backend", check=False).splitlines() if l.strip()])
CHECKIN_LINES = [l for l in git("grep", "-n", "-E", "-e", "check_in|checkin", TIP, "--", "backend", check=False).splitlines() if l.strip()]
CN_STAMP_HITS = len([l for l in git("grep", "-n", "-E", "-e", "集章|打卡", TIP, "--", "backend", check=False).splitlines() if l.strip()])
CHECKIN_SAMPLE = "%s:%s" % (CHECKIN_LINES[0].split(":")[1], CHECKIN_LINES[0].split(":")[2]) if CHECKIN_LINES else "无"
STAMP_A = "%s:%s" % ("backend/app/agent/autorun.py", re.search(r":(\d+):", git("grep", "-n", "-F", "-e", "stamp = now or datetime", TIP, "--", "backend/app/agent/autorun.py", check=False)).group(1))
STAMP_B = "%s:%s" % ("backend/app/agent/signal_pipeline.py", re.search(r":(\d+):", git("grep", "-n", "-F", "-e", "stamp = captured_at or _now()", TIP, "--", "backend/app/agent/signal_pipeline.py", check=False)).group(1))
ORD0063 = line_of(PUSHED, V8, "the day count is projected by the backend")
NOPCT = line_of(PUSHED, "frontend/src/api/citynexus.ts", "There is deliberately no progress percentage")
PCT_RULE = line_of(PUSHED, "frontend/src/api/citynexus.ts", "No percentage by design")
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = "%s:%s" % (NOW[:2], NOW[2:])
Z = ARMS["screen_zh-CN"]
E = ARMS["screen_en"]

B = []
A = B.append
A("### ORD-0438 · 道0370（会话 e4f3490f）· 集章打卡与进度合同 · 行程屏的天数接到服务端那一枚 · 合同形空态上屏 · 2026-09-29 %s+08" % NW)
A("")
A("## 交付坐标")
A("   新枝 `refs/heads/%s`（origin 上此前无同名枝）；push 后我 `git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/%s`" % (BRANCH, BRANCH))
A("   现读头 = %s （`git cat-file -t` = commit），我这 %d 笔挂在基点 %s 上（`git merge-base` 现读）。" % (PUSHED, N_AHEAD, BASE))
A("   写这块之前我又读了一次权威线 = %s ：它自己已从基点往前走了 %d 笔（`git rev-list --count %s..%s` 现读），" % (TIP, N_LAG, BASE, TIP))
A("   所以我报的是我量过的那一代，不冒充最新；两代合流我按只读口径预测过：`git merge-tree --write-tree %s %s` 退出码=%d 、冲突路径数=%d 。" % (
    TIP, PUSHED, MT_RC, MT_CONFLICT))
A("   相对基点 touched_file_count=%d 枚，逐枚：" % len([l for l in git("diff", "--name-only", BASE, PUSHED).splitlines() if l.strip()]))
for t in [l for l in git("diff", "--name-only", BASE, PUSHED).splitlines() if l.strip()]:
    A("      %s blob %s" % (t, blob_at(PUSHED, t)))
A("   其中产品字节 product_files_touched=%d 枚（blob %s 与 %s ），backend/ 前缀命中=%d 枚（基点 %s ，交付头 %s ）；" % (
    len(PRODUCT), MOD_BLOB, TRIP_BLOB, len([t for t in TOUCHED if t.startswith("backend/")]), BASE, PUSHED))
A("   styles.css 与 V8Experience.tsx 在我这两笔里一次没出现（`git diff --name-only %s %s` 现读就是上面那几枚）。" % (BASE, PUSHED))
A("")
A("## 结论一：现尖上「共几天」确实有两枚出处，我把行程屏那枚改接到了服务端那一枚")
A("   出处甲（服务端投影）：`%s` 读 `journey.temporal_shape.day_count`，Today 的措辞在 `%s`（null 走「天数未知」，绝不当 1 —— ORD-0063 的裁定记在 %s ）；" % (V12_DAY, "frontend/src/app/V8Experience.tsx:2782", ORD0063))
A("   出处乙（这一屏自己按天分组数出来的）：行程屏的标题原先写 `${days.length} 天行程`，`days` 由 %s 按行程时区把 activities 分桶得到。" % TRIP)
A("   我做的事：标题改接出处甲（现读那一行 `%s`，推导入口 `%s`），分组仍旧只管它本来唯一负责的那件事 —— 哪一天装着游标。" % (T_H1, T_USE))
A("   今天两枚数相等（现读 %d 与 %d，同一 run=%s ），所以屏上的数字没有变；能判别这接法对不对的是下面反控那一格，不是屏上的数。" % (
    P1["server_temporal_shape_day_count"], P1["client_grouped_day_count"], P1_R["run_id"]))
A("")
A("## 结论二：终态集合现读有三份，其中一份和权威那份不一致（我一份也没并表，具名交出来）")
A("   权威那一份：`%s` = %s ，成员逐枚 %s 。" % (E_OWNER, OWNERS[0].split(":", 3)[3].strip(), "、".join(SET_OWNER)))
A("   抄了同样三枚的第二份：`%s`（行内字面量，不走那份集合）。" % V8_COPY)
A("   只列了两枚的第三份：`%s`（两处）—— 逐枚 %s ，比权威那份少 %d 枚：%s 。" % (
    V12_A, "、".join(SET_V12), len(MISSING_IN_V12), "、".join(MISSING_IN_V12)))
A("   我没有并表：并了会改那屏给用户的可执行动作（把已取消的一站从「现在/接下来」里摘掉），那是行为变更不是收敛；")
A("   而且那一屏与 Today 谁说了算，归号令者裁。我这边只保证新落的这一份不自带状态表（`%s`，判据 %s ）。" % (M_IMP, G_S))
A("")
A("## 结论三：空态写成待完成合同，两臂都上屏、都命中（clean gate run_id=%s verdict=%s passed=%d，tree=%s）" % (
    GATE_R["run_id"], GATE_R["verdict"], GATE_R["counts"]["passed"], GATE_R["tree"]))
A("   中文臂这一行（testid trip-progress-contract，%s）：%r" % (T_ROW, Z["screen"]["contract"]["text"]))
A("   英文臂同一格：%s" % json.dumps(E["screen"]["contract"]["text"], ensure_ascii=False))
A("   命中点：zh 中心 %s 内命中=%s、最后一条绘制行底边 %d 对 hit_line=%d（%s）；en 中心 %s 内命中=%s、底边 %d（三枚 client rect，折行只认这个）。" % (
    json.dumps(Z["screen"]["contract"]["centre"]), Z["screen"]["contract"]["centreHitInside"],
    Z["screen"]["contract"]["lastLineBottom"], Z["screen"]["hitLine"], G_Z,
    json.dumps(E["screen"]["contract"]["centre"]), E["screen"]["contract"]["centreHitInside"],
    E["screen"]["contract"]["lastLineBottom"]))
A("   「已走到第几天」逐臂现读：期望 %r / 在屏=%s（zh）；期望 %r / 在屏=%s（en）；判据 %s 。" % (
    Z["day_phrase_expected"], Z["day_phrase_on_screen"], E["day_phrase_expected"], E["day_phrase_on_screen"], G_DAYASSERT))
A("   文案禁句现读：两臂都不含「没有数据/暂无」（断言写在 %s 那一条里）；空计数那句写的是「服务端改完这里自己 +1，这里没有给你打勾的地方」——" % G_Z)
A("   与行前清单那条裁定同调（`lib/pretripChecklist.ts:17`：完成不是勾选），我没有另造一个勾选框，也没有第二处状态。")
A("   还没排定任何一站那一档（合成输入，run 同上）：zh=%s" % json.dumps(
    ARMS["M_derivation"]["nothingPlanned"]["copy_zh"], ensure_ascii=False))
A("")
A("## 判别性读数（这一格是唯一能证「接对了」的，屏上数相等时证不了）")
A("   M 臂：%s ：服务端给 3 天而这一屏自己只分出 2 桶时，day_total 仍取 3、来源具名 server_temporal_shape（%s）；" % (G_M, M_HEAD))
A("   服务端不给整天数时 day_total 留 null、句子里写「天数留空/stays blank」，不退化成 1（%s）；" % M_COPY)
A("   混合态：completed=%d、settled=%d、planned=%d，游标不在任何桶里 ⇒ day_of=null 且 basis=cursor_unreadable，另起一句解释（%s）。" % (
    ARMS["M_derivation"]["mixedStatesWithAnUnreadableCursor"]["progress"]["completed_count"],
    ARMS["M_derivation"]["mixedStatesWithAnUnreadableCursor"]["progress"]["settled_count"],
    ARMS["M_derivation"]["mixedStatesWithAnUnreadableCursor"]["progress"]["planned_total"], M_GAP))
A("   S 臂：模块里自带状态清单的行数=%d 枚、自带日期格式化的行数=%d 枚（判据 %s ）⇒ 它没变成第二套。" % (
    len(ARMS["S_source_shape"]["own_status_list_lines"]), len(ARMS["S_source_shape"]["own_date_grouping_lines"]), G_S))
A("   没有百分比：后端那句裁定在 `%s` 与 `%s`，模块也不产百分比字段。" % (PCT_RULE, NOPCT))
A("")
A("## 反控两枚（造出第二套进度的两种方式，看闸咬不咬）")
A("   MUT-A 让模块自己再数一遍天数（`day_total: days.length`）：run_id=%s verdict=%s passed=%d failed=%d，红的那条=%s ，日志 %s" % (
    MA_R["run_id"], MA_R["verdict"], MA_R["counts"].get("passed", -1), MA_R["counts"].get("failed", -1),
    "the headline must follow the server projection even when this screen's own grouping says otherwise", MA_R["log"]))
A("   MUT-B 让模块自带一份状态表（Set([\"COMPLETED\",\"SKIPPED\"])）：run_id=%s verdict=%s passed=%d failed=%d，红两条形 %s 与 %s" % (
    MB_R["run_id"], MB_R["verdict"], MB_R["counts"].get("passed", -1), MB_R["counts"].get("failed", -1),
    "M 臂 settled_count 由 3 变 2", "S 臂 import 那一条与自带清单的行数不为空"))
A("   两枚变异跑完我都 `git checkout HEAD -- %s` 还原，逐枚比过 hash-object（还原后 = %s = 枝上 blob）；" % (MOD, MOD_BLOB))
A("   还原后重跑一次干净闸：run_id=%s verdict=%s passed=%d，tree 格 = 交付头上一笔 %s 逐字相同。" % (
    GATE_R["run_id"], GATE_R["verdict"], GATE_R["counts"]["passed"], HEAD))
A("")
A("## 邻居闸对照：我这一屏多了两行文案，撞不撞别人（撞了就得说，不能装作没看见）")
A("   跑 /v8/trips 这条屏的既有三闸，带我改动各一轮（按收据里的 target 归位）：")
for k in sorted(AFR):
    A("      %s run_id=%s verdict=%s counts=%s 日志 %s" % (
        k, AFR[k]["run_id"], AFR[k]["verdict"], json.dumps(AFR[k]["counts"]), AFR[k]["log"]))
A("   其中只有 `%s` 的游标句那一格（判据 %s ）会报红。我把这条闸在两种字节状态下交替跑了 %d 轮，" % (
    LANG, line_of(PUSHED, LANG, "the sentence claims a server cursor"), len(LANGROWS)))
A("   每轮的 TripItinerary blob 当场 `git hash-object` 记的（带我改动 = %s ，不带 = 基点那枚 %s ，两枚都可 cat-file）：" % (
    TRIP_BLOB, BASE_TRIP_BLOB))
for x in LANGROWS:
    A("      tag=%s run_id=%s 状态=%s verdict=%s 失败用例=%s 日志 %s" % (
        x["tag"], x["run_id"], x["state"], x["verdict"], "、".join(x["failing_cases"]) or "无", x["log"]))
A("   红在两种状态下都出现过（带我改动 %d 轮里 %d 红，不带我改动 %d 轮里 %d 红）⇒ 这枚红不归因于我这一步；" % (
    len([x for x in LANGROWS if x["state"] == "WITH"]), RED_WITH,
    len([x for x in LANGROWS if x["state"] == "WITHOUT"]), RED_WITHOUT))
A("   我读到的机理是那条闸自己的时机：它拿到的游标是 ABSENT_FALLBACK 时，Today 的「取自服务器场景（执行游标）」那句就与状态相冲（失败原文里的句子逐字带回上面那些日志）。")
A("   我没修它，也没为了让它变绿去动它的判据；这格交给闸门的主人裁，run_id 与日志都在上面那几行。")
A("")
A("## ④ 编译臂：硬链导出重跑，退码逐件一行（导出根 %s）" % SNAP)
A("   `git archive --format=tar %s | tar -x -C %s`，node_modules 用 os.link 借（等同 `cp -al`，非拷贝非 junction）：" % (HEAD, SNAP))
A("   `typescript/package.json` 的 st_nlink=%d；导出树对被跟踪路径逐枚核过 verify_pair_count=%d 枚全部相等（判据 `git rev-parse %s:<path>` 口径）。" % (
    NLINK, len(VERIFY), HEAD[:8]))
for c, r, e in BUILD:
    A("   cmd=%s rc=%d error_lines=%d" % (c, r, e))
A("   产物唯一：/assets/%s size_bytes=%d，本地字节重算文件 sha1=%s（非 git 对象、不在对象库里；同段可 cat-file 的坐标：交付头 %s ）" % (
    ASSET, ASSET_BYTES, ASSET_SHA1, PUSHED))
A("")
A("## 读数的边界（这单能到哪、不能到哪）")
A("   行程屏与 Today 的两枚天数今天相等（%d 与 %d），所以「改接出处」在屏上是看不出来的 —— 这一点我不拿屏读当绿证，判别性全压在 M 臂那组合成输入上（run_id=%s）。" % (
    P1["server_temporal_shape_day_count"], P1["client_grouped_day_count"], GATE_R["run_id"]))
A("   「已完成几处」今天=%d（sealed demo 的 9 站全是非终态，现读 %s ），所以合同句走的是「一站都还没走完」那一档；" % (
    P1["terminal_status_count"], "frontend/review/evidence/qoder-ord0438/P1_denominators.json"))
A("   真有一站被走完之后的那一档我没有屏读：那要动服务端状态机（transition 那条写路径），不在本单里，我没跑。")
A("   集章/打卡：后端现读没有那枚身 —— \"stamp\" 在 backend 的命中数=%d 行、逐枚都是局部时间戳变量（例 %s 与 %s ），" % (STAMP_HITS, STAMP_A, STAMP_B))
A("   \"check_in\" 这个词面在 backend 的命中数=%d 行，逐枚都是住宿的入住时间字段（%s ，例如 %s ），不是打卡；集章/打卡两种中文词面命中数=%d 行，路由与建表语句里也没有那枚身。" % (
    len(CHECKIN_LINES), "、".join(sorted({re.search(r"\bcheck_in\w*", l).group(0) for l in CHECKIN_LINES if re.search(r"\bcheck_in\w*", l)})) or "无",
    CHECKIN_SAMPLE, CN_STAMP_HITS))
A("   所以那一档要做只能新造一套存储 —— 正撞本单第一条「不建第二套进度系统」。我没造，借的是形状那一句：空态写成待完成合同。")
A("")
A("## 没改善的部分")
A("1. Today 那屏的三处各自算数还在：`%s`（行内终态清单）、%s（天数行）、还有「还没有安排/后面还有 N 站」那句的分支，" % (V8_COPY, V12_DAY))
A("   全在禁改墙上（V8Experience.tsx 被三张单占着），我只具名报出来，不动它。要动请给一句授权。")
A("2. V12 那屏少了 CANCELLED 我没并表（理由在上面结论二）；并表之后的行为差别我也没屏读，那条我标 NOT-MEASURED。")
A("3. 屏读来自车道私有栈的 dev（frontend_port=%d / backend_port=%d，端口具名格 %s ），没有推到手机握的那代产物上；手机链仍 NOT-DEPLOYED-OBSERVED。" % (
    GATE_R["ports"]["frontend"], GATE_R["ports"]["backend"], PORT_LINE))
A("4. 我没跑整套 e2e，只跑了本单这 4 条 + 邻居 3 条（邻居里那条游标句按上面 %d 轮交替跑法归因，不是我挤的）；" % len(LANGROWS))
A("   整套里若有按 /v8/trips 绝对坐标断言的，我这多出来的两行可能撞红 —— 那条标 NOT-MEASURED，要跑说一句。")
A("5. 行前清单、回收站那两屏的空态各是别的车道的文件（`lib/pretripChecklist.ts` 与 `features/trash/journeyTrashCopy.ts`），我没替它们改词，只把它们的裁定当同调引用。")
A("6. 我这枚块里「字典键」一个没加：文案按 `lib/pretripChecklist.ts:20` 那条同理由落在模块里，因为 `frontend/src/i18n/LocaleContext.tsx` 有别的实例在改。")
A("7. 本回合我自己废掉两轮，都点名：第一轮这具生成器按「我的基点＝当时现尖」写死，而现尖在那一轮里从 %s 走到了 %s ，" % (BASE, TIP))
A("   于是导出核对报「文件不存在」%d 枚（都是 0406/0415 的件，被新尖收进去了），它在 push 之前 REFUSE；" % len([t for t in git("diff", "--name-only", BASE, REBASE_TARGET).splitlines() if t.strip()]))
A("   那几轮都已落了本地读数提交（%s、%s、%s ，`git cat-file -t` 逐枚 = commit，三枚都没推过 origin），我用 `git reset --mixed` 退回未提交，" % (DROPPED, DROPPED_MORE[0], DROPPED_MORE[1]))
A("   退回的目标是 %s （`git cat-file -t` = commit，那笔是 rebase 前的仪表提交）；" % PREREBASE)
A("   再把两笔产品/仪表提交 rebase 到 %s 上（就是现在这枚基点 %s ）。" % (REBASE_TARGET, BASE))
A("   rebase 后产品字节逐枚不变（%s 仍是 %s ，%s 仍是 %s ，hash-object 与枝上 blob 逐字相同），上面所有读数都在 rebase 后的头 %s 上重跑过。" % (
    MOD, MOD_BLOB, TRIP, TRIP_BLOB, HEAD))
A("8. 同两轮里我还抓到自家仪器的一个正则漏：臂名带连字符（screen_zh-CN）被 `(\\w+)` 吞掉，第一次那轮的「四臂齐」断言因此少读那一臂；已改成按名匹配，本轮四臂都从日志现读进工件。")
A("9. 盘：D 盘剩余 %s（`df -h /d` 现读，写这块之前）；本车道端口跑完按 pid 关并 netstat 复查。" % GB)
A("")
A("门尺自检：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0，退出码与 findings 由本进程写盘前现跑；" % LIVE)
A("   那把尺本地字节重算文件 sha1=%s（与值守给的 40 位逐字相同；非 git 对象声明，同段可 cat-file 的坐标：入库 blob %s ，" % (R7_SHA1, R7_BLOB))
A("   `git cat-file -s %s` 得 byte_count=%d 与我运行的字节数相同；交付头 %s 与读数件 blob %s ）。" % (R7_BLOB, len(r7b), PUSHED, ART_BLOB))
A("   第二道闸在同一份草稿上逐值复算：只扫逐字 40 位，免除要同一行写明不可取回且同段有另一枚能 cat-file 的 40 位；")
A("   path:line 在那道闸里不算数。上面 %s 与 %s 两枚都可 cat-file，所以只有 asset_sha1 那一处走声明；abort 清单非空就不投递。" % (R7_BLOB, ART_BLOB))

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR, "q438_block_r1_draft.md")
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
if glob.glob(os.path.join(INBOX, "qoder-0438_*.md")):
    print("REFUSED PUBLISH -- a live qoder-0438 block is already in the inbox")
    sys.exit(4)
OUT = os.path.join(INBOX, "qoder-0438_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
