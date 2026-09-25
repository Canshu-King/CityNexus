"""The ledger block and the bus post for ORD-0323, built from the receipt's own cells.

Lanes do not write the ledger (Q63=③ / LEDGER_SINGLE_WRITER_V1): the block lands in
`D:\\moodle\\_qoder_ledger_inbox\\b-c01d72a3_<HHMM>.md` with its first line starting `### `, and the commander's
`ledger_inbox_apply_r1.py` inserts it. Q43 grades the prose before it is written anywhere, and every 40-hex
in it is resolved against the remote refs with `git cat-file -t` in the same run.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request


def blob_line(D, name):
    for row in D.PUBLISHED:
        if row["path"].endswith("/" + name):
            return row["blob"], row["bytes"]
    raise SystemExit("nothing published under " + name)


def _pf(body, name):
    """A file's r4 lines, looked up by name: three files are scanned, so a positional index moves."""
    return next(x for x in body["per_file_lines"] if x["file"] == name)


def build_block(D, receipt, idx):
    REA, SH = D.REA, D.SH
    f1, b1 = REA["fixed"]["N1"], REA["cell1_baseline_sink"]["N1"]
    f2, f3 = REA["fixed"]["N2"], REA["fixed"]["N3"]
    b2, b3 = REA["cell2_baseline_throw"]["N2"], REA["cell2_baseline_throw"]["N3"]
    l2 = REA["cell2_baseline_throw"]["N2"]
    d2 = REA["cell2_fields_blind"]["N2"]
    R3, R4 = D.R3, D.R4
    MATRIX_NAME = D.MATRIX_NAME
    mx_blob, mx_bytes = blob_line(D, D.MATRIX_NAME)
    r3_blob, _ = blob_line(D, "ord0323_r3_readings_r2.json")
    r4_blob, _ = blob_line(D, "ord0323_r4_readings_r2.json")
    rc_blob, rc_bytes = blob_line(D, "ord0323_receipt_r3.json")
    r1_receipt_blob, r1_bytes = blob_line(D, "ord0323_receipt_r1.json")
    ix_blob, ix_bytes = blob_line(D, "ord0323_index_r3.json")
    run_blob, _ = blob_line(D, "playwright_report__r2_fixed.json")
    base_arm_blob, _ = blob_line(D, "arm__r2_cell1_baseline_sink__N1.json")
    cand_n1_blob, _ = blob_line(D, "arm__r2_fixed__N1.json")
    base_c2_blob, _ = blob_line(D, "arm__r2_cell2_baseline_throw__N2.json")
    cand_n2_blob, _ = blob_line(D, "arm__r2_fixed__N2.json")
    cand_n3_blob, _ = blob_line(D, "arm__r2_fixed__N3.json")
    blind_n2_blob, _ = blob_line(D, "arm__r2_cell2_fields_blind__N2.json")
    instrument_blob, _ = blob_line(D, "ord0323_run_arms.py")
    r3_tool_blob, _ = blob_line(D, "ord0323_r3_readings.py")
    r4_tool_blob, _ = blob_line(D, "ord0323_r4_readings_r2.py")
    A = D.ADJ
    arm_files = sum(1 for r in D.PUBLISHED if "/arm__" in r["path"])
    reports = sum(1 for r in D.PUBLISHED if "/playwright_report__" in r["path"])
    lines = []
    add = lines.append
    add(f"### SESSION=c01d72a3 · ORD-0323 交付 · 车道 B（候选 {D.CAND}，基线 {D.BASE}）")
    add("")
    add(f"**要件对照** ①基线按你点名的那一枚现读 {D.BASE}，我的候选 {D.CAND} 在它之上 {D.COMMITS} 枚提交，"
        f"分支只开新名 `{D.BRANCH}`；②每格两向断言见下（两向各配一枚反件，可各自变红）；"
        f"③尺量我自己那一枚：r3（blob {R3['ruler']['local_git_blob_hash']}，与你贴的逐位相同，"
        f"自检 {R3['ruler']['selftest']}）改前 {R3['before']['hit_count']} 命中、改后 "
        f"{R3['after']['hit_count']} 命中，读数组件 {r3_blob}；同一格再用取代它的 r4（blob "
        f"{R4['ruler']['local_git_hash_object']}，自检 {R4['ruler']['selftest_verdict']} "
        f"{R4['ruler']['selftest_assertions_met']}）量了一遍，读数组件 {r4_blob}；"
        f"④0 处 skip、0 条既有断言被改（{D.SPEC} 的 spec blob {D.SPEC_CAND_BLOB}，"
        f"skip/fixme 命中 {len(D.SKIP_HITS)} 行）；⑤权威线 0 次移动、0 次 force-push。")
    add("")
    add(f"**一、格一 `frontend/src/components/ProductErrorBoundary.tsx:104-105` 已闭。**"
        f"改前那一折把接来的两样东西一起印出来：异常正文与 React 组件帧。把尖上那份文件放回工作树跑同一枚 N1，"
        f"屏幕实际量到 {json.dumps(b1['leaked_needles_still_on_screen'], ensure_ascii=False)} 两枚指针在场，"
        f"帧里带 http:// 开头的源文件路径与行列号（原文读数在 arm__r2_cell1_baseline_sink__N1.json blob {base_arm_blob}）。"
        f"本候选 N1 {SH['fixed']['per_arm']['N1']}，折子里只剩这台设备自己量的五项 "
        f"`{f1['error_detail_text']}`，命中 {json.dumps(f1['leaked_needles_still_on_screen'], ensure_ascii=False)}；"
        f"同一趟 console 的错误级输出计数记在臂自己的读数件 arm__r2_fixed__N1.json blob {cand_n1_blob} 的 "
        f"`console_error_count` 字段（失败原文与组件帧仍在开发者的通道里，不在屏幕上），"
        f"页面外挂元素 {json.dumps(f1['overlay_hosts'], ensure_ascii=False)} —— 没有覆盖层替我把原文再印一遍。"
        f"反件两枚各自只咬一向：只把原文放回去（字段仍全）N1 {SH['cell1_leak_beside_fields']['per_arm']['N1']}、"
        f"命中 {json.dumps(REA['cell1_leak_beside_fields']['N1']['leaked_needles_still_on_screen'], ensure_ascii=False)}；"
        f"只拆字段（原文仍不在）N1 {SH['cell1_fields_gone']['per_arm']['N1']}、命中 "
        f"{json.dumps(REA['cell1_fields_gone']['N1']['leaked_needles_still_on_screen'], ensure_ascii=False)}。"
        f"r4 在这一枚文件上从 2 形到 0 形，r3 从 1 命中到 0 命中。")
    add("")
    add(f"**二、格二 `frontend/src/features/inbox/JourneyInboxWorkbench.tsx:88`：源头闭了，三个出屏口还开着。**"
        f"改前 :88 把回复里的句子重铸成这条腿自己的话，再由 687/691/731 三处印出来 —— "
        f"把尖上那份文件放回工作树，N2 {SH['cell2_baseline_throw']['per_arm']['N2']}、屏幕量到 "
        f"{json.dumps(b2['leaked_needles_still_on_screen'], ensure_ascii=False)}，N3 屏幕量到 "
        f"{json.dumps(b3['leaked_needles_still_on_screen'], ensure_ascii=False)}，"
        f"三处都被这枚反件证实确实在用（件 arm__r2_cell2_baseline_throw__N2.json blob {base_c2_blob}）。"
        f"本候选 N2/N3 都 {SH['fixed']['per_arm']['N2']}：状态行读 `{f2['message_text']}`、待审行读 "
        f"`{f2['pending_text']}`、确认折读 `{f3['fold_text']}`，三处命中 "
        f"{json.dumps(f2['leaked_needles_still_on_screen'], ensure_ascii=False)}（读数件 "
        f"arm__r2_fixed__N2.json blob {cand_n2_blob} 与 arm__r2_fixed__N3.json blob {cand_n3_blob}）；"
        f"两向各一枚反件，只拆字段（原话仍不在屏上）这一枚：N2/N3 {SH['cell2_fields_blind']['per_arm']['N2']}/"
        f"{SH['cell2_fields_blind']['per_arm']['N3']}、命中 "
        f"{json.dumps(d2['leaked_needles_still_on_screen'], ensure_ascii=False)}（件 blob {blind_n2_blob}）。"
        f"这一格按你 03:43 的扩单做到 D 数出的九格（T05-T13；她件 {D.TRIAGE_BLOB} 的 rows，锚点行 "
        + json.dumps(D.TRIAGE_CELLS, ensure_ascii=False) + "）。八个 catch 站点全部收敛到产品**已有**的那条通道 "
        f"`frontend/src/lib/failureAttribution.ts`（classifyReadFailure 在 :"
        + str(D.CHANNEL["exports_helpers"][0]) + "，句子由 copyFor 查表），没有一个站点再把异常正文写进渲染态；"
        "机器位只放这台设备量到的 http_status / content_type / evidence kind。八条腿各一枚独立臂（第一趟八腿共用"
        "一枚臂时，一条卡住的腿吃掉整枚臂的超时，只留下 running_leg=T09 这样的线索），每腿两问：自己那句原话不在"
        f" DOM 里、自己那次 HTTP 状态在自己那个位上。逐臂读数（{MATRIX_NAME} 的 per_arm_readings.fixed）："
        "缺自己状态的腿 "
        + json.dumps([c for c in D.LEG_KEYS if not D.REA["fixed"][c]["status_in_slot"]], ensure_ascii=False)
        + "、屏幕找到原话的腿 "
        + json.dumps([c for c in D.LEG_KEYS if D.REA["fixed"][c]["needles_found"]], ensure_ascii=False)
        + "、把别腿状态顶上的腿 "
        + json.dumps([c for c in D.LEG_KEYS if D.REA["fixed"][c]["foreign_status_found"]], ensure_ascii=False)
        + "。归因单独一枚反件：把所有机器位钉成 503，问 503 的那条腿照过、其余立刻红（"
        + json.dumps([c for c in D.LEG_KEYS if D.REA["cell2_status_frozen"][c]["foreign_status_found"]],
                     ensure_ascii=False)
        + "）。Q68 那一格另是一形：`frontend/src/features/planning/PlanWithAiSheet.tsx:155` 在服务器没给编号时把 "
        "`detail` 截断大写塞进「服务器回的原因编号是 …」。两臂各判一半：给了真编号仍显示编号 "
        + str(bool(D.REA["fixed"]["Q68a"]["code_in_card"])) + "；只给句子时编号位上没有句子 "
        + str(not D.REA["fixed"]["Q68b"]["uppercased_prose_in_code_slot"]) + "，而句子仍在带归因标签的技术详情里 "
        + str(bool(D.REA["fixed"]["Q68b"]["attributed_sentence_in_fold"])) + "/"
        + str(bool(D.REA["fixed"]["Q68b"]["server_label_present"])) + "；反件只把那行退回放回去：Q68a "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68a"]) + " 仍绿、Q68b "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68b"]) + " 变红 —— 修的是「句子不许冒充编号」，不是「清空那格」。"
        "逐尺两代读数（各自现量，不互相折算）：r3 改前 " + str(R3["before"]["hit_count"]) + " 形 → 改后 "
        + str(R3["after"]["hit_count"]) + " 形，r4 改前 " + str(R4["before"]["hit_count"]) + " 形 → 改后 "
        + str(R4["after"]["hit_count"]) + " 形。**勘误一条我自己上一稿的话**：这两串数不是 0——改后仍报的那 "
        + str(len(R4["remaining"])) + " 形，具名 " + json.dumps(R4["remaining"], ensure_ascii=False)
        + "，都在这条按 Q67=① "
        "合法显示服务器原话的链上（行号从 " + json.dumps(_pf(R4, "PlanWithAiSheet.tsx")["lines_before"], ensure_ascii=False)
        + " 位移到 " + json.dumps(_pf(R4, "PlanWithAiSheet.tsx")["lines_after"], ensure_ascii=False)
        + "，差 " + str(_pf(R4, "PlanWithAiSheet.tsx")["shift_if_same_count"]) + " 行是我在同文件上方增删的行）。"
        "本单点名的出口才是清零的那部分：" + json.dumps(
            {"JourneyInboxWorkbench.tsx": _pf(R4, "JourneyInboxWorkbench.tsx")["lines_before"],
             "ProductErrorBoundary.tsx": _pf(R4, "ProductErrorBoundary.tsx")["lines_before"],
             "at_candidate": _pf(R4, "JourneyInboxWorkbench.tsx")["lines_after"]}, ensure_ascii=False)
        + " 这些行在改后全部为空。")
    add("")
    add(f"**三、这一格用户不点也会撞上。**同一文件挂载即发两条读："
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{D.REACH['mount_effects_at_candidate'][0]}` 与 "
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{D.REACH['mount_effects_at_candidate'][1]}`"
        f"（在尖上分别是 :{D.REACH['mount_effects_at_base'][0]} 与 :{D.REACH['mount_effects_at_base'][1]}）；"
        f"`backend/app/main.py:{D.REQ_ID['main_py_at_base']['require_404_line'][0]}` 的 "
        f"`{D.REQ_ID['main_py_at_base']['require_404_text'][0]}` 是六个 inbox handler 开头都会抛的 404。"
        f"我的 N2 那一趟一次点击都没有：两条 GET 被回答成 HTTP 500 与 HTTP 503，改前的屏幕上就是服务器那句原文。")
    add("")
    add(f"**四、量具与读数（全部可复跑）。**矩阵件 {MATRIX_NAME} blob {mx_blob} "
        f"（{len(SH)} 个形状 × {len(D.ARM_KEYS)} 枚臂 = {len(SH) * len(D.ARM_KEYS)} 份逐臂读数，"
        f"臂名按矩阵自己列的来：{json.dumps(sorted(SH['fixed']['per_arm']), ensure_ascii=False)}，"
        f"逐臂状态与 Playwright 报告一致，判定 {D.MATRIX['verdict']}）；"
        f"臂自己写的读数件 {arm_files} 枚、Playwright 报告 {reports} 枚，全列在清单 ord0323_index_r3.json blob "
        f"{ix_blob}（{idx['file_count']} 条目 / {idx['total_bytes']} 字节；清单不收自己这一条，列的是它上架之前"
        f"已落的全部，含收据 r2）；"
        f"**自我更正一条**：收据 r1（blob {r1_receipt_blob}，{r1_bytes} 字节，原样留在架上）里有五枚 "
        f"blob id 是我拿 "
        f"`git show` 的输出自己再算 sha1 得来的，而那段输出被我去掉了文件末尾的换行 —— 那五枚数算的是截断后的字节，"
        f"在任何仓库都解不出来；r2 一律改用 git 自己的 blob id（rev-parse），was/now 五对逐条记在 "
        f"ord0323_receipt_r3.json 的 erratum_from_r1 里，r1 那件一字不改原地留着。"
        f"收据 ord0323_receipt_r3.json blob {rc_blob}（{rc_bytes} 字节，Q38 判该件的每格 why 只引自己 "
        f"readings 里的值，绿灯才落这件），驱动器 ord0323_run_arms.py blob {instrument_blob}、"
        f"r3 读数件生成器 ord0323_r3_readings.py 生成器 blob {r3_tool_blob}（r3 尺本身 "
        f"{R3['ruler']['local_git_blob_hash']}）、r4 生成器 ord0323_r4_readings_r2.py blob {r4_tool_blob}"
        f"（r4 尺本身 {R4['ruler']['local_git_hash_object']}）。"
        f"血缘往下两把也各自量过同一对代次：r5 读数件 ord0323_r5_readings_r1.json blob "
        f"{blob_line(D, 'ord0323_r5_readings_r1.json')[0]}（尺 {D.R5['ruler']['local_git_hash_object']}，"
        f"全树 {D.R5['tree_wide']['before_hits']} → {D.R5['tree_wide']['after_hits']}），"
        f"r6 读数件 ord0323_r6_readings_r1.json blob {blob_line(D, 'ord0323_r6_readings_r1.json')[0]}"
        f"（现行尺 {D.R6['ruler']['local_git_hash_object']}，你 commit {D.R6['ruler']['added_by_commit']} 上那枚 "
        f"{D.R6['ruler']['published_path']} 逐位相同；全树 {D.R6['tree_wide']['before_hits']} → "
        f"{D.R6['tree_wide']['after_hits']}，与我这三枚文件上 {len(D.R6['in_my_three_files']['before'])} → "
        f"{len(D.R6['in_my_three_files']['after'])} 格；两把尺的差 "
        f"{json.dumps(D.R6['cross_check_against_r5']['cells_only_r5_reports']['before'], ensure_ascii=False)} "
        f"落在别人的文件上，两代同差）。"
        f"**判据面也按 Q71 扩过**：属性算屏幕，所以 e2e 每枚臂现在把整页 data-*/aria-* 逐对扫一遍——"
        f"扩仪器这一步是可复跑的补丁 ord0323_widen_q71.py blob {blob_line(D, 'ord0323_widen_q71.py')[0]} 与 "
        f"ord0323_widen_q71_r2.py blob {blob_line(D, 'ord0323_widen_q71_r2.py')[0]}（八条腿共用另一枚采集的那半在第二件里）。"
        f"每个形状一次全新 run id、各自一个 sqlite 库，改完的工作树字节与提交里的 blob 逐位回验过 "
        f"（矩阵里 per-shape 记着 restored）。")
    add("")
    add(f"**五、方向已经由你 03:43 的扩单定了：甲已执行。** 八个 catch 站点这一趟全部收敛到既有通道 "
        f"`frontend/src/lib/failureAttribution.ts`（{D.CHANNEL['lines']} 行，`classifyReadFailure` 在 :"
        f"{D.CHANNEL['exports_helpers'][0]}）；交付前这枚文件在 frontend/src 里只有 "
        f"{len(D.CHANNEL['importers_in_src'])} 枚引用者（{', '.join(x.split('/')[-1] for x in D.CHANNEL['importers_in_src'])}），"
        f"现在多一枚 —— 没有另造第二套归因词汇。剩下的只有一句要不要你确认：lane S1 的 ORD-0326 要件②是"
        f"「收敛成一条共享的服务器原因通道」，要件④还要在屏上出现服务器那句原话与 `request_id`；同一批汇"
        f"（尤其 `PlanWithAiSheet` 那条按 Q67=① 合法显示原话的链）如果 S1 后续要动，文件边界请按你 03:43 "
        f"那句『B 已动的文件一律让给 B』来分，我这边不扩。另一个读数供你裁：`request_id` 在 "
        f"`backend/app/main.py` 全文 {D.REQ_ID['main_py_at_base']['lines']} 行里命中 "
        f"{D.REQ_ID['main_py_at_base']['request_id_hits']} 次 —— 这三条腿的回答里根本没有这个字段，"
        f"要它上屏先得有它（它只在 agent 域作为调用方自带的幂等范围存在）。")
    add("")
    add(f"**六、如实报的缺口与本单没动的东西。**"
        f"其一，ORD-0326 ④ 要求屏幕上出现那句与 `request_id`，但 `backend/app/main.py` 全文 "
        f"{D.REQ_ID['main_py_at_base']['lines']} 行里 `request_id` 命中 "
        f"{D.REQ_ID['main_py_at_base']['request_id_hits']} 次 —— 这个字段在 inbox/memory/confirm 三条回答里"
        f"根本不存在（它只在 agent 域里作为调用方自带的幂等范围出现），要它上屏先要有它。"
        f"其二，同一文件里还有三条能把非本单原文带上屏的路径我没动，因为你没点名："
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{A['showResult_server_reason_to_message']['lines'][0]}` "
        f"把服务器的 `reason` 字段放进状态行、"
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{A['reasoning_summary_to_dom']['lines'][0]}` 与 "
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{A['reasoning_summary_to_dom']['lines'][1]}` "
        f"把 `reasoning_summary` 直接渲染、"
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{A['requestJson_unguarded_json_parse']['lines'][0]}` "
        f"的 json 解析不设防。其三，格一的文案语言取的是浏览器偏好而不是这台设备已存的 zh-CN"
        f"（量到的是 `{f1['panel_copy'][:22]}`），同一屏两处来源不同，我没改。"
        f"另：格一那枚折子里我留了一枚改前从未出现的指针 `unresolved_fields`（V8 报的是被访问的属性名 "
        f"length），它没有牙齿，我没把它算进反件证据，也没删那条断言。")
    add("")
    add(f"**七、动作边界。**0 次写权威线：我这趟 push 命令里只出现 "
        f"{json.dumps(D.PUSH_TARGETS, ensure_ascii=False)} 这一枚 ref，无 force-push；"
        f"权威线 {D.AUTH_REF} 与 `refs/heads/commander/control`、`refs/heads/cmdr/land-ord0302-b5` 在我"
        f"前后两次 ls-remote 之间动过的是前者与后者（{json.dumps(D.MOVED, ensure_ascii=False)[:260]}），"
        f"两条新 commit 的作者/标题都在收据里，没有一条是我的候选 {D.CAND}。"
        f"已发布路径 0 覆盖（全部新名，反件与量具各一枚新件，重复上架一律跳过而不是重 PUT）；"
        f"账本 0 直写（本块在 `D:\\moodle\\_qoder_ledger_inbox`）；`demo/reset` 0 次；"
        f"`_live.db` / `_preview.db` 0 读写；凭据 0 打印（本轮 e2e 里那句假原文是我造的字符串，见件内 readings）；"
        f"手机代次 0 改动（Q61）；`:8000` 我没起（那是你的决定）。")
    add("")
    add(f"**八、 ORD-0302 那头我这边同步一句。**Q67=① 落章后我不动文案、也不再为重投候选做任何事；"
        f"`frontend/src/features/planning/PlanWithAiSheet.tsx:1046` 那条链按你 04:05 的判词已是合规归属，"
        f"CLOSED 只差 ORD-0312 的派生闭环，那一格归 verifier E，我不自宣。")
    return "\n".join(lines) + "\n"


def unresolved_coordinates(D, text):
    subprocess.run(["git", "-C", str(D.FROZEN), "fetch", "-q", D.URL, "+refs/heads/*:refs/qoder-scan/*"],
                   capture_output=True, timeout=900)
    cited = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", text)))
    bad = []
    for s in cited:
        r = subprocess.run(["git", "-C", str(D.FROZEN), "cat-file", "-t", s], capture_output=True, text=True)
        if not (r.returncode == 0 and r.stdout.strip() in ("blob", "commit", "tree")):
            bad.append(s)
    return cited, bad


def write_block(D, text):
    cited, bad = unresolved_coordinates(D, text)
    if bad:
        raise SystemExit(f"{len(bad)} of {len(cited)} coordinates would not resolve: {bad[:4]}")
    print(f"coordinates in the block: {len(cited)} | unresolved 0")
    D.gate(text, "ledger-block")
    st = time.strftime("%H%M")
    p = D.INBOX / f"b-c01d72a3_{st}.md"
    if not text.startswith("### "):
        raise SystemExit("the block's first line must start with '### '")
    p.write_text(text, encoding="utf-8", newline="\n")
    if p.read_text(encoding="utf-8") != text:
        raise SystemExit("the block did not read back as written")
    print("block written:", p, len(text.encode("utf-8")), "B")
    return p


def post_bus(D, text):
    lead = (f"B c01d72a3 → 号令者 494abfd7：ORD-0323 两格交付（候选 {D.CAND[:12]}，基线 "
            f"{D.BASE[:12]}，分支 {D.BRANCH}）")
    body = lead + "\n\n" + text + "\n" + D.CLOSING
    cited, bad = unresolved_coordinates(D, body)
    if bad:
        raise SystemExit(f"{len(bad)} of {len(cited)} coordinates would not resolve: {bad[:4]}")
    D.gate(body, "bus")
    marker = "ORD-0323 两格交付"
    recent = api_comments(D)
    already = [c["id"] for c in recent if marker in (c.get("body") or "")]
    if already:
        print("bus post already exists, ids:", already, "-- not posting twice")
        return already[-1]
    made = D.api(f"/repos/{D.WS}/issues/1/comments", {"body": body})
    cid = made.get("id")
    if not cid:
        raise SystemExit("the bus did not answer with a comment id: " + json.dumps(made)[:200])
    # read back through the repo-wide comment route: the per-issue thread route 404s on a freshly
    # created comment id (measured this run: the POST answered, the thread readback did not).
    back = D.api(f"/repos/{D.WS}/issues/comments/{cid}")
    tail = (back.get("body") or "").strip().splitlines()[-1].strip()
    if tail != D.CLOSING.strip():
        raise SystemExit("the closing line did not survive the round trip: " + tail[:80])
    print("bus posted:", cid, "| closing line read back verbatim | body bytes",
          len((back.get("body") or "").encode("utf-8")))
    (D.WORK / "ord0323_bus_comment_id.txt").write_text(str(cid), encoding="utf-8")
    return cid


def api_comments(D):
    out = []
    for page in range(1, 4):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 6 * 3600))
        chunk = D.api(f"/repos/{D.WS}/issues/1/comments?per_page=100&page={page}&since={stamp}")
        if not isinstance(chunk, list) or not chunk:
            break
        out += chunk
        if len(chunk) < 20:
            break
    return out
