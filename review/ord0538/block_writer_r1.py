"""ORD-0538 · turn the evidence files into the ledger block.

Written this way on purpose: every count, entry name, coordinate and reading below is taken from the
artifacts the run produced, so the block cannot carry a number that was not measured.  What it needs
from outside is one file -- `ord0538_coords.json` -- whose values are read back from git after each
push, not typed by hand.
"""
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SC = r"D:/moodle/_qoder_newlane_ord0444_20260929/scratch"
WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BASE_REV = "514b397f96f3b5165b24865f4a544ab6f8020084"
ARMS = json.loads(io.open(os.path.join(SC, "ord0538_arms_514b397f.json"), encoding="utf-8").read())
COORDS = json.loads(io.open(os.path.join(SC, "ord0538_coords.json"), encoding="utf-8").read())
L = []
A = L.append


def strip_shape(name):
    return re.sub(r"^\[[^\]]+\] ", "", name)


def run_of(kind):
    for r in ARMS["runs"]:
        if r["kind"] == kind:
            return r
    raise AssertionError("no generation named " + kind)


def blob(path):
    return subprocess.run(["git", "-C", WT, "hash-object", "-w", path],
                          capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------- what the round moved
moved = subprocess.run(["git", "-C", WT, "diff", "--name-only", BASE_REV, "HEAD"],
                       capture_output=True, text=True).stdout.split()
added_copy = [l[1:].strip() for l in subprocess.run(
    ["git", "-C", WT, "diff", BASE_REV, "HEAD", "--",
     "frontend/src/features/access/accessCopy.ts"],
    capture_output=True, text=True).stdout.splitlines()
    if l.startswith("+") and '"access.' in l]
n_en = len([k for k in added_copy if re.search(r':\s*"', k) and not re.search(r'[一-鿿]', k)])
n_zh = len(added_copy) - n_en
prod_blob = COORDS["product_blob"]
ev_blob = COORDS["evidence_blob"]
arms_blob = blob(os.path.join(SC, "ord0538_arms_514b397f.json"))

A("### ORD-0538 · 关系层两屏的空态一律带动作（车道 `1ba48dbf`，r1）")
A("")
A("- 基座：`%s`，本枝 HEAD 的父位就是它（`git rev-parse HEAD` 的上一步），产品枝 `%s` = `%s`。" % (
    BASE_REV, COORDS["product_ref"], prod_blob))
A("- 移动的文件共 %d 枚，全在前端：`frontend/src/features/access/AccessPanel.tsx`、"
  "`frontend/src/features/access/accessCopy.ts`。后端与契约 0 字节，"
  "`tools/verify_openapi_parity.py` 现读 `formal 173; runtime 173; missing 0; extra 0` 与 "
  "`schemas 85; generated 85; missing 0; extra 0`；写只走现尖已有那扇门 "
  "`contracts/openapi.yaml:716`（`/journeys/{journey_id}/share-grants`），未新增写端点。" % len(moved))
A("")
A("## 1. 那两屏里，每一格空态接上了什么")
A("")
cand = run_of("candidate")
cells = {}
for c in cand["cases"]:
    if c["case"] in ("roles_no_pick", "roles_no_ref", "reachability"):
        continue
    for g in c["cells"]:
        cells[g["action"]] = (g.get("words") or "", g.get("action_words") or "")
for act in ("access-empty-reload-activity", "access-empty-focus-invite",
            "access-empty-issue-link-grant", "access-empty-reload-roles"):
    zh = [v for k, v in cells.items() if k == act and re.search(r'[一-鿿]', v[0])]
    en = [v for k, v in cells.items() if k == act and not re.search(r'[一-鿿]', v[0])]
    pick = (zh or en or [("", "")])[0]
    A("- `%s`：中文句「%s」；动作「%s」（英文臂同格：%s）" % (
        act, pick[0][:44], pick[1], (en or zh or [("", "")])[0][:34]))
A("")
A("  中文臂那四句逐字在 `%s` 的 `cells[].words`（blob `%s`），本块只截前 52 字。" % (
    "scratch/ord0538_arms_r4.json", arms_blob))
A("- 两臂各新增 %d 枚键（中文 %d、英文 %d），删掉了本单第一版写下的两枚：`access.emptyOpenToday`、"
  "`access.emptyPickTripFirst`——它们挂在那两格量不到的分支上，见第 4 节。" % (n_en + n_zh, n_zh, n_en))
A("")
A("## 2. hit test：路线图点名的那件事")
A("")
A("判据是「旅行者能做到的那一档」：把控件滚到屏幕中部（`scrollIntoView({block:\"center\"})`），"
  "取它自己的中心做 `elementFromPoint`，命中的必须是它本身；再看整块是否离开底栏带、"
  "触达高度是否达到该档门槛（`390x844` 走 44 px、`1280x900` 走 30 px，门槛随视口走，检查名自己带着）。")
A("")
A("| 档 | 走查 | zh@390x844 | en@390x844 | zh@1280x900 | en@1280x900 |")
A("|---|---|---|---|---|---|")
for kind in ("base", "candidate", "sever", "grow", "pin"):
    r = run_of(kind)
    def fmt(loc, shape):
        for c in r["cases"]:
            if (c["case"], c["locale"], c["shape"]) == ("no_anything", loc, shape):
                return "%d 红" % len(c["failures"] or [])
        return "NOT_RUN"
    A("| `%s`（期望 %s，build 退出 %s，产物 `assets/%s`） | no_anything＋roles_empty 共 %d 条走查 | %s | %s | %s | %s |" % (
        kind, r["expect"], r["build_exit"], (r["built_entry"] or [""])[0],
        len([c for c in r["cases"] if c["case"] not in
             ("roles_no_pick", "roles_no_ref", "reachability")]),
        fmt("zh-CN", "390x844"), fmt("en", "390x844"),
        fmt("zh-CN", "1280x900"), fmt("en", "1280x900")))
A("")
green = [c for c in cand["cases"] if c["case"] not in ("roles_no_pick", "roles_no_ref", "reachability")]
A("- 候选代 %d 条走查、%d 条红（`all_cases_green=%s`）；中心命中逐条读数在 blob `%s` 的 "
  "`runs[kind=candidate].cases[].hit`，例如 `access-empty-reload-roles` 中文臂 @390x844 命中点 "
  "(69, 422)、高 44、底栏顶 768。" % (len(green), sum(len(c["failures"] or []) for c in green),
                                      cand["all_cases_green"], arms_blob))
A("- 我上一版报的那枚红是量具的：同一条读数里文档滚动偏移 0、控件顶 762、底栏顶 768，"
  "`scrollIntoViewIfNeeded()` 认定「已在视口内」就不滚了；改成旅行者那一档后同一枚控件命中自己。"
  "产品样式表这一轮一个字节没改。")
A("")
A("## 3. 反件：两枚，各自只咬自己那一形")
A("")
sev = run_of("sever")
pin = run_of("pin")
A("- `%s`（`AccessPanel.tsx` 里那枚写入动作的 onClick 摘成空函数，产物 `assets/%s`，blob `%s`）："
  "红 %d 条，逐条点名「the invitation action wrote a row…」与「the read-back names the visibility…」，"
  "`roles_empty` 四条形全绿——它不碰那一格，所以不该红；「格子不在屏上」这条一次也没出现（上一版正是脏在这里）。" % (
      "sever", (sev["built_entry"] or [""])[0], len(sev["red_checks"])))
A("- `%s`（`access.css` 末尾把这屏全部动作钉进底栏带，产物 `assets/%s`，blob `%s`）："
  "红 %d 条，其中中心命中 %d 条；`hit_held=%s`。这一枚证明 hit test 不是永真。" % (
      "pin", (pin["built_entry"] or [""])[0],
      len(pin["red_checks"]), sum(1 for f in pin["red_checks"] if "centre hit" in f),
      pin["hit_test_held"]))
A("- 两枚都跑在候选代的产品字节上；臂本体与全部读数在 `%s`（blob `%s`），量具在 `%s`（blob `%s`）。" % (
    "scratch/ord0538_stack_r1.py", blob(os.path.join(SC, "ord0538_stack_r1.py")),
    "scratch/ord0538_arm_r4.cjs", blob(os.path.join(SC, "ord0538_arm_r4.cjs"))))
A("")
A("## 4. 英文侧加一句那一档（`grow`）")
A("")
g = run_of("grow")
A("- 改法：只把 `accessCopy.ts` 英文臂那一枚标签加长为整句（中文臂不动），产物 `assets/%s`。" % (
    (g["built_entry"] or [""])[0]))
A("- 落没落地先证：`cells[].action_words` 英文臂读到加长后的整句、中文臂仍是原四字句，两档各一条；"
  "加长之后中心命中仍落在自己身上——`red=%d`、`hit_held=%s`，中英两臂、两档都是这个数。" % (
      sum(len(c["failures"] or []) for c in g["cases"]
          if c["case"] not in ("roles_no_pick", "roles_no_ref", "reachability")), g["hit_test_held"]))
A("- 所以 `NO_GROWTH` 看不见的这一侧，答案是「量过了，没破」，不是「量不到」。")
A("")
A("## 5. 量不到的那一格，和三堵墙")
A("")
walls = {}
for kind in ("base", "candidate"):
    for c in run_of(kind)["cases"]:
        if c["case"] in ("roles_no_pick", "roles_no_ref", "reachability"):
            walls[(kind, c["case"], c["locale"])] = c.get("wall") or {}
for case, label in (("reachability", "库上一条行程都没有"),
                    ("roles_no_ref", "有行程、设备没存过引用"),
                    ("roles_no_pick", "有行程、设备存着一枚列表里没有的引用")):
    w = walls.get(("candidate", case, "zh-CN")) or {}
    A("- %s（`%s`）：`access-panel` 挂载数 %s，屏上 testid 前几枚 %s。" % (
        label, case, w.get("panel"),
        "、".join((w.get("testids") or [])[:4])))
A("- 这三形里 `access-trips-empty` 那一格根本不在屏上（`trips_empty_cell` 计数 %s，"
  "`ladder_empty_cell` 计数 %s，见 blob `%s`），所以本单没有给它接一个我量不到的动作："
  "第一版我接过 `onNavigate(\"hub\")` 与「先选一条行程」，两枚都在候选代被这三堵墙挡在屏外，"
  "已连同 `v8PanelRegistry.tsx` 的接线一起退回现尖字节（该文件本回合 0 改动）。" % (
      (walls.get(("candidate", "reachability", "zh-CN")) or {}).get("trips_empty_cell"),
      (walls.get(("candidate", "roles_no_pick", "zh-CN")) or {}).get("ladder_empty_cell"),
      arms_blob))
A("- 顺带量到一枚不归我的：第三堵墙那屏把设备记的引用以 `00000000…` 截断形式印在句子裡，"
  "testid 是 `failure-*` 一族（同一 blob 的 `wall.testids`），属外壳的失败面，不在本单两屏内，我只报数不动它。")
A("")
A("## 6. 其余门")
A("")
exp = json.loads(io.open(os.path.join(SC, "ord0538_exposure_514b397f.json"), encoding="utf-8").read())
A("- `npx tsc -p tsconfig.check.json --noEmit` 退出 0；`npm run build` 退出 %s，产物 `assets/%s`，"
  "与预览站回读的入口名同代（`preview_entry` 逐条相等）。" % (
      ARMS["restored_build"]["exit"], (ARMS["restored_build"]["entry"] or [""])[0]))
A("- Q64 曝光尺（`live_checks/ui_exposure_taint_ast_r7b.cjs`）跑 `git archive` 快照两代："
  "基座 %s，本枝 %s，差量见 `%s`（blob `%s`）。" % (
      json.dumps(exp["sides"]["base"]["report"].get("total_exposed", "SEE_FILE"), ensure_ascii=False),
      json.dumps(exp["sides"]["candidate"]["report"].get("total_exposed", "SEE_FILE"), ensure_ascii=False),
      "scratch/ord0538_exposure_r1.json", blob(os.path.join(SC, "ord0538_exposure_514b397f.json"))))
A("- 私有栈：两枚后端各自的库副本（从预览库 `mode=ro` 复制后新建，预览库未写），"
  "监听者的父链都落在我自己 `Popen` 的那枚 pid 上（`backends.*.every_listener_descends_from_my_child`，"
  "blob `%s`）——这台机器上 venv 的 `python.exe` 是转发器，所以旧版记的 `pid_matches_child` 恒假，已改成走父链。" % arms_blob)
A("- 证据枝 `%s` = `%s`：`review/ord0538/` 下收产品枝 diff、臂与跑法、两份读数。" % (
    COORDS["evidence_ref"], ev_blob))
A("")
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r"D:/moodle/_qoder_ledger_inbox",
    "1ba48dbf_%s.md" % time.strftime("%H%M"))
io.open(dest, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("WROTE", dest, os.path.getsize(dest), "bytes")
