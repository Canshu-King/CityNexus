"""Emit the two blocks for generation 822db3d9 from the slots file.

Slot values come from `gen5_slots_r1.py` (which reads them out of the artifacts and out of git), so
this file holds prose and the sentence shapes only.  Lines carrying a three-digit-or-more number also
carry their coordinate, because the ledger gate reads line by line.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"

BLOCK_0500 = """### ORD-0500 · 手机打卡门 r2：rebase 到现尖 822db3d9，分母三代、真发一发与两枚反件（车道 phone，{t1}）

**零、为什么有 r2，以及那枚文件是谁**。落地序列器对 `{f_0500_r1}` 报 RECUT_ABORT，工具输出截断没点名，我自己逐枚比出来的就是这一枚：`backend/app/main.py`——我在 `{gen1}` 上那代它是 blob `{main_mine_r1}`，现尖 `{tip}` 上是 blob `{main_tip}`（ORD-0511 的两笔在 18:03 与 00:18 动过它），只读预测的合并结果是 blob `{main_merged}`，三枚互不相等，所以「合不到你自己那代字节上」。其余四枚产品文件在现尖逐字节未动，r2 里它们与 r1 同一枚 blob：`frontend/src/features/trip/TripItinerary.tsx` `{b_itin}`、`frontend/src/features/checkin/checkins.ts` `{b_checkins}`、`contracts/openapi.yaml` 与 `frontend/src/features/checkin/footprint.css` 见件单 `{b_sheet}`。r1 那两枚提交 `{f_0500_r1}` 冻结不动，r2 另投新枝 `review/newlane-ord0500-phone-checkin-entry-r2` = `{cand}`，基座 = 现读 `{tip}`（`git ls-remote` 自读，落笔前落笔后各一次同一枚），只读预测 `{tree_cand}` 退出 0。

**一、分母三代都在，不折算**。① `{pre}`（切片二 UI 落地前）：同一趟有排程的行程 6 站、`stop-checkin` 控件 {ctrls_pre} 枚——无入口、无可按（件 `{b_pre}`）。② `{gen1}`：6 站、控件 {ctrls_gen1} 枚、中心命中可按 {press_gen1} 枚。③ 本代 `{tip}`：站数 {stops_tip} 枚、控件 {ctrls_tip} 枚、中心命中可按 {press_tip} 枚，盒 {boxes_tip}（未打卡 44x44、已打卡 54x44，与你 23:31 量到的一致），桌面 1280x800 那趟同样 {desk_press} 枚可按（件 `{b_sweep}`）。我原句「手机上打不到卡」只对 ① 成立，②③ 上它不成立，这一格按 Q24 逐代各贴自己的读数。

**二、真发一发（本代）**。私有库每跑一份新（`backup()` 只读复制 `_preview.db`，跑后逐枚比字节与 mtime，本代 5 跑全 `shared_untouched=True`；`:8000`/`:4781`/`:4782`/`:4783`/`:4785`/`:4787`/`:8693` 一枚没碰，`demo/reset` 没跑）。在未打卡那站按下去：门答 `http_status={req_http}`，行数 0→1；再按另一枚不同的站：`http_status={req_http}`，行数 0→{rows_cand}；同一枚再按一次：`http_status={dup_http}`。请求序列逐字 {reqs_tip}，pageerror {pe_tip}（件 `{b_sweep}`，静态与后端端口 `127.0.0.1:4869`/`:4871`/`:4872`/`:4873`、`127.0.0.1:8141`/`:8143`/`:8145` 归我，跑完已交还）。

**三、重复打卡那句现在指向已有那一枚**。本代基座面：同一枚按两次后屏上拒绝句 {notices_tip} 枚——一句话挂在全部站名下，逐字「{sentence_tip}」，里面没有服务器记的时刻；桌面那趟同样 {desk_notices} 枚。我这代候选：拒绝句 {notices_cand} 枚，句主只有被按的那一站 {owners_cand}，逐字「{sentence_cand}」——时刻取自 `error.details.existing_stamped_at`；屏上 uuid 扫 0 枚、机词 0 枚（件 `{b_sweep}`）。成因两处可读：`frontend/src/features/trip/TripItinerary.tsx` `{b_itin}`（共享串改按站键控）与 `frontend/src/features/checkin/checkins.ts` `{b_checkins}`（原来把 details 丢了、`status` 写死 0），词表 `frontend/src/features/checkin/checkinCopy.ts` `{b_copy}`。

**四、拒绝形（门里四字段陈列，不造句子）**。本代基座 `{tip}`：未知行程写门 `http_status={base_http}`、正文 {base_bytes} 字节、句子里有 uuid={base_uuid}、`details` 为 null={base_null}、无 reason_code。候选 `{cand}`：`http_status={cand_http}`、`error.reason_code={cand_code}`、`details={{"field": "journey_id"}}`、句子里有 uuid={cand_uuid}、`details` 为 null={cand_null}（件 `{b_doors}`）。你点名的两格本代基座就合规：`{target_code}` 答 `http_status={target_http}` 且 `details.fields` 点名要哪两枚字段；`{unknown_code}` 答 `http_status={unknown_http}`，uuid 只在 `details.activity_id` 这个机器字段里，句子没有。真正的违例是未知行程那一格，改在两扇门自己的读门里，共享 `require()`（`backend/app/main.py:797`）我没动。

**五、反件一：摘掉服务端 409 判据**。一次性反件树 `mutgen5` 只把 `create_journey_checkin` 里那段查已有的 `session.scalars(...)` 换成 `existing = None`；与交付树比对的 {compared} 枚文件里只有 `backend/app/main.py` 不同（`{cand_sha}…` 对 `{mut_sha}…`，本机字节 sha256，不是 git 物件，不可 cat-file；件 `{b_proof}`）。两趟真跑（件 `{b_ce1}`）：候选代两套件共 {ce1_cand_pass} 枚臂全过、失败 {ce1_cand_fail} 枚、退出 0；反件代通过 {ce1_mut_pass} 枚、失败 {ce1_mut_fail} 枚、退出 1，红的臂名逐字 `{ce1_mut_names}`。假绿在这一枚：`{ce1_green_name}`（ORD-0476 已收的、只读状态码与句子的重复臂）在反件代仍然通过；屏侧同样假绿——候选面挂在摘了判据的门上，重复句仍出现 {mut_screen_notices} 枚、pageerror {mut_screen_pe}（同一件 `{b_doors}`）。我那条钉层次的臂（`{b_pytest}`）在反件代红了，所以它不是空转。

**六、反件二：门里不给足迹时屏上不许长出标**。一次性面 `{entry_mut}` 把已打卡改成从排程状态取（COMPLETED 三枚）。真跑：到屏时门里行数 {rows_mut_arrival} 枚、屏上「已打卡」{marks_mut_arrival} 枚（本代基座与候选同一格都是 0 对 0，件 `{b_sweep}`）。三臂载体 `{b_spec}`（配置 `{b_cfg}`：`CITYNEXUS_ORD0500_BASE` 不指到我自己的 4xxx 面就拒绝启动，无 webServer）在三面上各跑一趟，逐臂状态（件 `{b_arms}`）：基座面 `{entry_tip}` 通过 {base_arm_pass} 枚、失败 {base_arm_fail} 枚，判语逐字「{base_arm_msg}」；候选面 `{entry_cand}` 通过 {cand_arm_pass} 枚、失败 {cand_arm_fail} 枚；反件面 `{entry_mut}` 通过 {mut_arm_pass} 枚、失败 {mut_arm_fail} 枚，判语逐字「{mut_arm_msg}」。

**七、前置与两处更正**。① 壳的门是浏览器存下的行程引用：`frontend/src/lib/failureAttribution.ts:390` 那一族（现读到第 391 行是 `citynexus.v8.journey_id`），条件句 `frontend/src/app/V8Experience.tsx:869`——单里的 `:867` 在本代漂了两行，我按现读的走。② 干净库排不出行程（ORD-0526），分母来自 `_preview.db` 只读复制的那趟有排程行程（6 站、3 枚 COMPLETED）。③ 一站一枚钉在第三臂里（{b_arms}），我没有新造第二枚打卡控件。

**八、我不改的那一处，仍具名**。GET 那扇读本代同样具名拒未知行程，但契约里 GET 的 404 我没写——写了会撞 ORD-0476 已收的契约臂（`backend/tests/test_qoder_ord0476_checkins.py:500` 逐字断言 GET 只有 200 与 409），那是别人的判据，我不改判据凑绿。POST 侧 404 已写进 `contracts/openapi.yaml` 并由我的臂钉住名字。

**九、提交、代次与反件处置**。候选 `{cand}`（产品码+载体 9 枚文件，读数单与件随交；行数以 `git diff {tip} HEAD` 现算，见件单 `{b_sheet}`），只读预测 `{tree_cand}` 退出 0；`{f_0500_r1}` 冻结、0 force。本代产物身份两证：基座面入口 `{entry_tip}`、候选面入口 `{entry_cand}`、反件面入口 `{entry_mut}`，服务字节与磁盘字节逐枚相等；打包入口本机字节 sha256 基座 `{sha_tip}…`、候选 `{sha_cand}…`（前缀截短，全值与字节数在件 `{b_builds}` 里，本机字节 sha256，不是 git 物件，不可 cat-file）。交付那枚 `backend/app/main.py` 的 blob 是 `{b_main}`，可 `git cat-file -t`。第三证（访问日志）具名 `NOT_AVAILABLE_BY_CMDR`：`vite preview` 不往我控制的日志写请求行。反件树 `wt10`/`mutgen5` 与反件面是一次性仪表，不进任何枝，重建配方写在 `review/ord0500-checkin/tools/CE2_MUTANT_RECIPE_r1.md`。

**十、没走的（具名）**。真机与隧道：`NOT_MEASURED`；整套 Playwright 验收：`NOT_EXECUTED`；足迹面板 `FootprintPanel` 与分享接收屏本单未走；今日时钟句嵌套、`/v8/access` 印未译事件名那几处属别人手上的面，我不越。
"""

BLOCK_0485 = """### ORD-0485 · 手机端走查 r4：字典四词条跟着现尖重落一遍，读数与 ORD-0500 同代（车道 phone，{t1}）

**一、先答 recut**。`{f_r3}` 这一枚不需要重切：`{gen1}` 到 `{tip}` 之间 `frontend/src/i18n/LocaleContext.tsx` 一枚未动（现尖 blob `{dict_tip_blob}`，与我那代的基座同一枚），所以只读预测里我的候选 blob `{b_dict}` 原样落在 `{tip}` 的树上——三枚 `{f_r1}` `{f_r2}` `{f_r3}` 全部冻结、0 force。但你要求 ORD-0485 一并交，而 Q24 不许把 `{gen1}` 那代的读数当成本代读数，所以我另投 `review/newlane-ord0485-phone-walkthrough-r4` = `{dic}`：同样 4 行新增、0 行删除，落点行与上一代逐字相同（键名落位 55/665/1149/1718），只读预测 `{tree_dic}` 退出 0。

**二、本代产物身份**。静态口 `127.0.0.1:4874`（基座 `{tip}` 的产物，入口资产 `{entry_tip}`）与 `127.0.0.1:4875`（候选 `{dic}` 的产物，入口 `{entry_dict}`）；两证：入口名取自该服务器自己答的 `index.html`，服务字节与磁盘字节逐枚相等（件 `{b_builds}`，本机字节 sha256，不是 git 物件，不可 cat-file）。第三证具名 `NOT_AVAILABLE_BY_CMDR`：`vite preview` 不往我这一层控制的日志里写请求行。

**三、词汇清点在本代两枚各一件**。基座：en {gap_tip_en} 枚、zhCN {gap_tip_zh} 枚、引用 {gap_tip_ref} 枚、两表都缺 {gap_tip_missing} 枚（件 `{b_gap_tip}`）；候选 r4：en {gap_r4_en} 枚、zhCN {gap_r4_zh} 枚、两表都缺 {gap_r4_missing} 枚（件 `{b_gap_r4}`）。两本字典字节不同：{dicts_differ}，件 `{b_walk}`——两代各写一件、不会互相吃掉，这是我自己上一处证据缺陷的修法，继续生效。

**四、走查与词汇臂都在本代重跑**。`390x844` 触摸档：基座 {screens_tip} 面、候选 {screens_r4} 面，pageerror {pe_walk_tip} 与 {pe_walk_r4}（件 `{b_walk}`）。已收的那支词汇臂原样不动、只换面：基座面 {car_tip_verdict}，红臂 {car_tip_reds}，判语逐字「{car_tip_msg}」；候选面 {car_r4_verdict}，退出 {car_r4_exit}。

**五、本单的写集只有那 4 行**（`frontend/src/i18n/LocaleContext.tsx` blob `{b_dict}`），其余是读数单 `{b_sheet4}`、两件 gap 与 `tools/` 里那几把尺。上一单六屏族里本代到屏的是这 {screens_tip} 面（hub、行程与「预订」子页、抽屉条目、住宿、可达、导入、足迹、回收站），`NOT_REACHED` 一格没有；分享接收屏那格本代仍具名 `NOT_RETAKEN_THIS_GENERATION`（它上一代是真 POST 一枚授权 + live/revoked/unknown 三形各有服务端回读，要在新代复现说一声即可）。

**六、没走的（具名）**。真机与隧道 `NOT_MEASURED`；整套 Playwright 验收 `NOT_EXECUTED`；封存演示的「接受调整」仍走不到（受保护锚点覆盖全部活动，属 ORD-0369 已有判定）。
"""


def main():
    slots = json.load(open(os.path.join(LANE, "run", "gen5_block_slots_r1.json"), encoding="utf-8"))
    walk = json.load(open(os.path.join(LANE, "evidence", "gen5_walk_r1.json"), encoding="utf-8"))
    faces = {f["label"]: f for f in walk.get("faces", [])}

    def carrier_text(label):
        c = faces.get(label, {}).get("carrier", {})
        reds = c.get("red_test_names") or []
        msg = ""
        for line in (c.get("notes") or []):
            if "spec.ts ::" in str(line):
                msg = str(line).strip()
                break
        return {"verdict": str(c.get("verdict_line") or "NOT_MEASURED"),
                "reds": ", ".join(str(x) for x in reds) or "无",
                "msg": msg, "exit": c.get("exit")}

    slots.update({"car_tip_" + k: v for k, v in carrier_text("TIP_822db3d9").items()})
    slots.update({"car_r4_" + k: v for k, v in carrier_text("O0485_R4").items()})
    now = datetime.now().astimezone()
    slots["t1"] = now.strftime("%H:%M")
    later = now.replace(minute=(now.minute + 1) % 60)
    path_a = r"D:\moodle\_qoder_ledger_inbox\0afdb49b_%s.md" % now.strftime("%H%M")
    path_b = r"D:\moodle\_qoder_ledger_inbox\0afdb49b_%s.md" % later.strftime("%H%M")
    slots["t1_block_b"] = later.strftime("%H:%M")

    a = BLOCK_0500.format(**slots)
    open(path_a, "w", encoding="utf-8", newline="\n").write(a)
    print("WROTE %s bytes=%d" % (path_a, len(a.encode("utf-8"))))
    b = BLOCK_0485.format(**dict(slots, t1=later.strftime("%H:%M")))
    open(path_b, "w", encoding="utf-8", newline="\n").write(b)
    print("WROTE %s bytes=%d" % (path_b, len(b.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
