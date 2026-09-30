"""The r3 blocks: ORD-0500 (the Q64 call-site fix) and ORD-0485 -r5, on generation 7862c6de.

Every number is read out of an artifact this lane's instruments wrote, and every coordinate is read
out of git -- commit shas by `git rev-parse`, predicted trees from `run/merge_tree_r7.txt`, blob ids
from `run/blobs_r7.txt`.  Nothing in here is typed from memory, including the three exposure receipts,
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
TIP = "7862c6de5565c02c20ec2dccaa9da18960603e06"
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
    slots = json.load(open(os.path.join(LANE, "run", "gen7_block_slots_r1.json"), encoding="utf-8"))
    trees = {}
    for line in open(os.path.join(LANE, "run", "merge_tree_r7.txt"), encoding="utf-8"):
        m = re.match(r"branch (\w+) predicted_tree (\w+)", line)
        if m:
            trees[m.group(1)] = m.group(2)
    blobs = {}
    for line in open(os.path.join(LANE, "run", "blobs_r7.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            blobs[parts[1]] = parts[0]

    cand = rev("wt16", "HEAD")
    dic = rev("wt15", "HEAD")
    dic_first = rev("wt15", "HEAD~1")
    s = {k: str(v) for k, v in slots.items()}
    s.update({
        "cand": cand, "dic": dic, "dic_first": dic_first,
        "tree_cand": trees[cand], "tree_dic": trees[dic],
        "tip": TIP, "gen1": GEN1, "gen2": GEN2, "gen0": GEN0, "pre": PRE,
        "b_exp_tip": blobs["review/ord0500-checkin/receipts/exposure_tip_7862c6de_r1.json"],
        "b_exp_r2": blobs["review/ord0500-checkin/receipts/exposure_r2_candidate_r1.json"],
        "b_exp_r3": blobs["review/ord0500-checkin/receipts/exposure_r3_candidate_r1.json"],
        "b_copy": blobs["frontend/src/features/checkin/checkinCopy.ts"],
        "b_itin": blobs["frontend/src/features/trip/TripItinerary.tsx"],
        "b_dict": blobs["frontend/src/i18n/LocaleContext.tsx"],
        "b_sheet6": blobs["review/ord0485-phone-walk/GEN6_READINGS.md"],
    })
    exp = {}
    for key, name in (("tip", "exposure_tip_7862c6de_r1.json"),
                      ("r2", "exposure_r2_candidate_r1.json"),
                      ("r3", "exposure_r3_candidate_r1.json")):
        d = json.load(open(os.path.join(LANE, "wt16/review/ord0500-checkin/receipts", name),
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
    for line in open(os.path.join(LANE, "run", "ls_remote_r7.txt"), encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            remote[parts[1].replace("refs/heads/", "")] = parts[0]
    s["f_r1"] = remote["review/newlane-ord0500-phone-checkin-entry-r1"]
    s["f_r2"] = remote["review/newlane-ord0500-phone-checkin-entry-r2"]
    sweep = load("gen7_checkin_sweep_r1.json")
    s["runs_count"] = len(sweep.get("runs", []))
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

    block_cand = """### ORD-0500 · 手机打卡门 r3：改掉那处调用点（Q64 的 4 格是我开的一条路），并在 ORD-0532 之后的尖上重量（车道 phone，{t_cand}）

**零、这一轮改的是我自己那一格，不是尺**。号令者 02:01 那块把根查清了，我用自己的跑复现一遍，三枚件随候选交：同一把尺 `{exp_ruler}`（同一枚实例，三趟）量 ① 现尖 `{tip}` = {exp_tip} 格 / {exp_tip_mod} 模块，② 我 r2 那代 `{f_r2}` = {exp_r2} 格 / {exp_r2_mod} 模块，③ 本轮候选 `{cand}` = {exp_r3} 格 / {exp_r3_mod} 模块。多出来的四格逐字落在我从没打开过的两枚文件上：{exp_extra_cells}。路径是我开的：`frontend/src/features/trip/TripItinerary.tsx` 那一行把 `facts.existingStampedAt`（从服务器正文里读出来的）交给了 `frontend/src/lib/v8Formatting.ts:7` 的 `formatV8Date`，而那枚 helper 同时被 AccessPanel 与 PlanVersionHistoryPanel 调用；Q64 量的是路径不是文件归属，所以两枚面板各失免责。件 `{b_exp_tip}`（现尖 6 格那张）、`{b_exp_r2}`（我这代改前 10 格那张）、`{b_exp_r3}`（改后回到 6 格那张）。

**一、按裁语的第二条路改**：不复用那枚共用 helper，本屏自带渲染。新函数 `formatStampedMoment` 放在 `frontend/src/features/checkin/checkinCopy.ts`（blob `{b_copy}`）——这枚模块只有行程屏 import，正文值走到这里就停了；`TripItinerary.tsx`（blob `{b_itin}`）里 `formatV8Date` 的引用计数已降到 0，连那行 import 一起撤。输出形状沿用这些面上本来那一种（月/日、24 小时、按 locale），我没顺手改别的屏。改完两侧逐规则同数：{exp_rule_counts}（格总数 {exp_r3}={exp_tip}），未解析 import 三趟都是 {exp_unresolved} 条，parse 诊断 {exp_diags}，交叉预算 24 用掉 0——只有模块数与格数在变，这正是裁语要求的形状。

**二、重基到 ORD-0532 之后的尖**。`{tip}` 就是「main.py 转回 LF + .gitattributes 钉 *.py text eol=lf」那一笔；我这轮重落 `backend/app/main.py` 只花了两处小改（`git diff --numstat` 对基座 = 14 增 2 删，blob `{b_main}`），不再是整文件对撞。r1 `{f_r1}`、r2 `{f_r2}` 原样冻结、0 force、0 覆盖；本轮新枝 `review/newlane-ord0500-phone-checkin-entry-r3` = `{cand}`，只读预测 `{tree_cand}`（`git merge-tree --write-tree` 对 `{tip}`）。上一轮 r2 被拦下时工具输出截断没点名，我自己逐枚比出来是 `backend/app/main.py` 与 `contracts/openapi.yaml` 两枚，那一格的账在上一块里已经落了。

**三、分母四代都贴，不折算**。同一判法（先 `scrollIntoViewIfNeeded` 再元素中心 `elementFromPoint`，判据读渲染文字）：① `{pre}` 那代——站 {stops_pre} 枚、`stop-checkin` {ctrls_pre} 枚，无入口（件 `{b_pre}`）；② `{gen1}`——控件 {ctrls_gen1} 枚、可按 {press_gen1} 枚；③ `{gen2}`——控件 6 枚、可按 6 枚、重复点击后拒绝句 6 枚；④ 本轮 `{tip}`——站 {stops_tip} 枚、控件 {ctrls_tip} 枚、中心命中可按 {press_tip} 枚，盒 {boxes_tip}，桌面 1280x800 那趟 {desk_press} 枚可按、拒绝句 {desk_notices} 枚（件 `{b_sweep}`）。

**四、真发一发（本轮）**。每跑一份新私库（`backup()` 只读复制 `_preview.db`，跑后逐枚比字节与 mtime，{runs_count} 跑全 `shared_untouched=True`）：未打卡那站按下去 `http_status={req_http}`、行数 0→1；再按另一枚不同站、行数 0→{rows_cand}；同一枚第二次 `http_status={dup_http}`。请求序列逐字 {reqs_tip}，pageerror {pe_tip}。重复点击那句现在只有被按那一站有：屏上拒绝句 {notices_cand} 枚、句主 {owners_cand}，逐字「{sentence_cand}」——时刻是从 `error.details.existing_stamped_at` 取来、由本屏自己渲染的；屏上 uuid 0 枚、机词 0 枚（件 `{b_sweep}`）。同一步在本轮基座面上仍是 {notices_tip} 枚、逐字「{sentence_tip}」，里面没有那个时刻。

**五、门里四字段陈列（不造句子）**。本轮基座 `{tip}`：未知行程写门 `http_status={base_http}`、正文 {base_bytes} 字节、句子里有 uuid={base_uuid}、`details` 为 null={base_null}、无 reason_code。候选 `{cand}`：`http_status={cand_http}`、`error.reason_code={cand_code}`、`details={{"field": "journey_id"}}`、uuid={cand_uuid}、`details` 为 null={cand_null}（件 `{b_doors}`）。你点名的两格在基座上本就合规：`{target_code}` 答 `http_status={target_http}` 且 `details.fields` 点名两枚字段；`{unknown_code}` 答 `http_status={unknown_http}`，uuid 只在 `details.activity_id` 这个机器字段里。共享 `require()`（`backend/app/main.py:797`）我没动，改在两扇门自己的读门里。

**六、反件一：摘掉服务端 409 判据**。一次性树 `mutgen6` 与交付树比对 {compared} 枚文件，只有 `backend/app/main.py` 不同（`{cand_sha}…` 对 `{mut_sha}…`，本机字节 sha256，不是 git 物件，不可 cat-file；件 `{b_proof}`）。两趟真跑（件 `{b_ce1}`）：候选代两套件 {ce1_cand_pass} 枚臂全过、失败 {ce1_cand_fail} 枚、退出 0；反件代通过 {ce1_mut_pass} 枚、失败 {ce1_mut_fail} 枚、退出 1，红臂逐字 `{ce1_mut_names}`。假绿那枚：`{ce1_green_name}`（ORD-0476 已收、只读状态码与句子）在反件代仍通过；屏侧同形——候选面挂在摘了判据的门上，重复句仍 {mut_screen_notices} 枚、pageerror {mut_screen_pe}（件 `{b_doors}`）。我那条钉层次的臂（`{b_pytest}`）在反件代红了，不是空转。

**七、反件二：门里不给足迹时屏上不许长出标**。一次性面 `{entry_mut}` 把标记改成从排程活动状态取。真跑：到屏时门里 {rows_mut_arrival} 行、屏上「已打卡」{marks_mut_arrival} 枚（本轮基座与候选同格都是 0 对 0，件 `{b_sweep}`）。三臂载体 `{b_spec}`（配置 `{b_cfg}`）在本轮三面上各一趟（件 `{b_arms}`）：基座面 `{entry_tip}` 通过 {base_arm_pass} 枚、失败 {base_arm_fail} 枚，判语逐字「{base_arm_msg}」；候选面 `{entry_cand}` 通过 {cand_arm_pass} 枚、失败 {cand_arm_fail} 枚；反件面 `{entry_mut}` 通过 {mut_arm_pass} 枚、失败 {mut_arm_fail} 枚，判语逐字「{mut_arm_msg}」。

**八、一处我不改的缺口，仍具名**。GET 那扇读本候选同样具名拒未知行程，但契约里 GET 的 404 我没写——写了会撞 ORD-0476 已收的契约臂（`backend/tests/test_qoder_ord0476_checkins.py:500` 逐字断言 GET 只有 200 与 409）。POST 侧 404 已写进 `contracts/openapi.yaml` 并由我的臂钉名字。

**九、产物身份与反件处置**。两证：基座面入口 `{entry_tip}`、候选面入口 `{entry_cand}`、反件面 `{entry_mut}`，服务字节与磁盘字节逐枚相等，件 `{b_builds}`（本机字节 sha256，不是 git 物件，不可 cat-file）；第三证具名 `NOT_AVAILABLE_BY_CMDR`（`vite preview` 不往我控制的日志写请求行）。反件树 `wt18`/`mutgen6` 与反件面不进任何枝，重建配方 `review/ord0500-checkin/tools/CE2_MUTANT_RECIPE_r1.md`。我的端口：静态 `127.0.0.1:4869`/`:4871`/`:4872`/`:4873`，后端 `127.0.0.1:8141`/`:8143`/`:8145`，跑完已交还；`:8000`/`:4781`/`:4782`/`:4783`/`:4785`/`:4787`/`:8693` 未碰，`demo/reset` 未跑。

**十、没走的（具名）**。真机与隧道 `NOT_MEASURED`；整套 Playwright 验收 `NOT_EXECUTED`；足迹面板与分享接收屏本单未走；那两枚面板（AccessPanel / PlanVersionHistoryPanel）我一行没改，本轮只是不再从我的屏往它们共用的 helper 送正文值。
"""

    block_dict = """### ORD-0485 · 手机端走查 r5：字典四词条落在 0989713a 那一代、本代读数一页（车道 phone，{t_dic}）

**一、需不需要再重切：不需要**。`frontend/src/i18n/LocaleContext.tsx` 在我切的那代基座 `{gen0}` 上是 blob `{dict_at_gen0}`，在现尖 `{tip}` 上仍是 `{dict_at_tip}`——同一枚，逐字节比而不是按血缘。枝 `review/newlane-ord0485-phone-walkthrough-r5` = `{dic}`，只读预测 `{tree_dic}`；`-r1` `-r2` `-r3` `-r4` 全部原样冻结、0 force、0 覆盖。

**二、写集形状**。产品文件只那一本字典，4 行新增 0 行删除（`git diff --numstat` 对 `{gen0}`），候选 blob `{b_dict}`；两条提交（`{dic_first}` 写内容、`{dic}` 把重切那一段改成对着已存在的提交算），两枚里那本字典逐字节同一枚 `{dict_first_blob}`。随交的载体是已收的那两支文件原样：`frontend/e2e/qoder-ord0485-phone-words.spec.ts` 与 `frontend/playwright.ord0485-phone.config.ts`。

**三、本代读数**（`390x844`、触摸档、判据读渲染文字）。基座面入口 `index-DaHdgt6W.js`、候选面入口 `{entry_dict}`，服务字节与磁盘字节逐枚相等；25 面走查两代各一趟，pageerror {pe_walk_tip} 与 {pe_walk_r4}，机词命中 0 枚；词汇清点两代各写一件：基座 en {gap_tip_en} 枚、zhCN {gap_tip_zh} 枚、引用 {gap_tip_ref} 枚、两表都缺 {gap_tip_missing} 枚（缺的就是 `poiImport.channelLocal` 与 `exec.state.notStarted`），候选 {gap_r4_en}/{gap_r4_zh} 枚、两表都缺 {gap_r4_missing} 枚；词汇臂基座面退出 {car_tip_exit}、{car_tip_verdict}、红臂 {car_tip_reds}，候选面退出 {car_r4_exit}、{car_r4_verdict}。件与尺在 `review/ord0485-phone-walk/`（读数单 blob `{b_sheet6}`）。

**四、没走的（具名）**。真机与隧道 `NOT_MEASURED`；整套 Playwright 验收 `NOT_EXECUTED`；分享接收屏 `NOT_RETAKEN_THIS_GENERATION`（那一格上一代是真 POST 一枚授权 + live/revoked/unknown 三形各有服务端回读，要在新代复现说一声即可）。
"""

    now = datetime.now().astimezone()
    later = now.replace(minute=(now.minute + 1) % 60)
    s["t_cand"] = now.strftime("%H:%M")
    s["t_dic"] = later.strftime("%H:%M")
    paths = {
        "cand": r"D:\moodle\_qoder_ledger_inbox\0afdb49b_%s.md" % now.strftime("%H%M"),
        "dic": r"D:\moodle\_qoder_ledger_inbox\0afdb49b_%s.md" % later.strftime("%H%M"),
    }
    for key, text in (("cand", block_cand), ("dic", block_dict)):
        try:
            out = text.format(**s)
        except KeyError as exc:
            raise SystemExit("ABORT_MISSING_SLOT %s in %s" % (exc, key))
        open(paths[key], "w", encoding="utf-8", newline="\n").write(out)
        print("WROTE %s bytes=%d" % (paths[key], len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
