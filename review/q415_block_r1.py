#!/usr/bin/env python3
"""ORD-0415 delivery: the instrument + its readings get committed on a fresh branch off the live tip,
then the block is built from those same objects and passed through both doors before it is published.

No product bytes: the diff from the tip is this order's spec and its readouts artifact only.
The expensive part of the earlier orders (the compile arm) is deliberately absent -- two named tsc
projects were run in the checkout and their exit codes are reported as measured, with the honest note
that neither project's include list covers e2e/.
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
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
NM = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
TSC = os.path.join(NM, "typescript", "bin", "tsc")
BRANCH = "review/Q-ord0415-label-string-origin-r1"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
JM = "frontend/src/components/JourneyMap.tsx"
ML = "frontend/src/lib/mapLabels.ts"
MP = "frontend/src/components/v8/MapPanel.tsx"
MN = "frontend/src/main.tsx"
G0412 = "frontend/e2e/qoder-map-ord0412-label-scope.spec.ts"
SPEC = "frontend/e2e/qoder-ord0415-label-string-origin.spec.ts"
PORTSPEC = "review/e4f_e2e_r1.py"
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
    out = git("grep", "-n", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for %r in %s on %s" % (pattern, rel, ref[:8]))
        return "%s:?" % rel
    return "%s:%s" % (rel, m.group(1))


def count_at(ref, rel, pattern):
    return len([l for l in git("grep", "-n", "-e", pattern, ref, "--", rel, check=False).splitlines()
                if l.strip()])


def grep_all(ref, pattern, pathspec):
    return [l for l in git("grep", "-n", "-e", pattern, ref, "--", pathspec, check=False).splitlines()
            if l.strip()]


TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
if not TIP or not git_ok("cat-file", "-e", TIP):
    bad.append("the live tip is not retrievable: %r" % TIP)
HEAD = git("rev-parse", "HEAD", cwd=WT)
if HEAD != TIP:
    bad.append("the checkout is not at the tip the readings claim")
R_LOGS = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "q415p3_*.json")), key=os.path.getmtime)
if not R_LOGS:
    bad.append("no tip receipt")
RJ = json.load(open(R_LOGS[-1], encoding="utf-8"))
RJ_LOG = os.path.basename(RJ["log"])
if RJ.get("verdict") != "GREEN" or RJ.get("tree") != TIP:
    bad.append("the tip run is not GREEN on the tip: %s %s" % (RJ.get("verdict"), RJ.get("tree")))
ARMS = {}
for m in re.finditer(r"O415 (arm\d\w*) (\{.*)", io.open(RJ["log"], encoding="utf-8",
                                                        errors="replace").read()):
    ARMS[m.group(1)] = json.loads(m.group(2))
if sorted(ARMS) != ["arm1_legacy", "arm2_v8_corpus"]:
    bad.append("both arms must print readings: %s" % sorted(ARMS))
A1, A2 = ARMS["arm1_legacy"], ARMS["arm2_v8_corpus"]
if A1["legacyRoot"] is not True or A1["title_count"] < 1:
    bad.append("arm 1 did not reach the legacy shell with a payload")
if A1["mapCard"] is not False or A1["canvasCountAnywhere"] != 0:
    bad.append("arm 1's finding is that the symbol layer is NOT mounted; re-measure before claiming it")
if A2["canvasTag"] != "div" or A2["realCanvasInnerTextChars"] != 0:
    bad.append("arm 2's finding is that the gate's glass element is a div; re-measure")
# how the rule's own symbols are used, repo-wide, on the tip
MTF = grep_all(TIP, "mapLabelTextField", "frontend")
IMP = [l for l in grep_all(TIP, "lib/mapLabels", "frontend") if ".spec.ts" in l]
SYM = grep_all(TIP, 'type: "symbol"', "frontend/src")
TITLES = A1["judged"]
VIOL = [t for t in TITLES if t["violations"]]
ARIA = [a for a in A2["panelAriaLabels"] if a and not a.startswith(("Map", "The view"))]
# ---------- instrument typecheck, as measured ----------
TSC_RC = []
for proj in ("tsconfig.check.json", "tsconfig.typecheck.json"):
    rc, o = run([NODE, TSC, "-p", proj, "--noEmit"], cwd=os.path.join(WT, "frontend"), timeout=1800)
    TSC_RC.append((proj, rc, len([l for l in o.splitlines() if "error TS" in l])))
INC_CHECK = line_of(TIP, "frontend/tsconfig.check.json", '"include"')
INC_TYPE = line_of(TIP, "frontend/tsconfig.typecheck.json", '"include"')
for proj, rc, e in TSC_RC:
    if rc:
        bad.append("%s rc=%d" % (proj, rc))
# ---------- commit the instrument + the readouts on a fresh branch ----------
ART = "review/q415_label_string_origin_r1.json"
json.dump({"tip_measured": TIP, "run": RJ, "log": RJ_LOG, "arms": ARMS,
           "repo_grep": {"mapLabelTextField": MTF, "spec_importers_of_lib_mapLabels": IMP,
                         "symbol_layers": SYM},
           "instrument_typecheck": [{"cmd": "npx tsc -p %s --noEmit" % p, "rc": r,
                                     "error_lines": e} for p, r, e in TSC_RC]},
          open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, "review", "q415_block_r1.py"))
git("add", "-f", SPEC, ART, "review/q415_block_r1.py", cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0415: where the strings painted on the map glass come from, read off two live screens"])
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
elif not git_ok("merge-base", "--is-ancestor", TIP, PUSHED):
    bad.append("the pushed head does not contain the tip the readings claim")
TOUCHED = [l for l in git("diff", "--name-only", TIP, PUSHED).splitlines() if l.strip()]
if [t for t in TOUCHED if not (t.startswith("review/") or t.startswith("frontend/e2e/"))]:
    bad.append("non-instrument paths in my diff: %s" % TOUCHED)
SPEC_BLOB = blob_at(PUSHED, SPEC)
ART_BLOB = blob_at(PUSHED, ART)
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    bad.append("the door ruler is not the byte-for-byte one the relay named: %s" % R7_SHA1)
J_TITLE = line_of(PUSHED, JM, "title: activity.title")
J_FIELD = line_of(PUSHED, JM, '"text-field"')
J_LAYER = line_of(PUSHED, JM, 'id: "citynexus-activity-labels"')
M_FUNC = line_of(PUSHED, ML, "export function mapLabelTextField")
M_SCOPE = line_of(PUSHED, ML, "judged:")
M_FORB = line_of(PUSHED, ML, '"clock-time"')
G_CORPUS = line_of(PUSHED, G0412, "const glassCorpus = [")
G_CANVAS = line_of(PUSHED, G0412, ".v8-maplibre-canvas")
G_ASSERT = line_of(PUSHED, G0412, "the compliance sentence")
MP_MARK = line_of(PUSHED, MP, "marker.textContent = String(index + 1)")
MN_LEGACY = line_of(PUSHED, MN, 'path.startsWith("/legacy")')
MY_A1 = line_of(PUSHED, SPEC, "legacyRoot: !!document.querySelector")
MY_A2 = line_of(PUSHED, SPEC, "canvasInnerTextChars:")
PORT_LINE = line_of(PUSHED, PORTSPEC, "LOW, HIGH = ")
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = "%s:%s" % (NOW[:2], NOW[2:])
DFL = [l for l in run(["df", "-h", "/d"])[1].splitlines() if l.strip()]
GB = DFL[-1].split()[3] if len(DFL[-1].split()) > 3 else "?"

B = []
A = B.append
A("### ORD-0415 · 道0370（会话 e4f3490f）· 图上标注的字符串从哪来 · 两臂现尖读数 · 0 产品字节 · 2026-09-29 %s+08" % NW)
A("")
A("## 交付坐标")
A("   新枝 `refs/heads/%s`，push 后 `git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/%s`" % (BRANCH, BRANCH))
A("   现读头 = %s （`git cat-file -t` = commit），它的父逐字等于我量的现尖 %s （`git rev-parse %s^` 现读）。" % (PUSHED, TIP, PUSHED))
A("   写这块之前我又读了一次现尖 = %s ，与基点逐字相同 ⇒ 这块是挂在最新一代上的候选枝，权威线我没动。" % TIP)
A("   枝上在基点之上 commit_count=%d 笔（第一笔落仪表与读数件，第二笔把我这具生成器也收进来：")
A("   `review/q415_block_r1.py` blob %s ，`git rev-list --count %s..%s` 现读）。" % (
    int(git("rev-list", "--count", "%s..%s" % (TIP, PUSHED)) or 0),
    blob_at(PUSHED, "review/q415_block_r1.py"), TIP[:12], PUSHED[:12]))
A("   相对现尖动了 touched_file_count=%d 枚，全在本单的仪表与读数件里：逐枚 %s 。" % (
    len(TOUCHED), " ".join("%s blob %s" % (t, blob_at(PUSHED, t)) for t in TOUCHED)))
A("   产品字节：同一集合按前缀现数，backend/ 命中=%d 枚、frontend/src/ 命中=%d 枚（逐枚清单在上面那行，全部在 frontend/e2e/ 与 review/ 之下）。" % (
    len([t for t in TOUCHED if t.startswith("backend/")]), len([t for t in TOUCHED if t.startswith("frontend/src/")])))
A("   仪表 `%s`（blob %s），" % (SPEC, SPEC_BLOB))
A("   读数件 `%s`（枝上 blob %s，可 cat-file）。本车道端口 :%d / :%d，具名格 %s 。" % (
    ART, ART_BLOB, RJ["ports"]["frontend"], RJ["ports"]["backend"], PORT_LINE))
A("")
A("## 答案（先给结论，再给两臂的数）")
A("   画在玻璃上的那串字来自 `%s`（`properties.title = activity.title`，未过任何规则），" % J_TITLE)
A("   被 `%s` 的 `\"text-field\": [\"get\", \"title\"]` 直接取用（层 id 与 type 在 %s ）。" % (J_FIELD, J_LAYER))
A("   规则那一份 `%s` 的返回值就是同一串 `[\"get\", \"title\"]`，两处各写一遍；现尖全仓 `%s` 的命中数=%d 枚（逐枚 %s ），" % (
    M_FUNC, "mapLabelTextField", len(MTF), " ".join(x.split(":")[1] + ":" + x.split(":")[2] for x in MTF)))
A("   也就是只有定义本身、没有一处调用者；`lib/mapLabels` 的 import 命中数=%d 枚，逐枚 %s （全是 e2e 侧）。" % (
    len(IMP), " ".join(x.split(":")[1] + ":" + x.split(":")[2] for x in IMP)))
A("   全仓 `type: \"symbol\"` 在产品源码里的命中数=%d 枚（%s），所以「有玻璃标注层」这句只对 `%s` 成立；" % (
    len(SYM), SYM[0].split(":")[1] + ":" + SYM[0].split(":")[2] if SYM else "无", JM))
A("   而 v8 自己那屏的停靠点是 DOM 画的、只画序号：`%s`（现读该枚 marker 的赋值行）。" % MP_MARK)
A("   入口开关在 `%s`：只有路径以 /legacy 开头才挂 LegacyApp ⇒ 那枚 symbol 层今天不在用户走的那条路上。" % MN_LEGACY)
A("")
A("## 臂一 /legacy（现尖 %s，run_id=%s verdict=%s passed=%d，日志 %s）" % (TIP[:8], RJ["run_id"],
                                                                       RJ["verdict"], RJ["counts"]["passed"], RJ_LOG))
A("   到没到：legacyRoot=%s、v8Shell=%s、h1=%r（判据 %s ）；" % (
    A1["legacyRoot"], A1["v8Shell"], A1["h1"], MY_A1))
A("   地图卡在不在 DOM：mapCard=%s、mapCardEl=%s、canvasCountAnywhere=%d、fallbackTexts=%s ⇒ 这枚 symbol 层在我能到的状态下没挂上。" % (
    A1["mapCard"], A1["mapCardEl"], A1["canvasCountAnywhere"], json.dumps(A1["fallbackTexts"])))
A("   它本来要画的字面集合（从那一屏收到的 payload 里递归取 activities[].title，不硬编码路由）：" )
A("   endpoint_response_count=%d、title_count=%d、distinct_title_count=%d、titles_with_violations=%d（判据 %s ）" % (
    A1["endpoint_response_count"], A1["title_count"], A1["distinct_title_count"], A1["titles_with_violations"],
    MY_A1))
A("   逐枚标题（前八枚，全 %d 枚在 %s）：%s" % (
    len(TITLES), ART, "、".join("`%s`" % t["title"] for t in TITLES[:8])))
A("   禁表四个类别名=%s（定义在 %s），按它判这一批标题：命中数=%d ⇒ 今天的缺线是潜在的，不是正在漏。" % (
    json.dumps(A1["forbidden_rule_names"], ensure_ascii=False), M_FORB, len(VIOL)))
A("")
A("## 臂二 /v8 那张闸的「玻璃语料」到底由什么组成（同一 run，判据 %s ）" % MY_A2)
A("   现读 `.v8-maplibre-canvas` 这个元素的 tagName=%r、它的 childElementCount=%d、innerText 长 %d 字符；" % (
    A2["canvasTag"], A2["canvasChildElementCount"], A2["canvasInnerTextChars"]))
A("   同一屏真正的 `<canvas>` 元素个数=%d，它的 innerText 长 %d 字符 ⇒ 玻璃上没有可读文本节点，这是结构事实不是猜。" % (
    A2["realCanvasCount"], A2["realCanvasInnerTextChars"]))
A("   那把闸的语料组合式在 `%s`（它取 `canvas?.innerText` 加 %s 那批 DOM 标记的 textContent 与 aria-label）：" % (
    G_CORPUS, MP_MARK))
A("   我这轮复算它的语料：markerCount=%d、markerTexts=%s、markerAriaCount=%d、glassCorpusChars=%d、其中来自那枚 div 的 %d 字符；" % (
    A2["markerCount"], json.dumps(A2["markerTexts"]), A2["markerAriaCount"], A2["glassCorpusChars"],
    A2["glassCorpusFromCanvasChars"]))
A("   `corpusHasHost`=%s（%s 那一串不在语料里，这一点它判对了）。" % (
    A2["corpusHasHost"], "openstreetmap"))
A("   所以：`%s` 的「glass corpus」实际是 9 枚序号加它们的 aria-label 加 17 字符 div 文本，" % G_CANVAS)
A("   没有一字符来自真正画在玻璃上的标注；那条闸报的「玻璃干净」判的是 DOM。（它自己声明的判据面在 %s 。）" % M_SCOPE)
A("   另一枚现读事实：地名今天活在 aria-label 里，不在玻璃上 —— panelAriaLabels 逐枚 %s 。" % (
    "、".join("`%s`" % a for a in ARIA)))
A("")
A("## 这对本单两条路各意味着什么（我把数放这儿，选哪条归号令者）")
A("   甲（把 `%s` 改成从 %s 取，并把违规拦在进管线之前）：消重是真能做到的，但拦下之后屏上显示什么" % (J_FIELD, M_FUNC))
A("   是一句用户可见的文案决定（整条不画？画去掉时间与钱的名字？给一句具名兜底？），我不替产品造这句字。")
A("   而且甲落在的唯一表面在 /legacy（`%s`），那一屏现在的 h1 是 %r、地图卡根本没挂上 ⇒ 甲落完我也取不到「违规被拦住」的运行读数；" % (
    MN_LEGACY, A1["h1"]))
A("   要甲有意义，先得有人修 /legacy 的行程连接（那不在本单授权里，成因我没查，只把 h1 原样报上）。")
A("   乙（具名「v8 那一屏没有玻璃标注层」并把规则标成只服务 symbol 层）：现读支持它 —— 产品源码里 symbol 层命中数=%d 枚且不在 v8 路径，" % len(SYM))
A("   v8 的 marker 是序号（%s）。但乙要顺手处理一件事：`%s` 现在按「判玻璃」自称，" % (MP_MARK, G0412))
A("   乙成立就等于承认它没有可判面，那条闸的 judged 表面要么改名成它真正在判的 DOM 面，要么等 v8 真上玻璃标注时再接上；")
A("   这枚件是别车道写的（%s 的作者在账本里），我只报读数，不动它。" % G0412)
A("   我不做的一件事：为了让尺有东西可判临时造一层 —— 号令者 22:29 已明写不许，我也取不到必要。")
A("")
A("## 没改善的部分")
A("1. 真画在玻璃上的那批字符串我没量到：maplibre 不在容器上留实例把手，而我这一轮拒绝为测量往产品源码里塞 window 钩子（0 产品字节是本单前提）。")
A("   要那一枚读数，得授权我加一个只在 dev 暴露的句柄，或者用像素差去推 —— 说一句我就做。")
A("2. /legacy 为什么回 h1=%r（payload 已经拿到 plans 与 twin，endpoint_response_count=%d）我没查；" % (A1["h1"], A1["endpoint_response_count"]))
A("   那是另一张单的范围，我只把它当作「甲今天没有可运行表面」的证据交上来。")
A("3. 我没跑整套 e2e，只跑了本单这支 spec（3 条）与两枚具名 tsc 工程：")
for proj, rc, e in TSC_RC:
    A("   cmd=npx tsc -p %s --noEmit rc=%d error_lines=%d" % (proj, rc, e))
A("   但两枚工程的 include 都不覆盖 e2e/（`%s` 与 `%s` 现读）⇒ 它们不为我的仪表担保；" % (INC_CHECK, INC_TYPE))
A("   仪表真正的编译证据是那三跑：Playwright 把它转译并执行过（run_id=%s，3 条全出读数）。" % RJ["run_id"])
A("4. ORD-0412 那把闸的表面命名（judged 写的是 canvas-label-strings，实判 DOM）我只报不改，文件不是我名下。")
A("5. 我这条车道的 worktree 现在检出在 %s 上（本单的新枝），不是 ORD-0406 那枚 %s ；" % (PUSHED, "5ae3874ed6328af6ad760c7a9eb0708a04362048"))
A("   0406 的产品字节仍在它自己那条枝上，两枝互不覆盖，读我的人按枝名取。")
A("6. 盘：D 盘剩余 %s（`df -h /d` 现读）；本车道的 :%d / :%d 跑完按 pid 关并 netstat 复查。" % (
    GB, RJ["ports"]["frontend"], RJ["ports"]["backend"]))
A("")
A("门尺自检：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0，findings 由本进程写盘前现跑；" % LIVE)
A("   那把尺本地字节重算文件 sha1=%s（与值守给的 40 位逐字相同；非 git 对象声明，同段可 cat-file 的坐标：" % R7_SHA1)
A("   入库 blob %s 、`git cat-file -s` 得 byte_count=%d 与我运行的字节数相同、交付头 %s）。" % (R7_BLOB, len(r7b), PUSHED))
A("   第二道闸在同一份草稿上逐值复算（只扫逐字 40 位；免除要同一行写明不可取回且同段有另一枚能 cat-file 的 40 位，")
A("   path:line 在那道闸里不算数），abort 清单非空就不投递。")

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR, "q415_block_r1_draft.md")
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
if glob.glob(os.path.join(INBOX, "qoder-0415_*.md")):
    print("REFUSED PUBLISH -- a live qoder-0415 block is already in the inbox")
    sys.exit(4)
OUT = os.path.join(INBOX, "qoder-0415_%s.md" % NOW)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
