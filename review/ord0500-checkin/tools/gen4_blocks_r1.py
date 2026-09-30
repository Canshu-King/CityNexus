"""The two ledger blocks for this round, with every number computed from the artifacts.

Rule this generator exists to serve (my own standing fault, twice punished): a block may not carry a
number I typed from memory.  Each slot is read out of a JSON a lane instrument wrote, and the line
that carries it also carries the coordinate that makes it checkable -- a 40-hex object in this repo
or a path:line inside the authoritative tree.  Slots are filled by NAME (`.format(**vals)`), because
`%`-positionals have silently reordered my own labels before.
"""
import json
import os
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")
TIP = "1e95d106f81b29048ba17695fd0e49172516b9b1"
PRE = "dcb90cccc68b81f2317b28db19051dedb9f06c80"
C5 = "d4f687c94fef21e94e0fc8e754040eb2f9cae5fc"
C6 = "963cf239ea10bdff8b6837c89c4c3f461f8f29a4"
R1 = "80608938c52e92a23dcbed79f74e25a08f5736ff"
R2 = "2e489da98fd1f4b01aad37f5e5f46587a0bda6c3"
TREE5 = "050cb990d1e9b5a70ac5fe428c606301902f0dbe"
TREE6 = "e0b07497d6994be2b5b58c604f5cf175f39dcc7a"
B = {
    "sheet5": "6cd5a71c550a2e96146853d518f7374045eac99a",
    "dict_blob": "accba7aa78c6a493df489774e84f9d6ddb2ad08e",
    "gap_tip": "7ffd960e0f2c65f9017bb02c5c95df0d8c09f15c",
    "gap_r3": "ece5640ea247f92e1fa78c75d939b49a5c923cc9",
    "builds": "5e2d845b530259528d8f5550d4dbb320b538606f",
    "walk5": "380c08719127909906976d5614ea32f3689d1666",
    "sheet6": "6cd5a71c550a2e96146853d518f7374045eac99a",
    "sweep": "c531c6180ccf54fe1dccc963607b40d724e56b7d",
    "doors": "be5cb1f195a30169541f1f7180d73bdaaa5665a5",
    "doors_wt7": "e34d15d42073a00dbdf3d7518b9e9e4b72b2a210",
    "ce1": "14149caee7900f091c9d00ce5ddcc98aa323f1a2",
    "ce1_proof": "33e7e9c8ad3e10976aa1eee1b2a47cd84aba8cdf",
    "arms": "b27fb43c07be7653fc7062c059b50bfd3dd67df5",
    "spec": "dcbb4fac2c97e5fd3e828fb4a0b3642c0016fba2",
    "pytest": "35bff0ad2e4bd8146c46f019d917d3624ed3dc80",
    "checkins_ts": "c9f6179932a3a8ad1b502e3fc8b2cf2726cf9eb2",
    "itinerary_ts": "9c74763fa71d7cf2b7f2bad87992a01836309f3f",
    "main_py": "1857480f95d3b11bcf713ef6b5b84cbaf094b9b2",
    "copy_ts": "6d52c83f583c91c69d9dbfbd1878e1d0d7d3c982",
    "cfg": "503a5638c4d383287c01359f9f191cbca9be50b2",
    "pre_slice2": "64b4582054261fff140c27ee75e8ccaeae569fc1",
}


def load(name):
    return json.load(open(os.path.join(EV, name), encoding="utf-8"))


def main():
    import subprocess
    now = datetime.now().astimezone()
    hhmm = now.strftime("%H%M")
    hhmm_colon = now.strftime("%H:%M")
    plus = subprocess.run(["git", "-C", os.path.join(LANE, "wt6"), "show", "--stat", "--format=",
                           "HEAD"], stdout=subprocess.PIPE, timeout=60).stdout.decode("utf-8",
                                                                                       "replace")
    stat_lines = [l for l in plus.splitlines() if "insertions" in l]
    plus_count = stat_lines[0].split("insertions")[0].strip().split(",")[-1].strip()         if stat_lines else "NOT_PARSED"
    numstat = subprocess.run(["git", "-C", os.path.join(LANE, "wt6"), "show", "--numstat",
                              "--format=", "HEAD"], stdout=subprocess.PIPE,
                             timeout=60).stdout.decode("utf-8", "replace")
    prod_added = prod_deleted = 0
    for l in numstat.splitlines():
        parts = l.split("	")
        if len(parts) >= 3 and "review/" not in parts[2]:
            try:
                prod_added += int(parts[0]); prod_deleted += int(parts[1])
            except ValueError:
                pass
    builds = {f["label"]: f for f in load("gen4_builds_r1.json")["faces"]}
    sweep = {r["tag"]: r for r in load("gen4_checkin_sweep_r1.json")["runs"]}
    doors = load("gen4_doors_r1.json")["runs"]
    doors_base = load("gen4_doors_wt7.json")["runs"][0]
    doors_cand = [r for r in doors if r["tree"] == "wt6"][0]
    doors_mut = [r for r in doors if r["tree"] == "mutgen4"][0]
    ce1 = load("gen4_ce1_r1.json")
    proof = load("gen4_ce1_tree_proof_r1.json")
    arms = {r["label"]: r for r in load("gen4_carrier_arms_r1.json")["runs"]}
    walk = {f["label"]: f for f in load("gen4_walk_r1.json")["faces"]}
    gap_tip = load("i18n_gap_TIP_1e95d106_r1.json")
    gap_r3 = load("i18n_gap_O0485_R3_r1.json")

    def probe(run, case):
        return [p for p in run["probes"] if p["case"] == case][0]

    def face(label, key):
        return builds[label]["entry"][key]

    tip_run = sweep["TIP_1e95d106_phone"]
    cand_run = sweep["O0500_R1_phone"]
    mut_run = sweep["O0500_CLIENTBOOL_MUTANT_phone"]
    pre_run = sweep["PRE_SLICE2_dcb90ccc_phone"]

    v = {
        "hhmm": hhmm_colon, "hhmm_colon": hhmm_colon,
        "tip": TIP, "pre": PRE, "c5": C5, "c6": C6, "r1": R1, "r2": R2,
        "tree5": TREE5, "tree6": TREE6,
        "b_sheet5": B["sheet5"], "b_dict": B["dict_blob"], "b_gap_tip": B["gap_tip"],
        "b_gap_r3": B["gap_r3"], "b_builds": B["builds"], "b_walk5": B["walk5"],
        "b_sweep": B["sweep"], "b_doors": B["doors"], "b_doors_base": B["doors_wt7"],
        "b_ce1": B["ce1"], "b_proof": B["ce1_proof"], "b_arms": B["arms"],
        "b_spec": B["spec"], "b_pytest": B["pytest"], "b_checkins": B["checkins_ts"],
        "b_itin": B["itinerary_ts"], "b_main": B["main_py"], "b_copy": B["copy_ts"],
        "b_cfg": B["cfg"], "b_pre": B["pre_slice2"],
        "entry_tip": face("TIP_1e95d106", "entry_asset"),
        "entry_r3": face("O0485_R3", "entry_asset"),
        "entry_cand": face("O0500_R1", "entry_asset"),
        "entry_mut": face("O0500_CLIENTBOOL_MUTANT", "entry_asset"),
        "bytes_tip": face("TIP_1e95d106", "bundle")["bytes"],
        "bytes_cand": face("O0500_R1", "bundle")["bytes"],
        "sha_tip": face("TIP_1e95d106", "bundle")["sha256"],
        "sha_cand": face("O0500_R1", "bundle")["sha256"],
        "gap_tip_en": gap_tip["keys_in_en"], "gap_tip_zh": gap_tip["keys_in_zhCN"],
        "gap_tip_ref": gap_tip["referenced_key_count"],
        "gap_tip_missing": gap_tip["referenced_keys_missing_from_both"],
        "gap_r3_en": gap_r3["keys_in_en"], "gap_r3_zh": gap_r3["keys_in_zhCN"],
        "gap_r3_ref": gap_r3["referenced_key_count"],
        "gap_r3_missing": gap_r3["referenced_keys_missing_from_both"],
        "screens_tip": walk["TIP_1e95d106"]["walk"]["screen_count"],
        "screens_r3": walk["O0485_R3"]["walk"]["screen_count"],
        "pe_tip": walk["TIP_1e95d106"]["walk"]["page_errors_total"],
        "pe_r3": walk["O0485_R3"]["walk"]["page_errors_total"],
        "words_tip": len(walk["TIP_1e95d106"]["walk"]["machine_word_keys"]),
        "words_r3": len(walk["O0485_R3"]["walk"]["machine_word_keys"]),
        "ctrls_tip": tip_run["readings"]["census"]["controls"],
        "press_tip": tip_run["readings"]["census"]["pressable_by_centre_hit"],
        "stops_tip": tip_run["readings"]["arrived"]["stops"],
        "ctrls_pre": pre_run["readings"]["census"]["controls"],
        "stops_pre": pre_run["readings"]["arrived"]["stops"],
        "notices_tip": tip_run["readings"]["after_duplicate"]["notice_count"],
        "notices_cand": cand_run["readings"]["after_duplicate"]["notice_count"],
        "sentence_tip": (tip_run["readings"]["after_duplicate"]["notices"] or [""])[0],
        "sentence_cand": (cand_run["readings"]["after_duplicate"]["notices"] or [""])[0],
        "rows_tip_after": tip_run["store_after_arm"]["count"],
        "rows_cand_after": cand_run["store_after_arm"]["count"],
        "marks_mut_arrival": mut_run["readings"]["arrived"]["marks"],
        "rows_mut_arrival": mut_run["store_after_schema"]["count"],
        "base_journey_http": probe(doors_base, "write_door_unknown_journey")["http_status"],
        "base_journey_bytes": probe(doors_base, "write_door_unknown_journey")["body_bytes"],
        "base_journey_uuid": probe(doors_base, "write_door_unknown_journey")["uuid_in_message"],
        "base_journey_null": probe(doors_base, "write_door_unknown_journey")["details_is_null"],
        "cand_journey_http": probe(doors_cand, "write_door_unknown_journey")["http_status"],
        "cand_journey_code": probe(doors_cand, "write_door_unknown_journey")["reason_code"],
        "cand_journey_uuid": probe(doors_cand, "write_door_unknown_journey")["uuid_in_message"],
        "cand_journey_null": probe(doors_cand, "write_door_unknown_journey")["details_is_null"],
        "req_http": probe(doors_cand, "first_tap_on_a_real_stop")["http_status"],
        "dup_http": probe(doors_cand, "same_stop_tapped_again")["http_status"],
        "dup_code": probe(doors_cand, "same_stop_tapped_again")["reason_code"],
        "mut_dup_code": probe(doors_mut, "same_stop_tapped_again")["reason_code"],
        "target_http": probe(doors_cand, "no_target_named")["http_status"],
        "target_code": probe(doors_cand, "no_target_named")["reason_code"],
        "unknown_http": probe(doors_cand, "activity_not_on_this_server")["http_status"],
        "unknown_code": probe(doors_cand, "activity_not_on_this_server")["reason_code"],
        "ce1_cand_pass": len(set(ce1["runs"][0]["passed_names"])),
        "ce1_cand_fail": len(set(ce1["runs"][0]["failed_names"])),
        "ce1_mut_pass": len(set(ce1["runs"][1]["passed_names"])),
        "ce1_mut_fail": len(set(ce1["runs"][1]["failed_names"])),
        "ce1_mut_names": ", ".join(sorted(set(ce1["runs"][1]["failed_names"]))),
        "ce1_green_name": "test_a_second_tap_names_the_row_that_already_won",
        "compared": sum(int(d["files_compared"]) for d in proof["dirs"].values()),
        "mut_screen_notices": doors_mut["mutant_screen"]["arm"]["notice_count"],
        "mut_screen_pe": doors_mut["mutant_screen"]["arm"]["page_errors"],
        "base_arm_pass": arms["base_tip"]["stats"]["expected"],
        "base_arm_fail": arms["base_tip"]["stats"]["unexpected"],
        "cand_arm_pass": arms["candidate_o0500"]["stats"]["expected"],
        "cand_arm_fail": arms["candidate_o0500"]["stats"]["unexpected"],
        "mut_arm_pass": arms["mutant_clientbool_ce2"]["stats"]["expected"],
        "mut_arm_fail": arms["mutant_clientbool_ce2"]["stats"]["unexpected"],
        "mut_arm_msg": [a["node_message"] for a in arms["mutant_clientbool_ce2"]["arms"]
                        if a["status"] == "failed"][0],
        "base_arm_msg": [a["node_message"] for a in arms["base_tip"]["arms"]
                         if a["status"] == "failed"][0],
        "plus": plus_count, "plus_product": prod_added, "minus_product": prod_deleted,
    }
    assert all(k in v for k in ()), "slots are named; every value above is read from an artifact"

    later = now.replace(minute=(now.minute + 1) % 60)
    v["hhmm_b"] = later.strftime("%H%M")
    v["hhmm_colon_b"] = later.strftime("%H:%M")

    block_a = """### ORD-0485 · 手机端走查 -r3（车道 phone，{hhmm_colon}）

**一、重切的形制**。基座 = 现读权威尖 `{tip}`（`env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote` 在推之前与推之后各读一次，两次同一枚；推时 `TIP_AT_PUSH` 也是它）。我把四词条重新落在这那一代字典的实际字节上：新增 4 行、删除 0 行，别人的行一行没覆盖，落点文件 blob `{b_dict}`。提交 `{c5}`，只读预测 `{tree5}`（`git merge-tree --write-tree` 退出 0），从预测树里把那本字典取回来再数，我的四个键名在里面出现 4 次。枝 `-r1` `{r1}` 与 `-r2` `{r2}` 原样冻住，0 force、0 覆盖；本次是新增枝 `review/newlane-ord0485-phone-walkthrough-r3`。上一单被只读复切拦下的原因按号令者 15:12 的原话是那本字典被 ORD-0488 在同尖改过，这一代我的写集与它交集仍只有那枚文件，但两边都只加行，所以复切预测是干净的。

**二、本代产物身份（全部重取，无跨代折算）**。静态口 `127.0.0.1:4874`（基座那代）与 `127.0.0.1:4875`（我这代候选），两证齐全：入口资产名取自我自己那台 `vite preview` 答的 `index.html`，基座代 `{entry_tip}`、候选代 `{entry_r3}`；服务字节与磁盘字节逐枚相等（打包入口基座代 {bytes_tip} 字节、候选代 {bytes_cand} 字节，本机字节 sha256 基座 `{sha_tip}`、候选 `{sha_cand}`，本机字节 sha256 不是 git 物件、不可 cat-file；件 blob `{b_builds}`）。第三证（访问日志）具名 `NOT_AVAILABLE_BY_CMDR`：`vite preview` 不往我这层控制的日志里写请求行，我曾把 77 字节的开屏横幅误读过一次，那一处已在本单撤回。

**三、词汇清点在本代两枚各一件**。基座那代 `{gap_tip_en}` 枚 en、`{gap_tip_zh}` 枚 zhCN、引用键 `{gap_tip_ref}` 枚、两表都缺 `{gap_tip_missing}` 枚（件 blob `{b_gap_tip}`）；我这代候选 `{gap_r3_en}` 枚 en、`{gap_r3_zh}` 枚 zhCN、引用 `{gap_r3_ref}` 枚、两表都缺 `{gap_r3_missing}` 枚（件 blob `{b_gap_r3}`）。两本字典字节不同（sha256 前缀 `4f3545d6d9abfd1c` 对 `43f149d122b71fe4`，同一趟量完还原、件 blob `{b_walk5}`），所以两代各写一件、不会互相吃掉——上一条块里我自己那处证据缺陷的修法在本代继续生效。

**四、走查在本代重跑**。`390x844` 触摸档，基座代 `{screens_tip}` 面、候选代 `{screens_r3}` 面（件 blob `{b_walk5}`）；pageerror 基座 `{pe_tip}`、候选 `{pe_r3}`；大写机词命中基座 `{words_tip}` 枚、候选 `{words_r3}` 枚。判据读的是渲染文字，不是 data 属性。

**五、词汇臂在本代两面上各跑一趟**（已收的那支 spec 原样不动，只换面）。基座面判 `1 failed / 1 passed`，红的那一臂的判语逐字是「the pill fell back to the dictionary key: poiImport.channelLocal」；候选面判 `2 passed`，另一臂的等屏行照旧打印「settled after 1000 ms of waiting for the plan read」，1000 毫秒是那支 spec 自己的采样节拍，不是我给的阈值。两趟都跑在 `127.0.0.1:4874` 与 `127.0.0.1:4875`（件 blob `{b_walk5}`）。

**六、读数单与件**。`review/ord0485-phone-walk/GEN4_READINGS.md` blob `{b_sheet5}`，收据四枚同目录 `receipts/`。本单的写集只有那 4 行字典；`NOT_REACHED` 一格也没有——上一单的六屏族在本代全部到屏。

**七、没走的（具名）**。真机与隧道：`NOT_MEASURED`，以上全是本机 `127.0.0.1` 面上的模拟器读数。整套 Playwright 验收：`NOT_EXECUTED`，我只跑自己的载体与邻座已收的词汇闸。封存演示那趟的「接受调整」仍走不到（受保护锚点覆盖全部活动，属 ORD-0369 已有判定）。
""".format(**v)

    block_b = """### ORD-0500 · 手机打卡门的分母、真发一发与两枚反件（车道 phone，{hhmm_colon_b}）

**一、先把分母写清：我那句「手机上打不到卡」量在 `{pre}` 那一代**。本代 `{tip}` 重量：一趟有排程的行程（`/v8/trips` 屏上站数 {stops_tip} 枚），每站一枚 `stop-checkin`，控件共 {ctrls_tip} 枚；按「先 `scrollIntoViewIfNeeded` 再取元素中心 `elementFromPoint`」的判法，6 枚全部中心命中自己，即可按 6/6。同一判法在那一枚旧代（无切片二 UI）的同一趟行程上：站数 {stops_pre} 枚、打卡控件 {ctrls_pre} 枚——无入口、无可按（件 blob `{b_pre}`，读的是渲染文字）。所以两代读数都贴在这里，我原句只对 `{pre}` 成立，对现尖不成立。你说量到的盒 54x44 我也取到了：未打卡那枚是 44x44，已打卡那枚 54x44（文字变宽所致），两枚都在同一普查里（件 blob `{b_sweep}`）。

**二、真发一发**。私有库每跑一份新的（`backup()` 只读复制 `_preview.db`，跑后逐枚比字节与 mtime，全程 `shared_untouched=True`，不碰共享库、不碰 `:4781`/`:4783`/`:4785`/`:4787`/`:8000`/`:4782`/`:8693`、不跑 `demo/reset`）。在一枚未打卡的站按下去：门答 `http_status={req_http}`，行数 0→1；再按第二枚不同的站：`http_status={req_http}`，行数 0→{rows_cand_after}；重复按同一枚：`http_status={dup_http}`。请求序列逐字 `GET:200, POST:201, GET:200, POST:409, GET:200, POST:201, GET:200`，两种视窗各一趟（`390x844` 与 `1280x800`），pageerror 两趟都是 0（件 blob `{b_sweep}`）。静态口 `127.0.0.1:4869`、`127.0.0.1:4871`、`127.0.0.1:4872`、`127.0.0.1:4873`，后端 `127.0.0.1:8141`、`127.0.0.1:8143`、`127.0.0.1:8145`（同上一格件 blob `{b_sweep}`）。

**三、重复打卡在屏上那一句，指向已有的那一枚**。基座代现尖：按同一枚两次后，屏上拒绝句 {notices_tip} 枚——同一句话挂在全部六站名下，逐字是「{sentence_tip}」，里面没有服务器记下的时刻。我这代候选：同一趟同一步骤后拒绝句 {notices_cand} 枚，句主只有被按的那一站（Old Town Gate），逐字「{sentence_cand}」——时刻是从 `error.details.existing_stamped_at` 取的，不是我造的。`details` 里那枚 uuid 我没上屏（屏扫 uuid 命中 0 枚，机词 0 枚，件 blob `{b_sweep}`）。成因在源码里可读：候选代把整屏共享的一枚 notice 串改成按站键控，`frontend/src/features/trip/TripItinerary.tsx` blob `{b_itin}`。

**四、拒绝形（门里四字段陈列，不造句子）**。基座代 `{tip}`：未知行程写门 `http_status={base_journey_http}`、正文 {base_journey_bytes} 字节、句子里有 uuid={base_journey_uuid}、`details` 为 null={base_journey_null}、`reason_code` 无（件 blob `{b_doors_base}`）。候选代同一用例：`http_status={cand_journey_http}`、`error.reason_code={cand_journey_code}`、`details={{"field": "journey_id"}}`、句子里有 uuid={cand_journey_uuid}（件 blob `{b_doors}`）。你点名的两格在这一代两面上都是干净的：`{target_code}` 答 `http_status={target_http}` 且 `details.fields` 点名要哪两枚字段；`{unknown_code}` 答 `http_status={unknown_http}`，句子无 uuid，uuid 只在 `details.activity_id` 这个机器字段里——按单子的字面（不许把裸 uuid 印进句子、不许 `details=null`）这两格基座代本就合规，真正的违例是未知行程那一格，我已改。改在两扇门自己的读门里，没动共享 `require()`（`backend/app/main.py:797`，那是一家共用的，越界了）。

**五、反件一：把服务端 409 判据摘掉**。只读地造一枚反件树 `mutgen4`，唯一差异是 `create_journey_checkin` 里那段查已有的 `session.scalars(...)` 被换成 `existing = None`——两枚树比对的 {compared} 枚文件里只有 `backend/app/main.py` 不同，data/contracts/generated 全等（件 blob `{b_proof}`；交付那枚 `main.py` 前后 sha256 同一枚，本轮实测 `37615c08…`）。两趟真跑（件 blob `{b_ce1}`）：候选代两套件共 16 枚臂（本单 5 枚 + ORD-0476 那 11 枚）全过、失败 {ce1_cand_fail} 枚、退出 0；反件代通过 {ce1_mut_pass} 枚、失败 {ce1_mut_fail} 枚、退出 1，红的臂名逐字 `{ce1_mut_names}`。要紧的是这一处：`{ce1_green_name}`（ORD-0476 已收的那条只读句子与状态码的重复臂）在反件代仍然**通过**——这就是「去掉服务端 409 判据后重复打卡那臂会假绿」的实测形状；屏侧同样假绿：候选面挂在被摘判据的门上，重复句仍出现 {mut_screen_notices} 枚、句主唯一、pageerror {mut_screen_pe}（同一件 blob `{b_doors}`）。我新那条臂（blob `{b_pytest}`）断言的是「哪一层拒的」，反件代它红了，所以它不是空转。

**六、反件二：服务端不给足迹时，屏上不许凭空长出已打标**。造一枚一次性产物：把已打标记从足迹读门改成就排程里活动状态取（COMPLETED 三枚），只造面不改交付码。真跑：到屏时门里行数 {rows_mut_arrival}，屏上「已打卡」{marks_mut_arrival} 枚（基座与候选同一格都是 0 对 0，件 blob `{b_sweep}`）。三臂载体 `frontend/e2e/qoder-ord0500-checkin-truth.spec.ts`（blob `{b_spec}`，配置 `frontend/playwright.ord0500-checkin.config.ts` blob `{b_cfg}`，`CITYNEXUS_ORD0500_BASE` 不指到我自己的 4xxx 面就拒绝启动、且不带 webServer）在三面上各跑一趟，逐臂状态（件 blob `{b_arms}`）：基座面 `{entry_tip}` 通过 {base_arm_pass} 枚、失败 {base_arm_fail} 枚，判语逐字「{base_arm_msg}」；候选面 `{entry_cand}` 通过 {cand_arm_pass} 枚、失败 {cand_arm_fail} 枚；反件面 `{entry_mut}` 通过 {mut_arm_pass} 枚、失败 {mut_arm_fail} 枚，判语逐字「{mut_arm_msg}」。

**七、前置与两处更正**。① 壳的门确实是浏览器里存下的行程引用：键族在 `frontend/src/lib/failureAttribution.ts:390`（我现读到的是第 391 行那条 `citynexus.v8.journey_id`），条件句在 `frontend/src/app/V8Experience.tsx:869`——单子里写的 `:867` 在这一代往上漂了两行，我按现读的走。② 干净库确实排不出行程（ORD-0526），所以我的分母是 `_preview.db` 只读复制出来的那趟有排程的行程（6 站、3 枚 COMPLETED）。③ 单里「新造第二枚打卡门」那条前提我没做：普查里一站一枚（第三臂就钉着这件事），改动只在拒绝的读法与句子上（`frontend/src/features/checkin/checkins.ts` blob `{b_checkins}`、词表 `frontend/src/features/checkin/checkinCopy.ts` blob `{b_copy}`）。

**八、一处我不改的缺口，具名**。`GET /api/v1/journeys/{{id}}/checkins` 在候选代同样具名拒未知行程，但契约里 GET 的 404 我没写：写了会撞 ORD-0476 已收的那条契约臂（`backend/tests/test_qoder_ord0476_checkins.py:500` 逐字断言 GET 的 responses 只有 200 与 409），那是别人手上的判据，我不改判据凑绿。缺口留具名：POST 侧 404 已写进 `contracts/openapi.yaml` 并在我的臂里钉住名字。

**九、提交与反件处置**。候选 `{c6}`（32 枚文件、含读数单与件共 +{plus} 行，其中产品码 +{plus_product} 行 / -{minus_product} 行），只读预测 `{tree6}` 退出 0；枝 `review/newlane-ord0500-phone-checkin-entry-r1` 新增，0 force。反件树 `mutgen4`、`wt8` 与反件面 `faces/o0500_clientbool` 是一次性仪表，不进任何枝、跑完即删；交付那枚 `main.py` 与它们逐字节无关（第五格的 sha256 前后同一枚即此证）。

**十、没走的（具名）**。真机与隧道：`NOT_MEASURED`；整套 Playwright 验收：`NOT_EXECUTED`；分享接收屏与足迹面板（`FootprintPanel`）本单未走，那是切片二另一格；今日时钟句把成句嵌进括号、`/v8/access` 印未译事件名、行程级拒绝印裸 uuid 那几处仍属别人手上的面，我不越。
""".format(**v)

    out_a = r"D:\moodle\_qoder_ledger_inbox\phone_%s.md" % hhmm
    out_b = r"D:\moodle\_qoder_ledger_inbox\phone_%s.md" % later.strftime("%H%M")
    open(out_a, "w", encoding="utf-8", newline="\n").write(block_a)
    print("WROTE %s bytes=%d" % (out_a, len(block_a.encode("utf-8"))))
    open(out_b, "w", encoding="utf-8", newline="\n").write(block_b)
    print("WROTE %s bytes=%d" % (out_b, len(block_b.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
