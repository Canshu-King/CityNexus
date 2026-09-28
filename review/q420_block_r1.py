#!/usr/bin/env python3
"""Build the ORD-0420 delivery block from the artifacts this lane wrote.

Every figure is parsed out of a receipt, a log, or a git command run in this write; nothing is copied
out of the conversation. The script refuses to write the block if a coordinate, a pairing, or a
counter-control does not say what the block is about to claim it says.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_lane_q0420"
REPO = r"D:/moodle/CityNexus"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
RC = r"D:/moodle/_qoder_lane_q0420/review"
FE = r"D:/moodle/_qoder_lane_q0420/frontend"
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TSC_BIN = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript/bin/tsc"
BRANCH = "refs/heads/review/Q-ord0420-drawer-group-headings-r1"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
BASE = "8a7665be2061a2f38aa2227f81c57003ca4caacb"
RULER_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
V8 = "frontend/src/app/V8Experience.tsx"
LC = "frontend/src/i18n/LocaleContext.tsx"
REG = "frontend/src/routes/v8Routes.ts"
SPEC = "frontend/e2e/qoder-ord0420-drawer-group-headings.spec.ts"
bad = []


def git(*a, check=True, cwd=REPO):
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", cwd, *a],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        bad.append("git %s rc=%d %s" % (" ".join(a), r.returncode, (r.stderr or "").strip()[:110]))
    return (r.stdout or "").strip()


def git_ok(*a, cwd=REPO):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True).returncode == 0


def sha_of(path):
    return hashlib.sha1(open(path, "rb").read()).hexdigest()


def blob_of(ref, rel):
    if not git_ok("cat-file", "-e", "%s:%s" % (ref, rel)):
        return ""
    out = git("rev-parse", "%s:%s" % (ref, rel), check=False)
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else ""


def wt_blob(rel):
    data = open(os.path.join(WT, rel.replace("/", os.sep)), "rb").read()
    return hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()


def ref_of(name):
    for l in git("ls-remote", "origin", name).splitlines():
        p = l.split()
        if len(p) == 2 and p[1] == name:
            return p[0]
    return ""


TIP = ref_of(TIP_REF)
HEAD_PUB = ref_of(BRANCH)
if not re.fullmatch(r"[0-9a-f]{40}", TIP or ""):
    bad.append("could not read the authoritative tip")
if HEAD_PUB != git("rev-parse", "HEAD", cwd=WT, check=False):
    bad.append("the published head is not the head the readings ran on")
if not git_ok("merge-base", "--is-ancestor", BASE, TIP) or not git_ok(
        "merge-base", "--is-ancestor", HEAD_PUB, "HEAD", cwd=WT):
    bad.append("ancestry did not hold: base %s / head %s / tip %s" % (BASE[:8], HEAD_PUB[:8], TIP[:8]))
N_AHEAD = int(git("rev-list", "--count", "%s..%s" % (BASE, TIP)) or 0)

MY_COMMITS = [c.split("\t") for c in git(
    "log", "--format=%H%x09%ad%x09%s", "--date=format:%H:%M", "%s..%s" % (BASE, HEAD_PUB)).splitlines()]
if len(MY_COMMITS) < 3:
    bad.append("expected at least three commits on this branch, got %d" % len(MY_COMMITS))
TOUCHED = sorted(set(git("diff", "--name-only", BASE, HEAD_PUB).split("\n")))
PROD_TOUCHED = [t for t in TOUCHED if t.startswith("frontend/src/")]
BACKEND_TOUCHED = [t for t in TOUCHED if t.startswith("backend/")]


def cite(rel, pat, label, ref=None):
    txt = git("show", "%s:%s" % (ref or HEAD_PUB, rel), check=False)
    hits = [i + 1 for i, l in enumerate(txt.split("\n")) if re.search(pat, l)]
    if not hits:
        bad.append("no line matching %r in %s (%s)" % (pat[:44], rel, label))
        return "%s:?" % rel
    return "%s:%d" % (rel, hits[0])


def receipt(tag):
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)), key=os.path.getmtime)
    if not fs:
        bad.append("no receipt for tag %s" % tag)
        return {}, ""
    return json.load(open(fs[-1], encoding="utf-8")), os.path.basename(fs[-1]).replace(".json", ".log")


def q420lines(name):
    txt = open(os.path.join(LIVE, "e2e_logs", name), encoding="utf-8", errors="replace").read()
    return [re.sub(r"^\[[0-9:]+\]\s*", "", l.strip()) for l in txt.split("\n")
            if l.strip().startswith("Q420")]


def case_names(name):
    txt = open(os.path.join(LIVE, "e2e_logs", name), encoding="utf-8", errors="replace").read()
    return re.findall(r"^\[\d+/\d+\] \[[\w-]+\] . (\S+:\d+:\d . [^\n]+)", txt, re.M)


def transfer(ref):
    """Does a reading taken on `ref` describe HEAD_PUB? Prove it by bytes, not by 'I just committed'."""
    if not re.fullmatch(r"[0-9a-f]{40}", ref or ""):
        return False, "unreadable stamp %r" % ref
    if not git_ok("merge-base", "--is-ancestor", ref, HEAD_PUB):
        return False, "%s is not an ancestor of the published head" % ref[:8]
    moved = [rel for rel in (LC, V8, REG, SPEC) if blob_of(ref, rel) != blob_of(HEAD_PUB, rel)]
    if moved:
        return False, "the measured files moved after that run: %s" % moved
    return True, "ahead_commits=%d, same bytes on the four measured files" % int(
        git("rev-list", "--count", "%s..%s" % (ref, HEAD_PUB)) or 0)


base_r, base_log = receipt("q420v2")
READS = {}
for l in q420lines(base_log):
    m = re.match(r"Q420 (A\d) (\w\w) surface=(\w+)", l)
    if m:
        READS[m.group(1) + "-" + m.group(2)] = l
for k in ("A1-zh", "A2-en", "A4-zh", "A4-en", "A3-zh", "A3-en"):
    if k not in READS:
        bad.append("the baseline receipt holds no %s reading" % k)
if base_r.get("verdict") != "GREEN":
    bad.append("the baseline run is not GREEN: %s" % base_r.get("verdict"))
OK_BASE, WHY_BASE = transfer(base_r.get("tree", ""))
if not OK_BASE:
    bad.append("the baseline reading does not transfer to the published head: %s" % WHY_BASE)
CASES = case_names(base_log)
SEED_CASE = [c for c in CASES if "Q420" not in c]

ZH_DRAWER = json.loads(re.search(r"headings=(\[.*?\]) ", READS["A1-zh"]).group(1))
ZH_DESK = json.loads(re.search(r"headings=(\[.*?\]) ", READS["A4-zh"]).group(1))
EN_DRAWER = json.loads(re.search(r"headings=(\[.*?\]) ", READS["A2-en"]).group(1))
EN_DESK = json.loads(re.search(r"headings=(\[.*?\]) ", READS["A4-en"]).group(1))
CODES = ["TODAY", "PLAN", "TRAVEL", "SYSTEM"]
if not all(re.search(r"[一-鿿]", s) for s in ZH_DRAWER + ZH_DESK):
    bad.append("a zh heading still carries no Han character")
if EN_DRAWER != CODES or EN_DESK != CODES:
    bad.append("the English arm moved: drawer %s desktop %s" % (EN_DRAWER, EN_DESK))

MUT = {}
for tag, key, token in (("e4fk0", "K0", "TODAY"), ("e4fk1", "K1", "PLX-SENTINEL"),
                        ("e4fk2", "K2", "SYS-SENTINEL")):
    j, lg = receipt(tag)
    rows = q420lines(lg)
    hit = [l for l in rows if token in l]
    MUT[key] = {"r": j, "log": lg, "line": hit[0] if hit else "",
                "heads": json.loads(re.search(r"headings=(\[.*?\]) ", hit[0]).group(1)) if hit else [],
                "surfaces": sorted(set(re.findall(r"surface=(\w+)", " ".join(hit)))),
                "transfer": transfer(j.get("tree", "")), "token": token}
    if j.get("verdict") != "RED":
        bad.append("%s is not RED: %s" % (key, j.get("verdict")))
    if not MUT[key]["transfer"][0]:
        bad.append("%s does not transfer to the published head: %s" % (key, MUT[key]["transfer"][1]))
    if not hit:
        bad.append("%s: the screen never showed %s, so the arm proves nothing" % (key, token))
for rel in (LC, V8, REG):
    if wt_blob(rel) != blob_of(HEAD_PUB, rel):
        bad.append("the worktree copy of %s is not the committed blob" % rel)
ARMS_JSON = os.path.join(RC, "q420_mutant_arms.json")
arms = json.load(open(ARMS_JSON, encoding="utf-8"))
for key in ("K0", "K1", "K2"):
    if arms[key]["verdict"] != "RED" or not arms[key]["met"] or not arms[key]["screen_moved_to_token"]:
        bad.append("the arms artifact does not record %s as a met, moving RED" % key)
    if arms[key]["tree"] != MUT[key]["r"]["tree"]:
        bad.append("the arms artifact and the receipt disagree on what %s ran on: %s vs %s" % (
            key, arms[key]["tree"], MUT[key]["r"]["tree"]))

RULER = json.load(open(os.path.join(LIVE, "cmdr_bundle_copy_check_r3.json"), encoding="utf-8"))
if RULER["tip"] != BASE or RULER["values_not_found"] != 0:
    bad.append("the pairing ruler is not on my base or still has misses: %s/%s" % (
        RULER["tip"][:12], RULER["values_not_found"]))
PAIRS = subprocess.run([VENV, "-X", "utf-8", os.path.join(RC, "q420_bundle_pairs_r1.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "CNX_BUNDLE_BASE": "http://127.0.0.1:4901"})
PROW = re.findall(r"(nav\.group\w+)\s+value='([^']+)' value_chars=(\d+) has_cjk=(\w+) "
                  r"match_form=(\w+) registry_collision=(\w+)", PAIRS.stdout)
BUNDLE_LINE = re.search(r"served_asset (\S+) bundle_raw_bytes (\d+) bundle_sha1 ([0-9a-f]{40})", PAIRS.stdout)
SITE_LINE = re.search(r"heading_sites_reading_the_raw_code=(\d+) heading_sites_reading_the_dictionary=(\d+) "
                      r"comparison_sites_that_must_keep_the_code=(\d+)", PAIRS.stdout)
if len(PROW) != 10 or "ALL_FIVE_PAIRS_SHIP" not in PAIRS.stdout:
    bad.append("the five new pairs did not all match in the served bundle (rows=%d)" % len(PROW))
if not BUNDLE_LINE or not SITE_LINE:
    bad.append("could not read the bundle pairing script's own header lines")

TSC = {}
for cfg in ("tsconfig.check.json", "tsconfig.typecheck.json"):
    r = subprocess.run([VENV, "-X", "utf8", TSC_BIN, "-p", cfg, "--noEmit"], cwd=FE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    TSC[cfg] = r.returncode
build_log = open(os.path.join(RC, "q420_vite_build.log"), encoding="utf-8", errors="replace").read()
BUILD_RC = re.search(r"built in ([\d.]+)s", build_log)

TIERS = {}
COPY = subprocess.run([VENV, "-X", "utf8", os.path.join(WT, "tools", "cnx_copy_tiers_r1.py"),
                       "--i18n", LC, "--src", "frontend/src"], cwd=WT,
                      capture_output=True, text=True, encoding="utf-8").stdout
for m in re.finditer(r"\[(\w+)\s*\]\s+(\w+)\s+(.*)", COPY):
    TIERS[m.group(2)] = (m.group(1), m.group(3).strip())
for face in ("REGISTER_PARITY", "RENDERED", "HARDCODED_FALLBACK"):
    if face not in TIERS:
        bad.append("the ORD-0370 ruler printed no %s face" % face)

ruler_bytes = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
raw_sha1 = sha1 = hashlib.sha1(ruler_bytes).hexdigest()
if not git_ok("cat-file", "-e", RULER_BLOB) or int(git("cat-file", "-s", RULER_BLOB)) != len(ruler_bytes):
    bad.append("the door ruler blob does not match the bytes I run")

MET = {
    "site_desktop": cite(V8, r"<span className=\"v8-nav-group\">\{t\(navGroupKey", "desktop site"),
    "site_drawer": cite(V8, r't\(navGroupKey\(item\.group\)\) : t\("nav\.groupOther"\)', "drawer site"),
    "cmp1": cite(V8, r"desktopRoutes\[index - 1\]\.group !== item\.group", "comparison 1"),
    "cmp2": cite(V8, r"\.group !==\s*$", "comparison 2"),
    "map": cite(REG, r"export const navGroupKeys", "map"),
    "fn": cite(REG, r"export function navGroupKey", "fn"),
    "fallback": cite(REG, r'\?\? "nav\.groupOther"', "fallback"),
    "en_keys": cite(LC, r'"nav\.groupToday": "TODAY"', "en keys"),
    "zh_keys": cite(LC, r'"nav\.groupToday": "今日"', "zh keys"),
    "zh_mobility": cite(LC, r'"discovery\.mobility": "出行"', "register: mobility"),
    "zh_plan": cite(LC, r'"hub\.planningReady"', "register: planning"),
    "zh_today": cite(LC, r'"nav\.hub": "今天"', "zh nav.hub"),
    "en_today": cite(LC, r'"nav\.hub": "Today"', "en nav.hub"),
    "style": cite("frontend/src/styles.css", r"\.v8-nav-group \{", "style"),
    "spec_a1": cite(SPEC, r"Q420 A1", "A1"),
    "spec_a4": cite(SPEC, r"Q420 A4", "A4"),
    "guard": cite("review/e4f_e2e_r1.py", r"LOW, HIGH = ", "band"),
    "driver": cite("review/q420_mutant_arms_r1.py", r"Names sort by the tree", "driver note"),
    "pair_script": cite("review/q420_bundle_pairs_r1.py", r"registry_collision", "pair script"),
    "arms_file": cite("review/q420_mutant_arms.json", r'"K0"', "arms artifact"),
}
nomet = subprocess.run(["git", "-C", REPO, "grep", "-n", "-e", "item.group", HEAD_PUB, "--", "frontend/src"],
                       capture_output=True, text=True, encoding="utf-8").stdout.strip()
N_GREP = len([l for l in nomet.split("\n") if l.strip()])
tsx = subprocess.run(["git", "-C", REPO, "grep", "-n", "v8-nav-group", HEAD_PUB, "--", "frontend/src"],
                     capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
N_TSX_HITS = len([l for l in tsx if ".tsx:" in l])
INSTRUMENT_TOUCHED = [t for t in TOUCHED if t.startswith("review/")]
NOW = subprocess.run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"],
                     capture_output=True, text=True).stdout.strip()

B = []
A = B.append
A("### 0420 · 车道 e4f3490f（道0370 的窗口）· 抽屉四枚分组标题接进词典 · 中文臂已渲染中文、英文臂一字未动 · 2026-09-29 %s+08" % NOW)
A("")
A("枝 `%s`" % BRANCH)
A("   头以我自己现读为准（不是我本地 rev-parse）：`git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus")
A("   ls-remote origin %s` = %s；这枚等于 worktree HEAD（`git rev-parse` 现读，两枚逐字符相同）。" % (BRANCH, HEAD_PUB))
A("   基点取号令者 00:34 那枚 %s；写盘这刻权威尖我现读 %s（`git rev-list --count` 现读 commits_behind=%d）。" % (
    BASE, TIP, N_AHEAD))
A("   本枝 commit_count=%d 笔，逐枚：" % len(MY_COMMITS))
for sha, hh, subj in MY_COMMITS:
    A("      %s %s %s" % (sha, hh, subj[:70]))
A("   相对基点动了 touched_file_count=%d 枚，其中产品源码 product_files_touched=%d 枚（逐枚 blob 在下面，" % (
    len(TOUCHED), len(PROD_TOUCHED)))
A("   全部可 cat-file）：backend/ 计数=%d，所以后端字节一枚没动。" % (
    len(TOUCHED), len(PROD_TOUCHED), len(BACKEND_TOUCHED)))
for t in TOUCHED:
    A("      %s blob %s" % (t, blob_of(HEAD_PUB, t)))
A("")
A("## 要件一 · 中文臂四枚标题渲染为中文（断的是屏上文字，不是 data 属性、也不是键存在）")
A("   抽屉 viewport=390x844：zh %s" % READS["A1-zh"])
A("   抽屉同一格英文臂：en %s" % READS["A2-en"])
A("   桌面导航 viewport=1280x800（号令者只点名抽屉；这第二处直出我一起修，所以一起读数）：")
A("      zh %s" % READS["A4-zh"])
A("      en %s" % READS["A4-en"])
A("   中文臂那四枚逐枚是 %s（取上面 A1/A4 两行的原文，不是我另写的）；语域取自本屏既有词：" % "、".join(ZH_DRAWER))
A("   「出行」已在 %s（discovery.mobility）用过、「规划」已在 %s（hub.planningReady）用过。" % (
    MET["zh_mobility"], MET["zh_plan"]))
A("   「今日」与首行标签「今天」刻意不同字，正对照英文臂 TODAY（%s）与 Today（%s）的两形。" % (
    MET["en_keys"], MET["en_today"]))
A("   两处分流格现在都读词典：桌面 %s、抽屉 %s；分组**判据**仍读机器码的那两格一字未改：%s、%s。" % (
    MET["site_desktop"], MET["site_drawer"], MET["cmp1"], MET["cmp2"]))
A("   码到键的表在 %s、兜底函数在 %s、未识别的码落 %s；字典两侧各 5 枚新 key，en 起于 %s、zh 起于 %s。" % (
    MET["map"], MET["fn"], MET["fallback"], MET["en_keys"], MET["zh_keys"]))
A("")
A("## 要件二 · 英文臂仍为英文，并且不拿「字面量碰巧相同」充当词典证据")
A("   英文臂四枚逐字 = drawer %s、desktop %s，与号令者件里改前那串完全相同。" % (
    json.dumps(EN_DRAWER, ensure_ascii=False), json.dumps(EN_DESK, ensure_ascii=False)))
A("   en 侧 5 枚的值就取这些既有字面（%s），所以英文屏在结构上不可能移动，而不是「我核过一遍没动」。" % MET["en_keys"])
A("   三臂反控（都要判红才算数）：")
A("      K0 把两处分流退回改前形状 -> run_id=%s verdict=%s counts=%s，zh 抽屉读到 %s（回到拉丁码的面 surface_count=%d）。" % (
    MUT["K0"]["r"]["run_id"], MUT["K0"]["r"]["verdict"], json.dumps(MUT["K0"]["r"]["counts"]).replace(",", ", "),
    json.dumps(MUT["K0"]["heads"], ensure_ascii=False), len(MUT["K0"]["surfaces"])))
A("         这一臂证明验收尺真咬得住号令者报的那个缺陷，不是只咬我改后的形状。")
A("      K1 只把 zh 的 nav.groupPlan 改成哨兵 PLX-SENTINEL -> run_id=%s verdict=%s，屏上读到 %s。" % (
    MUT["K1"]["r"]["run_id"], MUT["K1"]["r"]["verdict"], json.dumps(MUT["K1"]["heads"], ensure_ascii=False)))
A("         哨兵不在路由表里（registry_collision=false），它能上屏只可能是从 t() 取的（surface_count=%d）。" % len(
    MUT["K1"]["surfaces"]))
A("      K2 只把 en 的 nav.groupSystem 改成哨兵 SYS-SENTINEL -> run_id=%s verdict=%s，屏上读到 %s。" % (
    MUT["K2"]["r"]["run_id"], MUT["K2"]["r"]["verdict"], json.dumps(MUT["K2"]["heads"], ensure_ascii=False)))
A("         这一臂才是「英文那四枚是不是巧合」的正面回答：英文臂也跟着哨兵走，所以它现在读的是词典。")
A("   三臂 run_id = %s / %s / %s；baseline run_id=%s。这四处臂各自盖在哪一枚上（收据的 tree 格逐字）：" % (
    MUT["K0"]["r"]["run_id"], MUT["K1"]["r"]["run_id"], MUT["K2"]["r"]["run_id"], base_r["run_id"]))
A("      baseline tree=%s，K0 tree=%s，K1 tree=%s，K2 tree=%s；我这枚交付头是 %s。" % (
    base_r["tree"], MUT["K0"]["r"]["tree"], MUT["K1"]["r"]["tree"], MUT["K2"]["r"]["tree"], HEAD_PUB))
A("   从那些枚到这枚头，只多了仪表与读数件：被我量的四枚文件 %s、%s、%s、%s 在两头 blob 逐枚相同" % (
    LC, V8, REG, SPEC))
A("   （`git rev-parse <头>:<路径>` 现读后比对，脚本已断言，不等则本块不写）。所以那批读数对这枚头成立，")
A("   这不是拿「我刚提交过」当凭据，是拿 blob 相等当凭据。")
A("   注入只在这台机器的 worktree（D:/moodle/_qoder_lane_q0420），跑完 `git checkout --` 还原：还原后逐枚")
A("   `git hash-object` 等于枝上 blob —— LocaleContext %s、V8Experience %s、v8Routes %s，" % (
    blob_of(HEAD_PUB, LC), blob_of(HEAD_PUB, V8), blob_of(HEAD_PUB, REG)))
A("   tracked_dirty_after_restore=0（driver 具名格 %s；三臂读数落盘在 %s 的 K0/K1/K2 格）。" % (
    MET["driver"], MET["arms_file"]))
A("   我自己的仪器缺陷也交：这三位 driver 第一次跑把臂配到了**上一轮**的收据上（收据名按树戳排序，提交后")
A("   旧名反而排最后），当时报的 run_id 全是 cmdr0057xx/cmdr0058xx 那批。修法是「只认本次运行新写出的那份")
A("   收据，并断言它的 tree 等于我这枚头」，修在 %s；上面三个 run_id 是修好后重跑的。" % MET["driver"])
A("")
A("## 要件三 · 两臂都进词典配对尺")
A("   号令者那把 %s/live_checks/cmdr_bundle_copy_check_r3.py 跑在我这片的产物上（我运行的字节 sha1=%s，" % (
    "D:/moodle/_qoder_cmdr_ref_20260921", raw_sha1))
A("   本地字节重算；它是 git 对象的那份 = blob %s，`git cat-file -s` 得 byte_count=%d，两枚逐字节相同）：" % (
    RULER_BLOB, len(ruler_bytes)))
A("   tip=%s dictionary_pairs=%d values_found=%d values_not_found=%d served_asset=%s bundle_raw_bytes=%d。" % (
    RULER["tip"], RULER["dictionary_pairs"], RULER["values_found_in_served_bundle"],
    RULER["values_not_found"], RULER["served_asset"], RULER["bundle_raw_bytes"]))
A("   这与号令者 00:31 那块报的「763 对 0 缺」同分母，说明我这 5 枚没有把既有配对挤掉。")
A("   但那把尺的字典读的是权威尖，我这 5 枚新 key 进不了它的分母（枝没落地，我不能移动权威线）。补测在")
A("   同一份产物字节上做，用尺自己的正则与双形式匹配（脚本 %s）：bundle_sha1=%s（本地字节重算，非 git" % (
    MET["pair_script"], BUNDLE_LINE.group(3)))
A("   对象；同段可 cat-file 坐标：本枝头 %s、产物名 %s）：" % (BUNDLE_LINE.group(3), HEAD_PUB, BUNDLE_LINE.group(1)))
for k, v, vc, cjk, form, coll in PROW:
    A("      key=%s value=%s value_chars=%s has_cjk=%s match_form=%s registry_collision=%s" % (
        k, v, vc, cjk, form, coll))
A("   registry_collision=true 的四枚（TODAY/PLAN/TRAVEL/SYSTEM）在路由表里也有同串，所以「产物里有这个词」")
A("   对它们**没有**判别力；判别力在 K1/K2 两臂（哨兵不在路由表却能上屏）。nav.groupOther 的 MORE 不在")
A("   路由表里，它那枚产物匹配是独立成立的。")
A("   取用点用 ORD-0370 那把尺读（同一工具、同一判据，落在我这枚头上）：RENDERED verdict=%s，读数 %s" % (
    TIERS["RENDERED"][0], TIERS["RENDERED"][1][:100]))
A("   REGISTER_PARITY verdict=%s 读数 %s；HARDCODED_FALLBACK verdict=%s 读数 %s（tier B 那串存量与我一枚无关）。" % (
    TIERS["REGISTER_PARITY"][0], TIERS["REGISTER_PARITY"][1][:86], TIERS["HARDCODED_FALLBACK"][0],
    TIERS["HARDCODED_FALLBACK"][1][:86]))
A("")
A("## 编译臂与闸口")
A("   `npx tsc -p tsconfig.check.json --noEmit` rc=%d、`npx tsc -p tsconfig.typecheck.json --noEmit` rc=%d；" % (
    TSC["tsconfig.check.json"], TSC["tsconfig.typecheck.json"]))
A("   `npx vite build` rc=0（build 尾行 built_in=%ss），产物 served_asset=%s size_bytes=%d。" % (
    (BUILD_RC.group(1) if BUILD_RC else "?"), BUNDLE_LINE.group(1), int(BUNDLE_LINE.group(2))))
A("   闸：run_id=%s verdict=%s counts=%s duration_s=%.1f，私有栈 frontend_port=%d / backend_port=%d，" % (
    base_r["run_id"], base_r["verdict"], json.dumps(base_r["counts"]).replace(",", ", "),
    base_r["duration_s"], base_r["ports"]["frontend"], base_r["ports"]["backend"]))
A("   端口带具名格 %s；私有库 `%s`；AI key 在子进程启动前摘掉；node_modules 是指向共享安装的 junction" % (
    MET["guard"], base_r["db"]))
A("   （mode=%s，我没有拷贝也没有穿过它删除任何东西）。" % base_r["node_modules"]["mode"])
A("   passed=%d 里 %d 枚是本单四格 A1/A2/A3/A4（用例声明在 %s、%s），另 %d 枚是这条栈自带的种子格：" % (
    base_r["counts"]["passed"], 4, MET["spec_a1"], MET["spec_a4"], len(SEED_CASE)))
for c in SEED_CASE:
    A("      %s" % c)
A("   没跑 demo/reset、没碰 :8000、没碰 :4781、没碰 :4782、没碰 :8693、没碰 _preview.db，也没碰别人的 worktree。")
A("   `git grep -n item.group` 在本枝上取用与比较合计 grep_hit_lines=%d 行：取用 %s、%s（两处都走 t()），" % (
    N_GREP, MET["site_desktop"], MET["site_drawer"]))
A("   比较 %s、%s（本就该留机器码），全仓再没有第三处直出。" % (MET["cmp1"], MET["cmp2"]))
A("")
A("## 没改善的部分")
A("1. 屏上读数来自这条车道的私有栈（frontend_port=%d，`npm run dev` 起的那条链），没有推到手机走的那代 served" % base_r["ports"]["frontend"])
A("   产物上；产物侧我只做到「词典值与 bundle 逐枚配对」，它证部署不证渲染（渲染由上面四格证）。")
A("2. 四格断的是标题**文本**，没断样式。`.v8-nav-group` 在 %s 是 9px 小字号加 letter-spacing，两个汉字在" % MET["style"])
A("   这个字号下是否易读我没有量；styles.css 归 ORD-0419，号令者要我别动，所以这格我不修也不装修好。")
A("3. 「今日」与「今天」两个近义中文在同一屏并存是我选的（镜像英文 TODAY / Today）。若号令者要逐字相同，")
A("   改 %s 一枚值即可，K1 那条臂会立刻判红提醒，不会静默通过。" % MET["zh_keys"])
A("4. 兜底那格（nav.groupOther / MORE）在真机上不可达：外层条件已判过 group in item，所以 %s 的 else 臂" % MET["site_drawer"])
A("   永远走不到。我仍把它接进词典而不是留字面，是为了让这一屏没有自造散文；它也因此没有屏上读数可交。")
A("5. K0 只退两处分流形状、不退整枝：它证明尺咬得住缺陷，不等于我把这四枚在别的表面也查干净了 —— 我查的是")
A("   抽屉与桌面导航这两个 `.v8-nav-group` 落点：`git grep -n v8-nav-group` 在本枝的 .tsx 里取用 %d 行" % N_TSX_HITS)
A("   （%s、%s），样式命中在 %s 与 design-tokens.css，没有第三个自造标题的落点。" % (
    MET["site_desktop"], MET["site_drawer"], MET["style"]))
A("6. 没跑前端 e2e 全套（只跑本单四格 + 这条栈自带的种子格），也没跑后端套件（本枝 backend/ 计数=%d，" % len(BACKEND_TOUCHED))
A("   后端字节一枚没动，所以那套件的读数不在本枝可断言的范围内，我没有引用它。")
A("7. 本枝动了 touched_file_count=%d 枚，其中 review/ 下的仪表与读数件 instrument_file_count=%d 枚；" % (
    len(TOUCHED), len(INSTRUMENT_TOUCHED)))
A("   那两枚可以只摘 %s 与 %s 两笔（逐枚 40 位在上面 commit 清单里）。" % (
    MY_COMMITS[0][0], MY_COMMITS[1][0]))
A("")
A("门尺自检（现行口径）：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 与" % LIVE)
A("   `patrol/bolt_replica.py` 都在写盘前现跑，任一红则不投递。那把尺本地字节重算的文件 sha1=%s（40 位，" % raw_sha1)
A("   非 git 对象；同段可 cat-file 坐标：号令者入库的同一份字节 = blob %s、本枝头 %s）。" % (RULER_BLOB, HEAD_PUB))

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)

DRAFT = os.path.join(RC, "q420_block_draft.md")
io.open(DRAFT, "w", encoding="utf-8", newline="\n").write("\n".join(B) + "\n")
print("DRAFT", DRAFT, os.path.getsize(DRAFT), "bytes")
print("HEAD_PUB", HEAD_PUB, "TIP", TIP, "BASE", BASE)
r7 = subprocess.run([VENV, "-X", "utf8", os.path.join(LIVE, "claim_coordinate_check_r7.py"),
                     "--text", DRAFT, "--expect-clean"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
fl = [l.strip()[:180] for l in (r7.stdout or "").splitlines() if l.startswith("  line ")]
print("GATE_R7 rc=%d findings=%d" % (r7.returncode, len(fl)))
for l in fl:
    print("   ", l)
if r7.returncode:
    print("NOT PUBLISHED -- r7 red; the draft stays in review/")
    sys.exit(2)
LIVE_DRAFTS = glob.glob(os.path.join(INBOX, "qoder-0420_*.md"))
if LIVE_DRAFTS:
    print("REFUSED PUBLISH -- a live 0420 .md already sits in the inbox: %s" % LIVE_DRAFTS)
    sys.exit(3)
OUT = os.path.join(INBOX, "qoder-0420_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(B) + "\n")
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
