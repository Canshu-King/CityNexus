#!/usr/bin/env python3
"""ORD-0406 (.v8-message recipe) delivery.

Adds the one proof a dev server cannot give -- served bytes equal to the bytes on disk -- by building
the branch's own export and serving it through `vite preview` on a port in this lane's band, then
comparing sha1 over the received bytes with sha1 over the files on disk. Everything else is read back
out of the branch and the receipt the spec wrote.
"""
import glob
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

WT = r"D:/moodle/_qoder_lane_q0406"
REPO = r"D:/moodle/CityNexus"
LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
SCR = r"D:/moodle/_qoder_lane_q0370_scratch"
SNAP = r"D:/moodle/_qoder_lane_0406r_snap"
NM_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/node_modules"
NODE = r"C:/Program Files/nodejs/node.exe"
VITE = os.path.join(NM_SRC, "vite", "bin", "vite.js")
VENV = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BRANCH = "review/Q-ord0406-v8-message-recipe-r1"
R7_BLOB = "cf1f047d53d4848fa16abcd03df34099ec87d90d"
R7_SHA1_WANTED = "2690a3f7eb0b817a882212854ad906bfc8703e2d"
SPEC = "frontend/e2e/qoder-ord0406-v8-message-recipe-r1.spec.ts"
V8 = "frontend/src/app/V8Experience.tsx"
RUNNER = "review/e4f_e2e_r1.py"
SITES = {
    "shell-address-verdict": (V8, 'data-testid="address-no-screen"'),
    "shell-shared-banner": (V8, '<div className="v8-message" role="status">'),
    "agent-send-error": ("frontend/src/features/agent/AgentComposer.tsx", 'data-testid="agent-send-error"'),
    "discovery-error": ("frontend/src/features/discovery/RealCityDiscoveryPanel.tsx", 'data-testid="v13-discovery-error"'),
    "discovery-batch-error": ("frontend/src/features/discovery/RealCityDiscoveryPanel.tsx", 'data-testid="v13-discovery-batch-error"'),
    "rank-failed": ("frontend/src/features/planning/PlanRankingPanel.tsx", 'data-testid="rank-failed"'),
    "history-failed": ("frontend/src/features/studio/PlanVersionHistoryPanel.tsx", 'data-testid="history-failed"'),
}
bad = []


def run(cmd, cwd=None, timeout=None, env=None):
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e.update(env or {})
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
    out = git("grep", "-n", "-F", "-e", pattern, ref, "--", rel, check=False)
    m = re.search(r":(\d+):", out)
    if not m:
        bad.append("no grep hit for %r in %s" % (pattern, rel))
        return "%s:?" % rel
    return "%s:%s" % (rel, m.group(1))


def guard_of(ref, rel, n):
    """The line that decides whether that element mounts: the nearest preceding `&&` / `?` guard."""
    body = git("show", "%s:%s" % (ref, rel), cwd=REPO).split("\n")
    for i in range(n - 1, max(0, n - 14), -1):
        if "&& (" in body[i] or "? " in body[i] and "):" in body[i]:
            return i + 1, body[i].strip()[:120]
    return None, ""


def free_port(lo, hi):
    for p in range(lo, hi):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return None


TIP = head_of("refs/heads/mirror/integration-frontend-apple-pass1")
if not git_ok("cat-file", "-e", TIP):
    bad.append("the live tip is not retrievable: %r" % TIP)
HEAD = git("rev-parse", "HEAD", cwd=WT)
BASE = git("merge-base", TIP, HEAD)
if BASE != HEAD:
    bad.append("the live tip does not contain my head (I am not an ancestor of it): base %s head %s" % (BASE, HEAD))
N_LAG = int(git("rev-list", "--count", "%s..%s" % (HEAD, TIP)) or 0)
# the line moves every few minutes; what has to hold is that the bytes my readings are about match
DEPENDS = [V8, "frontend/src/i18n/LocaleContext.tsx", "frontend/index.html",
           "frontend/src/features/intelligence/ControlTowerPanel.tsx",
           "frontend/src/app/v8PanelRegistry.tsx", "frontend/e2e/_qoderShellSeed.ts"]
DRIFT = [f for f in DEPENDS if blob_at(HEAD, f) and blob_at(TIP, f) and blob_at(HEAD, f) != blob_at(TIP, f)]
if DRIFT:
    bad.append("bytes my readings depend on moved past my head: %s" % DRIFT)
MT_RC, MT_OUT = run(["git", "-C", REPO, "merge-tree", "--write-tree", TIP, HEAD])
R = receipt = None
RS = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "q406r5_*.json")), key=os.path.getmtime)
if not RS:
    bad.append("no recipe receipt")
else:
    receipt = json.load(open(RS[-1], encoding="utf-8"))
if receipt and (receipt.get("verdict") != "GREEN" or str(receipt.get("tree")) != HEAD):
    bad.append("the recipe run is not GREEN on this head: %s %s" % (
        receipt.get("verdict") if receipt else "?", receipt.get("tree") if receipt else "?"))
ARMS = {}
if receipt:
    for m in re.finditer(r"O406R ([A-Za-z0-9_-]+) (\{.*)", io.open(receipt["log"], encoding="utf-8",
                                                                   errors="replace").read()):
        ARMS[m.group(1)] = json.loads(m.group(2))
if sorted(ARMS) != ["armA_en", "armA_zh-CN", "armB_en", "armB_zh-CN", "armS"]:
    bad.append("the recipe did not print all five readings: %s" % sorted(ARMS))
for k in ("armA_zh-CN", "armA_en", "armB_zh-CN", "armB_en"):
    s = ARMS.get(k, {}).get("verdict") or ARMS.get(k, {}).get("banner")
    if not s or len(s.get("text", "")) < 8:
        bad.append("%s has no painted sentence" % k)
if not ARMS.get("armS", {}).get("entry_named_by_served_html"):
    bad.append("arm S did not confirm this checkout's own entry")
if ARMS.get("armS", {}).get("served_equals_disk") is not False:
    bad.append("arm S claims byte equality under dev; it must not")
DEAD = ARMS.get("armB_zh-CN", {}).get("dead_link", {})

EARLY = []
FAILGEOM = {}
for tag in ("q406r1", "q406r2", "q406r4"):
    fs = sorted(glob.glob(os.path.join(LIVE, "e2e_logs", "%s_*.json" % tag)))
    if not fs:
        bad.append("no %s receipt to disclose" % tag)
    else:
        r0 = json.load(open(fs[0], encoding="utf-8"))
        EARLY.append((tag, r0["run_id"], r0["log"]))
        if tag == "q406r4":
            for m in re.finditer(r"O406R (armB_[\w-]+) (\{.*)", io.open(r0["log"], encoding="utf-8",
                                                                        errors="replace").read()):
                FAILGEOM[m.group(1)] = json.loads(m.group(2))

if DEAD.get("message_count") != 0 or not DEAD.get("responses"):
    bad.append("the dead-link reading is missing or changed shape")

# ---------- static port: the proof dev cannot give ----------
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
rc, bo = run([NODE, VITE, "build", "--outDir", "dist", "--emptyOutDir"],
             cwd=os.path.join(SNAP, "frontend"), timeout=2400)
if rc:
    bad.append("vite build rc=%d %s" % (rc, bo[-200:]))
fe = os.path.join(SNAP, "frontend")
# the served HTML is the *built* one; comparing it to the source index.html would be a category error
entry_disk = os.path.join(fe, "dist", "index.html")
assets = sorted(os.path.basename(a) for a in glob.glob(os.path.join(fe, "dist", "assets", "index-*.js")))
PORT = free_port(5610, 5640)
STATIC = {"port": PORT, "build_rc": rc, "assets": assets, "nlink": NLINK}
server = None
if PORT and len(assets) == 1:
    server = subprocess.Popen([NODE, VITE, "preview", "--outDir", "dist", "--port", str(PORT),
                               "--strictPort", "--host", "127.0.0.1"],
                              cwd=fe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(9)
    def get(path):
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (PORT, path), timeout=20) as r:
            return r.status, r.read()
    try:
        st, html = get("/")
        st2, js = get("/assets/" + assets[0])
        disk_html = open(entry_disk, "rb").read()
        disk_js = open(os.path.join(fe, "dist", "assets", assets[0]), "rb").read()
        STATIC = dict(STATIC, served_status=st, asset_status=st2,
                      html_sha1_served=hashlib.sha1(html).hexdigest(),
                      html_sha1_disk=hashlib.sha1(disk_html).hexdigest(),
                      html_bytes_served=len(html), html_bytes_disk=len(disk_html),
                      asset_sha1_served=hashlib.sha1(js).hexdigest(),
                      asset_sha1_disk=hashlib.sha1(disk_js).hexdigest(),
                      asset_bytes=len(js),
                      entry_named_by_served_html=b"/assets/" in html,
                      served_equals_disk=(hashlib.sha1(html).hexdigest() == hashlib.sha1(disk_html).hexdigest()
                                          and hashlib.sha1(js).hexdigest() == hashlib.sha1(disk_js).hexdigest()))
    except Exception as exc:
        bad.append("the static port did not answer: %s" % exc)
if server:
    server.terminate()
    time.sleep(2)
    try:
        server.kill()
    except OSError:
        pass
if not STATIC.get("served_equals_disk"):
    bad.append("the static serving proof is not byte-for-byte: %s" % json.dumps(STATIC))
HELD = run(["netstat", "-ano"])[1]
PORT_FREE = ("\n127.0.0.1:%d " % PORT) not in HELD and ("127.0.0.1:%d:" % PORT) not in HELD

SITE_ROWS = {}
for key, (rel, pat) in SITES.items():
    ln = line_of(HEAD, rel, pat)
    n = int(ln.rsplit(":", 1)[1]) if ln.rsplit(":", 1)[1].isdigit() else 0
    gl, gtext = guard_of(HEAD, rel, n) if n else (None, "")
    SITE_ROWS[key] = {"site": ln, "guard_line": ("%s:%s" % (rel, gl)) if gl else None,
                      "guard_text": gtext, "blob": blob_at(HEAD, rel)}

# ---------- readouts artifact, commit, push ----------
ART = "review/q406_v8_message_recipe_r1.json"
if bad:
    print("REFUSING BEFORE THE COMMIT -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
json.dump({"tip": TIP, "branch_head_at_readings": HEAD, "receipt": receipt, "log": receipt["log"],
           "arms": ARMS, "static_port": STATIC, "sites": SITE_ROWS,
           "earlier_iterations": {"run_ids": [e[1] for e in EARLY], "biting_run_geometry": FAILGEOM},
           "sentinel_dead_link_id": "0f0f0f0f-0f0f-4f0f-8f0f-0f0f0f0f0f0f"},
          open(os.path.join(WT, ART), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
shutil.copyfile(os.path.abspath(__file__), os.path.join(WT, "review", "q406_message_recipe_r1.py"))
git("add", "-f", SPEC, ART, "review/q406_message_recipe_r1.py", cwd=WT)
rc, co = run(["git", "-C", WT, "commit", "-q", "-m",
              "ORD-0406 recipe: how each .v8-message site is made to render, with the painted "
              "sentences and the static-port byte proof"])
if rc and "nothing to commit" not in co:
    print("COMMIT FAILED -- %s" % co[-200:])
    sys.exit(1)
PUSHED = head_of("refs/heads/" + BRANCH)
if not PUSHED:
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
elif [l for l in git("diff", "--name-only", HEAD, PUSHED).splitlines()
      if l.strip() and not l.startswith("review/")]:
    bad.append("the readouts commit touched non-review paths")
SPEC_BLOB = blob_at(PUSHED, SPEC)
ART_BLOB = blob_at(PUSHED, ART)
r7b = open(os.path.join(LIVE, "claim_coordinate_check_r7.py"), "rb").read()
R7_SHA1 = hashlib.sha1(r7b).hexdigest()
if R7_SHA1 != R7_SHA1_WANTED or int(git("cat-file", "-s", R7_BLOB)) != len(r7b):
    bad.append("the door ruler is not the byte-for-byte one the relay named")
ADDR_LINE = line_of(PUSHED, V8, 'data-testid="address-no-screen"')
ADDR_COND = line_of(PUSHED, V8, 'deepLink.kind === "unknown" && route === "hub"')
BANNER_LINE = line_of(PUSHED, V8, '<div className="v8-message" role="status">')
DISMISS_LINE = line_of(PUSHED, V8, "shell.dismiss")
AUTONOMY_SET = line_of(PUSHED, V8, "setMessage(t(\"shell.autonomyEnabled\"))")
AUTONOMY_PUT = line_of(PUSHED, V8, "/agent-policy")
CTA_BUTTON = line_of(PUSHED, "frontend/src/features/intelligence/ControlTowerPanel.tsx",
                     "onClick={() => void onActivate()}")
CTA_PANEL = line_of(PUSHED, "frontend/src/app/v8PanelRegistry.tsx", 'id: "intelligence"')
DEEP_LINK = line_of(PUSHED, V8, "function deepLinkFromPath")
DICT_ZH = line_of(PUSHED, "frontend/src/i18n/LocaleContext.tsx", '"shell.addressNoScreen": "这个地址')
DICT_EN = line_of(PUSHED, "frontend/src/i18n/LocaleContext.tsx", '"shell.addressNoScreen": "This address')
DICT_AUTO_ZH = line_of(PUSHED, "frontend/src/i18n/LocaleContext.tsx", '"shell.autonomyEnabled": "自主恢复')
DICT_AUTO_EN = line_of(PUSHED, "frontend/src/i18n/LocaleContext.tsx", '"shell.autonomyEnabled": "Autonomous')
ENTRY_LINE = ARMS["armS"]["entry_line_in_index_html"]
PORT_LINE = line_of(PUSHED, RUNNER, "LOW, HIGH = ")
NOW = run([VENV, "-c", "import datetime;print(datetime.datetime.now().strftime('%H%M'))"])[1].strip()
NW = "%s:%s" % (NOW[:2], NOW[2:])
GB = [l for l in run(["df", "-h", "/d"])[1].splitlines() if l.strip()][-1].split()[3]
A_EN, A_ZH = ARMS["armA_en"], ARMS["armA_zh-CN"]
B_EN, B_ZH = ARMS["armB_en"], ARMS["armB_zh-CN"]

B = []
A = B.append
A("### ORD-0406 补件二 · 道0370（e4f3490f）· 让 `.v8-message` 真渲染的配方 · 两臂屏读 + 静态口字节等证 · 2026-09-29 %s+08" % NW)
A("")
A("## 交付坐标")
A("   新枝 `refs/heads/%s`（不覆盖任何已推 ref）；`git -c http.proxy= -c https.proxy= -C D:/moodle/CityNexus ls-remote origin refs/heads/%s` 现读头 = %s" % (BRANCH, BRANCH, PUSHED))
A("   （`git cat-file -t` = commit）。这一轮权威线走得太快，我不追：我这枝是现尖的祖先（`git merge-base %s %s` 现读 = 我的头 %s ），尖在我之上多 %d 笔；" % (TIP, HEAD, HEAD, N_LAG))
A("   而我这些读数所依赖的 %d 枚字节（外壳、词典、入口 html、面板注册表、控制塔面板、e2e 播种件）在我的头与现尖上 blob 逐枚相同（脚本按 `git rev-parse <rev>:<path>` 断言，漂移=%d 枚）⇒ 报的是我量过的那一代，且那一代与现尖在这些文件上没有分叉；合流预测 `git merge-tree --write-tree %s %s` 退出码=%d 。" % (
    len(DEPENDS), len(DRIFT), TIP, PUSHED, MT_RC))
A("   相对基点 touched_file_count=%d 枚：仪表 `%s`（blob %s ）、读数件 `%s`（blob %s ）、生成器 `review/q406_message_recipe_r1.py`（blob %s ）；" % (
    len([l for l in git("diff", "--name-only", TIP, PUSHED).splitlines() if l.strip()]),
    SPEC, SPEC_BLOB, ART, ART_BLOB, blob_at(PUSHED, "review/q406_message_recipe_r1.py")))
A("   产品字节 0 处（同一集合里 frontend/src/ 前缀命中=%d 枚，`git diff --name-only %s %s` 现读；样式与热文件一枚没碰）。" % (
    len([l for l in git("diff", "--name-only", TIP, PUSHED).splitlines() if l.startswith("frontend/src/")]), TIP, PUSHED))
A("")
A("## 配方一 · shell 的两处 `.v8-message`：一条 URL 就够的那处，和必须有一个动作的那处")
A("   **site 1（派生，不需要数据）** `%s` —— 条件是 %s ：地址第一段既不是任何屏的键、也不是行程 UUID，且这一屏落在 Today。" % (ADDR_LINE, ADDR_COND))
A("   驱动：`page.goto(\"/v8/nosuchscreen\")`（等 `today-heading` 可见再读，别等网络空闲——行程读还在飞）。判定式出处 %s 。" % DEEP_LINK)
A("   渲染出来的句子（%s 中文臂 / %s 英文臂，run_id=%s verdict=%s）：" % (DICT_ZH, DICT_EN, receipt["run_id"], receipt["verdict"]))
A("      zh：%r" % A_ZH["verdict"]["text"])
A("      en：%r" % A_EN["verdict"]["text"])
A("      两臂同位：box y=%d..%d、最后一条绘制行底边 %d 对 hit_line=%d、中心 %s 命中自己=%s 、role=%s 、visible=%s ；" % (
    A_ZH["verdict"]["box"]["y"], A_ZH["verdict"]["box"]["bottom"], A_ZH["verdict"]["lastLineBottom"],
    A_ZH["hitLine"], json.dumps(A_ZH["verdict"]["centre"]), A_ZH["verdict"]["centreHitSelf"],
    A_ZH["verdict"]["role"], A_ZH["verdict"]["visible"]))
A("      两臂各一句、非属性：中文臂句里含汉字与段名 nosuchscreen，英文臂同（断言在仪表里，%s ）；证据 %s/armA_zh-CN.json 与 armA_en.json 。" % (
        line_of(PUSHED, SPEC, "the sentence has to be painted text, not an attribute"),
        "frontend/review/evidence/qoder-ord0406-recipe"))
A("   **site 2（状态，需要一个动作）** `%s` —— 只有 `setMessage` 写过才挂；空列表/条件语句会把它整个省掉。" % BANNER_LINE)
A("   我选的驱动是最省数据的一条：`/v8/intelligence`（注册表 %s ，面板 %s ）上点「启用可逆恢复」→ PUT %s → 成功后 %s ；" % (CTA_PANEL, CTA_BUTTON, AUTONOMY_PUT, AUTONOMY_SET))
A("   数据条件具名到接口与载荷字段：GET/PUT `/api/v1/travelers/{traveler_id}/agent-policy` 两趟都 200，PUT 回来的体里 `mode=AUTONOMOUS`、`auto_accept_replan=true`、`max_auto_replan_cost_delta_minor=5000`、`allowed_activity_types=[\"transport\",\"visit\"]`（逐枚见 %s 里 policy_calls 那格）；" % ART)
A("   这一格**不新建进度/勾选状态**：句子由那一次写成功触发，`shell.dismiss`（%s）关掉就不再挂，服务端策略改回去句子也不会自己出现。" % DISMISS_LINE)
A("      zh：%r" % B_ZH["banner"]["text"])
A("      en：%r" % B_EN["banner"]["text"])
A("      同位读数：box y=%d..%d、最后绘制行底边 %d 对 hit_line=%d、中心 %s 命中自己=%s 、role=%s ；两臂各一份证据 armB_zh-CN.json / armB_en.json 。" % (
    B_ZH["banner"]["box"]["y"], B_ZH["banner"]["box"]["bottom"], B_ZH["banner"]["lastLineBottom"],
    B_ZH["hitLine"], json.dumps(B_ZH["banner"]["centre"]), B_ZH["banner"]["centreHitSelf"], B_ZH["banner"]["role"]))
A("      这一格必须**先滚进可达带再判命中**：点完那一刻，en 那臂的句子在视口外（box.y=%d 、它在文档里的位置 documentY=%d 、scrollY=%d 、页高=%d px），" % (
    (B_EN.get("before_scroll", {}).get("sentences") or [{}])[0].get("box", {}).get("y", 0),
    (B_EN.get("before_scroll", {}).get("sentences") or [{}])[0].get("documentY", 0),
    B_EN.get("before_scroll", {}).get("scrollY", 0), B_EN.get("before_scroll", {}).get("docHeight", 0)))
A("      zh 那臂同刻 box.y=%d 、scrollY=%d （这一臂刚好没被点击带着滚）；两臂都在 `scrollIntoViewIfNeeded` 之后才取上面那组命中数（仪表里的这一步 %s ）。" % (
    (B_ZH.get("before_scroll", {}).get("sentences") or [{}])[0].get("box", {}).get("y", 0),
    B_ZH.get("before_scroll", {}).get("scrollY", 0),
    line_of(PUSHED, SPEC, "scroll the sentence into the reachable band")))
A("      注意 zh 那行 `hasControlTowerCard=%s`：`v17-runtime-status` 那张卡在 e2e（AI 关）下没挂，按钮照样在 —— 等那张卡当锚会把这一格判成不可达，配方里别用它当锚。" % B_ZH["screen"]["hasControlTowerCard"])
A("")
A("## 配方二 · 反向那一格：一次答不上的读，两处 `.v8-message` 都不渲染（这是缺口不是我的绿）")
A("   我拿一个库里没有的行程 UUID 直接当地址进 `%s`：后端答 404，体里 `code=NOT_FOUND`、`message_key=resource.not_found`、带 `trace_id` 与 `error_receipt_id`（逐枚在 %s 的 dead_link.responses 里）；" % (
    "/v8/0f0f0f0f-0f0f-4f0f-8f0f-0f0f0f0f0f0f", ART))
A("   屏上读数：`.v8-message` 个数=%d 、`.v8-product-shell` 挂了吗=%s 、body 可视字数=%d —— 也就是这条路径根本没走到能挂横幅的那层。" % (
    DEAD["message_count"], DEAD["shell_mounted"], DEAD["body_chars"]))
A("   所以「读失败要说话」这句话现在不在这枚元素里；要它出现在 `.v8-message`，得改的是 shell 的 boot 读路径（在 %s 里），那是热文件、我不在这单里偷改，具名交给号令者。" % V8)
A("")
A("## 服务证明：dev 给不了字节等证，静态口给")
A("   dev（`npm run dev`，端口带具名格 %s ）：服务到的 HTML 里确实带着本检出自己的入口行 `%s`（磁盘 `frontend/index.html:%d` 那行原文 %r）；" % (
    PORT_LINE, "/src/main.tsx", ENTRY_LINE, ARMS["armS"]["disk_entry_line_text"]))
A("   但 dev 下 served != disk 是**正常的**：vite 注入了 `/@vite/client` 与 `/@react-refresh` 两块，实测 served_bytes=%d 对 disk_bytes=%d ，两枚 sha1 分别 %s 与 %s（我只断言入口名同源 + 差量就是注入块，不断言相等）；" % (
    ARMS["armS"]["served_bytes"], ARMS["armS"]["disk_bytes"], ARMS["armS"]["served_sha1_over_bytes"], ARMS["armS"]["disk_sha1_over_bytes"]))
A("   静态口（这条才是字节等证）：`git archive %s | tar -x` 导出后 `npx vite build --outDir dist`（rc=%d ，node_modules 用 os.link 借、nlink=%d ），再 `vite preview --outDir dist --port %d --strictPort`；" % (
    HEAD, STATIC["build_rc"], STATIC["nlink"], STATIC["port"]))
A("   实测构建产物 `frontend/dist/index.html`：served_sha1=%s == disk_sha1=%s（bytes %d/%d）；入口资产 /assets/%s：served_sha1=%s == disk_sha1=%s（bytes=%d ，状态码 %s/%s ）⇒ 两枚都逐字节相同（sha1 over bytes，本地重算；非 git 对象声明，同段可 cat-file 的坐标：交付头 %s ）。" % (
    STATIC["html_sha1_served"], STATIC["html_sha1_disk"], STATIC["html_bytes_served"], STATIC["html_bytes_disk"],
    "".join(STATIC["assets"]), STATIC["asset_sha1_served"], STATIC["asset_sha1_disk"], STATIC["asset_bytes"],
    STATIC["served_status"], STATIC["asset_status"], PUSHED))
A("   preview 进程 terminate+kill 之后 `netstat -ano` 现读该端口已无条目（=%s ）。" % ("已无监听" if PORT_FREE else "仍在，未通过"))
A("")
A("## 其余带 `.v8-message` 的格（配方齐到这里，跑没跑逐枚标清）")
for key in sorted(SITE_ROWS):
    row = SITE_ROWS[key]
    A("   %s 元素在 %s blob %s ；决定它挂不挂的那一行 %s ：%s" % (
        key, row["site"], row["blob"], row["guard_line"] or "未定位", row["guard_text"] or "（同条 if 之外没找到守卫行）"))
A("   我这轮只跑了 shell 那两处（配方一）。其余 %d 处我按守卫原样报名，不当已验；它们的共同点是「需要一次失败/一个动作」，" % (len(SITE_ROWS) - 2))
A("   其中 discovery/rank/history 三处要真失败才亮，本车道私有栈离线可造的失败只有上面那枚 404（而 404 走的是 boot 读，见配方二）。")
A("")
A("## 没改善的部分")
A("1. site 2 的驱动选了 `activateAutonomy`，它写了策略（PUT 到我私有库 `_cmdr%s.db` 那一代）；我没有找「零写入也能亮横幅」的路径——那要产品先有一条只读失败上屏的通路（见配方二）。" % str(receipt["run_id"]).replace("cmdr", ""))
A("2. 这些读数都在车道私有栈的 dev 上，手机那一代仍未推；静态口那一段只证「我发出去的就是这些字节」，不证手机上那台。")
A("3. 仪表里 `armS` 断言的是入口同源 + 差量即注入块，**没有**断言 dev 下字节相等；等相等只在静态口量到，两处分开报。")
A("4. 我没跑整套 e2e，也没跑号令者手上那把配对尺（不越界），只跑了本单这一支 spec（%d 条）。" % receipt["counts"].get("passed", -1))
A("5. 本回合我返工三次，收据都留着（同目录同名 .log 可逐枚查）：`%s` 与 `%s` 两轮 arm B 猜「答不上的读会走共享横幅」，实测那一屏 `.v8-message` 个数=%d ，路径不对（那才是配方二）；`%s` 到了现尖之后横幅**渲染了但中心命中为假**——那一轮 zh 臂 box.y=%d（为负，句子在滚动位置之上），判语 `and be hit-testable where it paints`。" % (
    EARLY[0][1], EARLY[1][1], DEAD["message_count"], EARLY[2][1],
    (FAILGEOM.get("armB_zh-CN", {}).get("banner") or {}).get("box", {}).get("y", 0)))
A("   第四轮才是对的写法：判命中之前先把句子滚进可达带，`%s` 两臂全绿（这一条正好是「空分母假绿」的反面：不滚会把已渲染的读成不可达，滚了不判命中会把遮住的读成可达）。" % receipt["run_id"])
A("6. 盘：D 盘剩余 %s（`df -h /d` 现读）；本车道起过的端口跑完按 pid 关并 `netstat` 复查。" % GB)
A("")
A("门尺自检：`%s/claim_coordinate_check_r7.py --text <本块> --expect-clean` 要 rc=0，退出码与 findings 由本进程写盘前现跑；" % LIVE)
A("   那把尺本地字节重算文件 sha1=%s（与值守给的 40 位逐字相同；非 git 对象声明，同段可 cat-file 的坐标：入库 blob %s 、byte_count=%d 与我运行的字节数相同、交付头 %s ）。" % (R7_SHA1, R7_BLOB, len(r7b), PUSHED))
A("   第二道闸在同一份草稿上逐值复算：只扫逐字 40 位，免除要同一行写明不可取回且同段有另一枚能 cat-file 的 40 位，path:line 不算数；abort 非空不投递。")

if bad:
    print("REFUSING -- %d:" % len(bad))
    for x in bad:
        print("   ", x)
    sys.exit(1)
DRAFT = os.path.join(SCR, "q406_message_recipe_r1_draft.md")
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
    print("    L%-3d %s" % (n, h[:14]))
if AB:
    print("NOT PUBLISHED -- second arm would abort")
    sys.exit(3)
if glob.glob(os.path.join(INBOX, "qoder-0406c_*.md")):
    print("REFUSED PUBLISH -- a live qoder-0406c block is already in the inbox")
    sys.exit(4)
OUTP = os.path.join(INBOX, "qoder-0406c_%s.md" % NOW)
io.open(OUTP, "w", encoding="utf-8", newline="\n").write(io.open(DRAFT, encoding="utf-8", newline="").read())
print("WROTE", OUTP, os.path.getsize(OUTP), "bytes")
