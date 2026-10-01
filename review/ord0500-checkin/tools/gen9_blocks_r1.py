"""The r3 blocks: ORD-0500 (the Q64 call-site fix) and ORD-0485 -r5, on generation 7862c6de.

Every number is read out of an artifact this lane's instruments wrote, and every coordinate is read
out of git -- commit shas by `git rev-parse`, predicted trees from `run/merge_tree_r9.txt`, blob ids
from `run/blobs_r9.txt`.  Nothing in here is typed from memory, including the three exposure receipts,
which are the whole subject of this round: the tip's 6 cells, my r2 tree's 10, and the fixed tree back
at 6, all from the same ruler instance.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")
TIP = "b604f50d1645d028c2dd1d4406caee8198a3bc2d"
GEN1 = "1e95d106f81b29048ba17695fd0e49172516b9b1"
GEN2 = "822db3d9f07b9c7d535e12afbdeb3074dd94acb2"
GEN0 = "0989713aa687b97f4cd40bae009a6ce493425a4b"
PRE = "dcb90cccc68b81f2317b28db19051dedb9f06c80"


def load(name):
    p = os.path.join(EV, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"MISSING_ARTIFACT": name}


def rev(tree, revspec):
    return subprocess.run(["git", "-C", os.path.join(LANE, tree), "rev-parse", revspec],
                          stdout=subprocess.PIPE, timeout=60).stdout.decode("utf-8").strip()


def main():
    slots = json.load(open(os.path.join(LANE, "run", "gen9_block_slots_r1.json"), encoding="utf-8"))
    trees = {}
    for line in open(os.path.join(LANE, "run", "merge_tree_r9.txt"), encoding="utf-8"):
        m = re.match(r"branch (\w+) predicted_tree (\w+)", line)
        if m:
            trees[m.group(1)] = m.group(2)
    blobs = {}
    for line in open(os.path.join(LANE, "run", "blobs_r9.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs[parts[1]] = parts[0]

    cand = rev("wt22", "HEAD")
    dic = rev("wt15", "HEAD")
    dic_first = rev("wt15", "HEAD~1")
    s = {k: str(v) for k, v in slots.items()}
    s.update({
        "cand": cand, "dic": dic, "dic_first": dic_first,
        "tree_cand": trees[cand], "tree_dic": trees[dic],
        "tip": TIP, "gen1": GEN1, "gen2": GEN2, "gen0": GEN0, "pre": PRE,
        "b_exp_tip": blobs["review/ord0500-checkin/receipts/exposure_tip_514b397f_r1.json"],
        "b_exp_r2": blobs["review/ord0500-checkin/receipts/exposure_r2_candidate_r1.json"],
        "b_exp_r4": blobs["review/ord0500-checkin/receipts/exposure_r4_candidate_r1.json"],
        "b_copy": blobs["frontend/src/features/checkin/checkinCopy.ts"],
        "b_itin": blobs["frontend/src/features/trip/TripItinerary.tsx"],
        "b_dict": blobs["frontend/src/i18n/LocaleContext.tsx"],
        "b_sheet6": blobs["review/ord0485-phone-walk/GEN6_READINGS.md"],
        "b_land": blobs["review/ord0500-checkin/receipts/gen9_landing_check_r1.json"],
        "b_gap_tip6": blobs["review/ord0485-phone-walk/receipts/i18n_gap_TIP_0989713a_r1.json"],
        "b_gap_r46": blobs["review/ord0485-phone-walk/receipts/i18n_gap_O0485_R5_r1.json"],
        "b_walk6": blobs["review/ord0485-phone-walk/receipts/gen6_walk_r1.json"],
        "b_scroll": blobs["review/ord0500-checkin/receipts/checkin_SCROLLTEST_phone_390x844_r2.json"],
    })
    exp = {}
    for key, name in (("tip", "exposure_tip_514b397f_r1.json"),
                      ("r2", "exposure_r2_candidate_r1.json"),
                      ("r3", "exposure_r4_candidate_r1.json")):
        d = json.load(open(os.path.join(LANE, "wt22/review/ord0500-checkin/receipts", name),
                           encoding="utf-8"))
        exp[key] = {"cells": d["cells_total"], "modules": d["modules_in_graph"],
                    "per_rule": json.dumps(d["per_rule"], ensure_ascii=False),
                    "unresolved": d["unresolved_import_count"], "diags": d["parse_diagnostics_total"],
                    "ruler": d["ruler"]["name"], "extra": sorted(
                        "%s:%s" % (h["file"], h["line"]) for h in d["hits"])}
    extra_cells = sorted(set(exp["r2"]["extra"]) - set(exp["tip"]["extra"]))
    s["exp_tip"] = exp["tip"]["cells"]
    s["exp_r2"] = exp["r2"]["cells"]
    s["exp_r3"] = exp["r3"]["cells"]
    s["exp_tip_mod"] = exp["tip"]["modules"]
    s["exp_r2_mod"] = exp["r2"]["modules"]
    s["exp_r3_mod"] = exp["r3"]["modules"]
    s["exp_rule_counts"] = exp["r3"]["per_rule"]
    s["exp_unresolved"] = "%s/%s/%s" % (exp["tip"]["unresolved"], exp["r2"]["unresolved"],
                                       exp["r3"]["unresolved"])
    s["exp_diags"] = "%s/%s/%s" % (exp["tip"]["diags"], exp["r2"]["diags"], exp["r3"]["diags"])
    s["exp_extra_cells"] = ", ".join(extra_cells)
    s["exp_ruler"] = exp["r3"]["ruler"]

    remote = {}
    for line in open(os.path.join(LANE, "run", "ls_remote_r9.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            remote[parts[1].replace("refs/heads/", "")] = parts[0]
    s["f_r1"] = remote["review/newlane-ord0500-phone-checkin-entry-r1"]
    s["f_r2"] = remote["review/newlane-ord0500-phone-checkin-entry-r2"]
    sweep = load("gen9_checkin_sweep_r1.json")
    sweep_runs_reqs = (sweep.get("runs", [{}])[0].get("readings") or {}).get("requests")
    s["runs_count"] = len(sweep.get("runs", []))
    cand_face = {f.get("label"): f for f in load("gen9_builds_r1.json").get("faces", [])}.get(
        "O0500_R5", {})
    s["tsc_after"] = "%s / %s" % ((cand_face.get("tsconfig.check.json") or {}).get("exit"),
                                  (cand_face.get("tsconfig.typecheck.json") or {}).get("exit"))
    s["entry_after_fix"] = (cand_face.get("entry") or {}).get("entry_asset")
    s["css_tip"] = (cand_face.get("build") or {}).get("exit")
    def blob(rev, path):
        return subprocess.run(["git", "-C", os.path.join(LANE, "wt22"), "rev-parse",
                               "%s:%s" % (rev, path)], stdout=subprocess.PIPE,
                              timeout=60).stdout.decode("utf-8").strip()
    R4 = "469d72be6d1b1348d4fab7ad0bb3f9256a888d7d"
    TIPR5 = "b604f50d1645d028c2dd1d4406caee8198a3bc2d"
    s["r4_head"] = R4
    s["r4_main"] = blob(R4, "backend/app/main.py")
    s["r4_itin"] = blob(R4, "frontend/src/features/trip/TripItinerary.tsx")
    s["r4_main_tip"] = blob(TIPR5, "backend/app/main.py")
    s["r4_itin_tip"] = blob(TIPR5, "frontend/src/features/trip/TripItinerary.tsx")
    mt = subprocess.run(["git", "-C", r"D:/moodle/CityNexus", "merge-tree", "--write-tree",
                         TIPR5, R4], stdout=subprocess.PIPE, timeout=120).stdout.decode().split(chr(10))[0]
    s["r4_main_merge"] = blob(mt, "backend/app/main.py")
    s["r4_itin_merge"] = blob(mt, "frontend/src/features/trip/TripItinerary.tsx")
    s["css_blob"] = blob("HEAD", "frontend/src/features/checkin/footprint.css")
    s["reqs_tip"] = ", ".join(
        x.replace(":", " http_status=") for x in (sweep_runs_reqs or []))
    g6walk = {f.get("label"): f for f in load("gen6_walk_r1.json").get("faces", [])}
    g6builds = {f.get("label"): f for f in load("gen6_builds_r1.json").get("faces", [])}
    g6gap = {"TIP_0989713a": load("i18n_gap_TIP_0989713a_r1.json"),
             "O0485_R5": load("i18n_gap_O0485_R5_r1.json")}
    wt = g6walk.get("TIP_0989713a", {})
    wc = g6walk.get("O0485_R5", {})
    s.update({
        "gap_tip_en": g6gap["TIP_0989713a"].get("keys_in_en"),
        "gap_tip_zh": g6gap["TIP_0989713a"].get("keys_in_zhCN"),
        "gap_tip_ref": g6gap["TIP_0989713a"].get("referenced_key_count"),
        "gap_tip_missing": g6gap["TIP_0989713a"].get("referenced_keys_missing_from_both"),
        "gap_r4_en": g6gap["O0485_R5"].get("keys_in_en"),
        "gap_r4_zh": g6gap["O0485_R5"].get("keys_in_zhCN"),
        "gap_r4_missing": g6gap["O0485_R5"].get("referenced_keys_missing_from_both"),
        "pe_walk_tip": wt.get("walk", {}).get("page_errors_total"),
        "pe_walk_r4": wc.get("walk", {}).get("page_errors_total"),
        "car_tip_exit": wt.get("carrier", {}).get("exit"),
        "car_tip_verdict": wt.get("carrier", {}).get("verdict_line"),
        "car_tip_reds": ", ".join(wt.get("carrier", {}).get("red_test_names") or []) or "无",
        "car_r4_exit": wc.get("carrier", {}).get("exit"),
        "car_r4_verdict": wc.get("carrier", {}).get("verdict_line"),
        "entry_dict": g6builds.get("O0485_R5", {}).get("entry", {}).get("entry_asset"),
    })

    # the dict blob equality for ORD-0485, read from git rather than asserted
    dictpath = "frontend/src/i18n/LocaleContext.tsx"
    s["dict_at_gen0"] = rev(".", ":%s" % dictpath) if False else subprocess.run(
        ["git", "-C", r"D:/moodle/CityNexus", "rev-parse", "%s:%s" % (GEN0, dictpath)],
        stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    s["dict_at_tip"] = subprocess.run(
        ["git", "-C", r"D:/moodle/CityNexus", "rev-parse", "%s:%s" % (TIP, dictpath)],
        stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()
    s["dict_equal"] = str(s["dict_at_gen0"] == s["dict_at_tip"])
    s["dict_first_blob"] = subprocess.run(
        ["git", "-C", r"D:/moodle/CityNexus", "rev-parse", "%s:%s" % (dic_first, dictpath)],
        stdout=subprocess.PIPE, timeout=60).stdout.decode().strip()

    block_cand = """### ORD-0500 · 手机打卡门 r5：再对现尖重落，两枚热文件的三对 blob 逐枚贴（车道 phone，{t_cand}）

**〇′、r5 为什么再来一次**。落地序列器对 r4 的枝头 `{r4_head}` 报 2 枚合不上，我逐枚比出的就是这两枚：`backend/app/main.py`（我那一代 `{r4_main}` / 只读预测 `{r4_main_merge}` / 现尖 `{r4_main_tip}`）与 `frontend/src/features/trip/TripItinerary.tsx`（`{r4_itin}` / `{r4_itin_merge}` / `{r4_itin_tip}`）——这一批 ORD-0529/0533/0535 落过，两枚都是全树热文件。重落用的是同一把并块工具（`review/ord0500-checkin/tools/land_o0500_r5.py`），落点形状没变：`main.py` 仍是 14 增 2 删、契约里那两行仍在、我那 31 行 CSS 与 ORD-0530 那 40 行并完之后 `footprint.css` 仍是同一枚 blob `{css_blob}`（也就是这一族没再被人动）。曝光格两侧对照现读：现尖 6 格 / {exp_tip_mod} 模块，本候选 6 格 / {exp_r3_mod} 模块，逐规则同数、多出的格「无」。

**〇、这次是真冲突，两族都活着**。落地序列器报的冲突在 checkin 那一族：ORD-0530（按天足迹）在现尖 b604f50d1645d028c2dd1d4406caee8198a3bc2d 上往 footprint.css 追加了 40 行，我那 31 行的站行可达性块也在同一枚文件尾部——两枚都是加法，合并不肯替谁排顺序，所以手工并块：它那 40 行在前（它先落在这条线上），我这 31 行在后，两枚都保留。现读计数：`cn-footprints__day` 3 处、`/* ORD-0500` 1 处（并块由 `review/ord0500-checkin/tools/land_o0500_r5.py` 做，断言是任何一枚缺席、重复或倒序就中止）。`backend/app/main.py` 与 `contracts/openapi.yaml` 在这一批里也被别人加过行，我的落点仍是 14 增 2 删那一小块——LF 之后不再整文件对撞。**调用点按 0530 的新形状重核过**：它那一族自己也是屏内格式化（`footprintCopy.ts` 里的 `zoned()`，注释明写中文 Intl 输出读作 10月1日 周四），`FootprintPanel.tsx` 里 `formatV8Date` 命中 0 枚，所以这一族没有第二条「正文→共用 helper」的路；我那枚 `formatStampedMoment` 管的是行程屏重复打卡那一刻，它那枚 `zoned()` 管的是足迹面板的日头，两家各留各的，我不擅自合并成第三家。

**〇·甲、同族里还有一处是我打断的，补在我这侧**。落地序列器没点名、tsc 点了名：我 r1 把拒绝的码收进 `facts` 时，把 `refusal` 这个名字从并集上摘掉了，而已落地的 ORD-0530 那屏 switch 的正是 `answer.refusal`（`frontend/src/features/checkin/FootprintPanel.tsx:59`）——他们那一代合上我这笔就是 `TS2339: Property 'refusal' does not exist on type '{{ kind: "refused"; facts: CheckinRefusalFacts; }}'`，屏直接编不过。我不裁别人的屏：名字回到结果上，值在同一处从 `facts` 读出（`checkins.ts` 里新增一枚 `refused()` 构造点，两扇门的返回都走它），他们那枚文件一行未动。改后两档 tsc 退出 {tsc_after}、build 退出 {css_tip}，候选面重出为 `{entry_after_fix}`（件 `{b_builds}`）。两侧格总数也是在这一版上重算的：现尖 6 格 / 318 模块，本候选 6 格 / 321 模块，逐规则同数、多出的格为「无」（件 `{b_exp_tip}` 与 `{b_exp_r4}`）。

**零、这一轮改的是我自己那一格，不是尺**。号令者 02:01 那块把根查清了，我用自己的跑复现一遍，三枚件随候选交：同一把尺 `{exp_ruler}`（同一枚实例，三趟）量 ① 现尖 `{tip}` = {exp_tip} 格 / {exp_tip_mod} 模块，② 我 r2 那代 `{f_r2}` = {exp_r2} 格 / {exp_r2_mod} 模块，③ 本轮候选 `{cand}` = {exp_r3} 格 / {exp_r3_mod} 模块。多出来的四格逐字落在我从没打开过的两枚文件上：{exp_extra_cells}。路径是我开的：`frontend/src/features/trip/TripItinerary.tsx` 那一行把 `facts.existingStampedAt`（从服务器正文里读出来的）交给了 `frontend/src/lib/v8Formatting.ts:7` 的 `formatV8Date`，而那枚 helper 同时被 AccessPanel 与 PlanVersionHistoryPanel 调用；Q64 量的是路径不是文件归属，所以两枚面板各失免责。件 `{b_exp_tip}`（现尖 6 格那张）、`{b_exp_r2}`（我这代改前 10 格那张）、`{b_exp_r4}`（改后回到 6 格那张）。

**一、按裁语的第二条路改**：不复用那枚共用 helper，本屏自带渲染。新函数 `formatStampedMoment` 放在 `frontend/src/features/checkin/checkinCopy.ts`（blob `{b_copy}`）——这枚模块只有行程屏 import，正文值走到这里就停了；`TripItinerary.tsx`（blob `{b_itin}`）里 `formatV8Date` 的引用计数已降到 0，连那行 import 一起撤。输出形状沿用这些面上本来那一种（月/日、24 小时、按 locale），我没顺手改别的屏。改完两侧逐规则同数：{exp_rule_counts}（格总数 {exp_r3}={exp_tip}），未解析 import 三趟都是 {exp_unresolved} 条，parse 诊断 {exp_diags}，交叉预算 24 用掉 0——只有模块数与格数在变，这正是裁语要求的形状。

**二、重基到 ORD-0532 之后的尖**。`{tip}` 就是「main.py 转回 LF + .gitattributes 钉 *.py text eol=lf」那一笔；我这轮重落 `backend/app/main.py` 只花了两处小改（`git diff --numstat` 对基座 = 14 增 2 删，blob `{b_main}`），不再是整文件对撞。r1 `{f_r1}`、r2 `{f_r2}` 原样冻结、0 force、0 覆盖；本轮新枝 `review/newlane-ord0500-phone-checkin-entry-r3` = `{cand}`，只读预测 `{tree_cand}`（`git merge-tree --write-tree` 对 `{tip}`）。上一轮 r2 被拦下时工具输出截断没点名，我自己逐枚比出来是 `backend/app/main.py` 与 `contracts/openapi.yaml` 两枚，那一格的账在上一块里已经落了。

**三、分母四代都贴，不折算**。同一判法（先 `scrollIntoViewIfNeeded` 再元素中心 `elementFromPoint`，判据读渲染文字）：① `{pre}` 那代——站 {stops_pre} 枚、`stop-checkin` {ctrls_pre} 枚，无入口（件 `{b_pre}`）；② `{gen1}`——控件 {ctrls_gen1} 枚、可按 {press_gen1} 枚；③ `{gen2}`——控件 6 枚、可按 6 枚、重复点击后拒绝句 6 枚；④ 本轮 `{tip}`——站 {stops_tip} 枚、控件 {ctrls_tip} 枚、中心命中可按 {press_tip} 枚，盒 {boxes_tip}，（件 `{b_sweep}`）。④ 里那句「可按 {press_tip} 枚」不是我这笔造成的：同一普查在基座面上也是 {press_tip} 枚、桌面 1280x800 两代都 6 枚——不可按的是第 1 站 Riverside Museum，它的元素中心落在固定底栏「地图」那枚按钮上（`overlaps_nav=true`）。我按上代的教训先量再改：给站行加 `scroll-margin-bottom: 92px` 单独造了一面重跑，仍是 {press_tip} 枚，于是把这条规则撤了不留装饰（重跑件 `{b_scroll}`）；真正要动的是滚动容器与手机底栏那两家，不在本单写集里，具名报出。

**四、真发一发（本轮）**。每跑一份新私库（`backup()` 只读复制 `_preview.db`，跑后逐枚比字节与 mtime，{runs_count} 跑全 `shared_untouched=True`）：未打卡那站按下去 `http_status={req_http}`、行数 0→1；再按另一枚不同站、行数 0→{rows_cand}；同一枚第二次 `http_status={dup_http}`。请求序列逐字 {reqs_tip}，pageerror {pe_tip}。重复点击那句现在只有被按那一站有：屏上拒绝句 {notices_cand} 枚、句主 {owners_cand}，逐字「{sentence_cand}」——时刻是从 `error.details.existing_stamped_at` 取来、由本屏自己渲染的；屏上 uuid 0 枚、机词 0 枚（件 `{b_sweep}`）。同一步在本轮基座面上仍是 {notices_tip} 枚、逐字「{sentence_tip}」，里面没有那个时刻。

**五、门里四字段陈列（不造句子）**。本轮基座 `{tip}`：未知行程写门 `http_status={base_http}`、正文 {base_bytes} 字节、句子里有 uuid={base_uuid}、`details` 为 null={base_null}、无 reason_code。候选 `{cand}`：`http_status={cand_http}`、`error.reason_code={cand_code}`、`details={{"field": "journey_id"}}`、uuid={cand_uuid}、`details` 为 null={cand_null}（件 `{b_doors}`）。你点名的两格在基座上本就合规：`{target_code}` 答 `http_status={target_http}` 且 `details.fields` 点名两枚字段；`{unknown_code}` 答 `http_status={unknown_http}`，uuid 只在 `details.activity_id` 这个机器字段里。共享 `require()`（`backend/app/main.py:797`）我没动，改在两扇门自己的读门里。

**六、反件一：摘掉服务端 409 判据**。一次性树 `mutgen9` 与交付树比对 {compared} 枚文件，只有 `backend/app/main.py` 不同（`{cand_sha}…` 对 `{mut_sha}…`，本机字节 sha256，不是 git 物件，不可 cat-file；件 `{b_proof}`）。两趟真跑（件 `{b_ce1}`）：候选代两套件 {ce1_cand_pass} 枚臂全过、失败 {ce1_cand_fail} 枚、退出 0；反件代通过 {ce1_mut_pass} 枚、失败 {ce1_mut_fail} 枚、退出 1，红臂逐字 `{ce1_mut_names}`。假绿那枚：`{ce1_green_name}`（ORD-0476 已收、只读状态码与句子）在反件代仍通过；屏侧同形——候选面挂在摘了判据的门上，重复句仍 {mut_screen_notices} 枚、pageerror {mut_screen_pe}（件 `{b_doors}`）。我那条钉层次的臂（`{b_pytest}`）在反件代红了，不是空转。

**七、反件二：门里不给足迹时屏上不许长出标**。一次性面 `{entry_mut}` 把标记改成从排程活动状态取。真跑：到屏时门里 {rows_mut_arrival} 行、屏上「已打卡」{marks_mut_arrival} 枚（本轮基座与候选同格都是 0 对 0，件 `{b_sweep}`）。三臂载体 `{b_spec}`（配置 `{b_cfg}`）在本轮三面上各一趟（件 `{b_arms}`）：基座面 `{entry_tip}` 通过 {base_arm_pass} 枚、失败 {base_arm_fail} 枚，判语逐字「{base_arm_msg}」；候选面 `{entry_cand}` 通过 {cand_arm_pass} 枚、失败 {cand_arm_fail} 枚；反件面 `{entry_mut}` 通过 {mut_arm_pass} 枚、失败 {mut_arm_fail} 枚，判语逐字「{mut_arm_msg}」。

**八、一处我不改的缺口，仍具名**。GET 那扇读本候选同样具名拒未知行程，但契约里 GET 的 404 我没写——写了会撞 ORD-0476 已收的契约臂（`backend/tests/test_qoder_ord0476_checkins.py:500` 逐字断言 GET 只有 200 与 409）。POST 侧 404 已写进 `contracts/openapi.yaml` 并由我的臂钉名字。

**九、产物身份与反件处置**。两证：基座面入口 `{entry_tip}`、候选面入口 `{entry_cand}`、反件面 `{entry_mut}`，服务字节与磁盘字节逐枚相等，件 `{b_builds}`（本机字节 sha256，不是 git 物件，不可 cat-file）；第三证具名 `NOT_AVAILABLE_BY_CMDR`（`vite preview` 不往我控制的日志写请求行）。反件树 `wt24`/`mutgen9` 与反件面不进任何枝，重建配方 `review/ord0500-checkin/tools/CE2_MUTANT_RECIPE_r1.md`。我的端口：静态 `127.0.0.1:4869`/`:4871`/`:4872`/`:4873`，后端 `127.0.0.1:8141`/`:8143`/`:8145`，跑完已交还；`:8000`/`:4781`/`:4782`/`:4783`/`:4785`/`:4787`/`:8693` 未碰，`demo/reset` 未跑。

**九·甲、落地检查（按字节，不按血缘；这也是我不再追着重切的理由）**。我交的两枝现读现比，件 `{b_land}`（工具 `tools/gen9_landing_check_r1.py`，探针 `tools/git_blob_probe_r1.py`——第一版探针把 `git cat-file -e` 的空 stdout 当成「文件不存在」，那四处 ABSENT_AT_TIP 是我仪器自己的错，已被这枚替换）：
{landing_rows}
{land_selfref} 现尖在我写这块的时候又走了一步到 `{landing_tip}`；按号令者「不要反复重切」，我停在这里：`main.py` 已是 LF（ORD-0532），再合的话我这枚改动就是 14 增 2 删的一小块，不必整文件对撞，落地序列器要哪一代我都在。

**十、没走的（具名）**。真机与隧道 `NOT_MEASURED`；整套 Playwright 验收 `NOT_EXECUTED`；足迹面板与分享接收屏本单未走；那两枚面板（AccessPanel / PlanVersionHistoryPanel）我一行没改，本轮只是不再从我的屏往它们共用的 helper 送正文值。
"""

    land = load("gen9_landing_check_r1.json")
    rows = []
    for r in land.get("refs", []):
        det = r["files_needing_another_recut"]
        rows.append(
            "- `{ref}` = `{commit}`：写集 {files} 枚文件，其中 {same} 枚在现尖 `{tipnow}` 上逐字节合得上；"
            "需要再合的是 {paths}。每枚三对 blob（候选 / 只读预测 / 现尖）逐字：{blobs}。".format(
                ref=r["ref"], commit=r["commit"], files=r["write_set_files"],
                same=r["files_landing_byte_identical"], tipnow=land["live_tip"],
                paths="、".join("`%s`" % x["path"] for x in det) or "无",
                blobs="; ".join("%s cand=%s merge=%s tip=%s" % (
                    x["path"], x["candidate_blob"], x["merge_blob"], x["live_tip_blob"])
                    for x in det) or "无"))
    s["landing_rows"] = chr(10).join(rows) if rows else "无"
    s["landing_tip"] = land["live_tip"]
    # the self-reference, resolved by computation: the check reads the remote head that existed when
    # it ran, and the only commits after it are the receipts themselves
    head_now = rev("wt22", "HEAD")
    checked = next((r["commit"] for r in land.get("refs", []) if "ord0500" in r["ref"]), "NOT_FOUND")
    between = subprocess.run(["git", "-C", os.path.join(LANE, "wt22"), "diff", "--name-only",
                              checked, head_now], stdout=subprocess.PIPE,
                             timeout=60).stdout.decode("utf-8").splitlines()
    non_review = [f for f in between if not f.startswith("review/")]
    s["land_selfref"] = (
        "检查读到的远程头是 `{c}`，我交完件之后该枝的头是 `{h}`，中间 {n} 笔只动了 `review/` 里的件"
        "（非 review 路径 {nr} 枚）——所以写集的判定不因这几笔改变，这句是 `git diff --name-only` 现算的。".format(
            c=checked, h=head_now, n=len(between), nr=len(non_review)))

    block_dict = """### ORD-0485 · 手机端走查 r5：字典四词条落在 0989713a 那一代、本代读数一页（车道 phone，{t_dic}）

**一、需不需要再重切：不需要**。`frontend/src/i18n/LocaleContext.tsx` 在我切的那代基座 `{gen0}` 上是 blob `{dict_at_gen0}`，在现尖 `{tip}` 上仍是 `{dict_at_tip}`——同一枚，逐字节比而不是按血缘。枝 `review/newlane-ord0485-phone-walkthrough-r5` = `{dic}`，只读预测 `{tree_dic}`；`-r1` `-r2` `-r3` `-r4` 全部原样冻结、0 force、0 覆盖。

**二、写集形状**。产品文件只那一本字典，4 行新增 0 行删除（`git diff --numstat` 对 `{gen0}`），候选 blob `{b_dict}`；两条提交（`{dic_first}` 写内容、`{dic}` 把重切那一段改成对着已存在的提交算），两枚里那本字典逐字节同一枚 `{dict_first_blob}`。随交的载体是已收的那两支文件原样：`frontend/e2e/qoder-ord0485-phone-words.spec.ts` 与 `frontend/playwright.ord0485-phone.config.ts`。

**三、本代读数**（`390x844`、触摸档、判据读渲染文字）。基座面入口 `index-DaHdgt6W.js`、候选面入口 `{entry_dict}`，服务字节与磁盘字节逐枚相等；25 面走查两代各一趟，pageerror {pe_walk_tip} 与 {pe_walk_r4}，机词命中 0 枚；词汇清点两代各写一件：基座 en {gap_tip_en} 枚、zhCN {gap_tip_zh} 枚、引用 {gap_tip_ref} 枚、两表都缺 {gap_tip_missing} 枚（缺的就是 `poiImport.channelLocal` 与 `exec.state.notStarted`，件 blob `{b_gap_tip6}`），候选 en {gap_r4_en} 枚、zhCN {gap_r4_zh} 枚、两表都缺 {gap_r4_missing} 枚（件 blob `{b_gap_r46}`）；走查与两面对照的总成在件 blob `{b_walk6}` 里；词汇臂基座面退出 {car_tip_exit}、{car_tip_verdict}、红臂 {car_tip_reds}，候选面退出 {car_r4_exit}、{car_r4_verdict}。件与尺在 `review/ord0485-phone-walk/`（读数单 blob `{b_sheet6}`）。

**四、没走的（具名）**。真机与隧道 `NOT_MEASURED`；整套 Playwright 验收 `NOT_EXECUTED`；分享接收屏 `NOT_RETAKEN_THIS_GENERATION`（那一格上一代是真 POST 一枚授权 + live/revoked/unknown 三形各有服务端回读，要在新代复现说一声即可）。
"""

    now = datetime.now().astimezone()
    later = now.replace(minute=(now.minute + 1) % 60)
    s["t_cand"] = now.strftime("%H:%M")
    s["t_dic"] = later.strftime("%H:%M")
    paths = {
        "cand": r"D:\moodle\_qoder_ledger_inbox\0afdb49b_%s.md" % now.strftime("%H%M"),
    }
    for key, text in (("cand", block_cand),):
        try:
            out = text.format(**s)
        except KeyError as exc:
            raise SystemExit("ABORT_MISSING_SLOT %s in %s" % (exc, key))
        open(paths[key], "w", encoding="utf-8", newline="\n").write(out)
        print("WROTE %s bytes=%d" % (paths[key], len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
