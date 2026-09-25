"""Re-point ORD-0323's receipt cell and ledger block at the per-leg arms.

The eight wallet legs were one test that reported a `legs` array; they are now eight arms that each report
one row, and the Q68 cell added two more. Anything still reading `N4.legs` would quote a reading that no
longer exists, so those two passages are rebuilt from the per-arm files.
"""
from __future__ import annotations

import ast
import pathlib

P = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")

# ---------------------------------------------------------------- deliver.py: the leg keys, from the runner's own names
d = P / "ord0323_deliver.py"
s = d.read_text(encoding="utf-8")
if "LEG_KEYS" not in s:
    s = s.replace('ARMS = ("N1", "N2", "N3", "N4")',
                  'LEG_KEYS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")\n'
                  'ARM_KEYS = ("N1", "N2", "N3") + LEG_KEYS + ("Q68a", "Q68b")')
    if "LEG_KEYS" not in s:  # the ARMS line may already read differently; append the constants instead
        s += ('\nLEG_KEYS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")\n'
              'ARM_KEYS = ("N1", "N2", "N3") + LEG_KEYS + ("Q68a", "Q68b")\n')
    d.write_text(s, encoding="utf-8", newline="\n")
    ast.parse(s)
    print("deliver: leg keys added")

# ---------------------------------------------------------------- stages.py: rebuild the leg cell
st = P / "ord0323_stages.py"
t = st.read_text(encoding="utf-8")
start = t.index('    legs = REA["fixed"]["N4"]["legs"]')
end = t.index('    add("代次：两格候选与新十格候选的字节关系", "MET",')
NEW = '''    leg_rows = {c: REA["fixed"][c] for c in D.LEG_KEYS}
    asked = {c: leg_rows[c]["status_asked"] for c in D.LEG_KEYS}
    bad_needle = [c for c in D.LEG_KEYS if leg_rows[c]["needles_found"]]
    bad_status = [c for c in D.LEG_KEYS if not leg_rows[c]["status_in_slot"]]
    bad_foreign = [c for c in D.LEG_KEYS if leg_rows[c]["foreign_status_found"]]
    frozen_bad = [c for c in D.LEG_KEYS if REA["cell2_status_frozen"][c]["foreign_status_found"]]
    frozen_ok = [c for c in D.LEG_KEYS if not REA["cell2_status_frozen"][c]["foreign_status_found"]]
    q68a, q68b = REA["fixed"]["Q68a"], REA["fixed"]["Q68b"]
    slot_texts = {c: leg_rows[c]["slot_text"] for c in D.LEG_KEYS}
    add("要件②扩到 D 数出的九格（T05-T13）与 Q68 那一格：逐臂双向", "MET",
        {"triage_artifact": "evidence/ord0320-triage-d/ord0320_triage_r2.json",
         "triage_blob": D.TRIAGE_BLOB, "cells_named_by_D": D.TRIAGE_CELLS,
         "file": D.CELL2, "blob_at_candidate_parent": D.CELL2_BASE_BLOB,
         "blob_at_candidate": D.CELL2_CAND_BLOB,
         "leg_keys": list(D.LEG_KEYS), "asked_status_per_leg": asked,
         "legs_with_a_needle_on_screen": bad_needle, "legs_missing_their_own_status": bad_status,
         "legs_showing_another_leg_status": bad_foreign, "slot_texts": slot_texts,
         "frozen_shape": {"legs_still_green": frozen_ok, "legs_reddened": frozen_bad,
                          "arm_status": {c: SH["cell2_status_frozen"]["per_arm"][c] for c in D.LEG_KEYS}},
         "q68": {"file": "frontend/src/features/planning/PlanWithAiSheet.tsx",
                 "code_arm_card": q68a["card_text"], "code_in_card": q68a["code_in_card"],
                 "prose_arm_code_slot": q68b["uppercased_prose_in_code_slot"],
                 "prose_arm_fold": q68b["reason_fold_text"],
                 "prose_arm_attributed": q68b["attributed_sentence_in_fold"],
                 "prose_arm_label": q68b["server_label_present"],
                 "slot_back": {"Q68a": SH["cell3_code_slot_back"]["per_arm"]["Q68a"],
                               "Q68b": SH["cell3_code_slot_back"]["per_arm"]["Q68b"]},
                 "ruling": "Q68=「编号槽只准放编号」；句子按 Q67=① 留在带归因标签的技术详情里"},
         "arms_matrix": DIR + "/ord0323_arms_matrix_r2.json"},
        "D 的分桶把钱包那枚文件数成九格：" + json.dumps(D.TRIAGE_CELLS, ensure_ascii=False)
        + "（T05 是折子，T06-T13 是八个 catch 站点，锚点行与逐行依据在她件 " + D.TRIAGE_BLOB + " 的 rows）。"
        "第一趟我只闭了源头 :88，r4 仍报 3 形：汇接的还是 `error.message` 这条流，而被拒的回复也可能以 fetch 的"
        " TypeError 或正文解析异常走进同一个汇。这一趟八个站点全部改走产品**已有**的通道（classifyReadFailure + "
        "copyFor 查表），没有一个站点把异常正文写进渲染态；机器位只放这台设备量到的 http_status / content_type / "
        "evidence kind。八条腿各一枚臂、各自一次全新状态码 " + json.dumps(asked, ensure_ascii=False)
        + "，逐臂读数：屏上有原话的腿 " + json.dumps(bad_needle, ensure_ascii=False) + "、缺自己状态的腿 "
        + json.dumps(bad_status, ensure_ascii=False) + "、把别腿状态顶上的腿 " + json.dumps(bad_foreign, ensure_ascii=False)
        + "。归因单独钉一枚反件（所有机器位印成 503）：问 503 的腿 " + json.dumps(frozen_ok, ensure_ascii=False)
        + " 照过，其余 " + json.dumps(frozen_bad, ensure_ascii=False) + " 立刻红 —— 说不清自己是哪条请求的汇不算量到。"
        "Q68 那一格是另一枚尺（r4）看得见、r3 看不见的形：`frontend/src/features/planning/PlanWithAiSheet.tsx:155`"
        " 在服务器没给编号时退回 `detail.slice(0, 60).toUpperCase()`，把句子截断大写后塞进「服务器回的原因编号是 …」。"
        "两臂各判一半：给了真编号的卡片仍显示编号（" + str(bool(q68a["code_in_card"])) + "，读数 "
        + json.dumps(str(q68a["card_text"])[:90], ensure_ascii=False) + "）；只给句子的卡片，编号位上没有句子（"
        + str(not q68b["uppercased_prose_in_code_slot"]) + "），而句子仍在带标签的技术详情里（"
        + str(bool(q68b["attributed_sentence_in_fold"])) + " / 标签在不在 "
        + str(bool(q68b["server_label_present"])) + "）。反件只把删掉的退回行放回去：Q68a "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68a"]) + " 保持绿、Q68b "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68b"]) + " 变红 —— 修的是「句子不许冒充编号」，不是「把那格清空」。")

'''
t = t[:start] + NEW + t[end:]
st.write_text(t, encoding="utf-8", newline="\n")
ast.parse(t)
print("stages: leg cell rebuilt from per-arm rows")

# ---------------------------------------------------------------- block.py: section two's tail quoted N4.legs
bl = P / "ord0323_block.py"
b = bl.read_text(encoding="utf-8")
anchor = 'f"新臂 N4 逐腿驱动八条路由，每腿两问：自己那句原话不在 DOM 里、自己那次 HTTP 状态在自己那个位上。读数（arms_matrix_r2 "\n'
if anchor in b:
    i = b.index('        f"新臂 N4 逐腿驱动八条路由')
    j = b.index('归因单独一枚反件：把所有机器位钉成 503，问 503 的那条腿照过、问别的立刻红。"')
    j = b.index("\n", j)
    b = b[:i] + '''        "八条腿各一枚独立臂（第一趟八腿共用一枚臂时，一条卡住的腿吃掉了整枚臂的超时，只留下 "
        "running_leg=T09 这样的线索），每腿两问：自己那句原话不在 DOM 里、自己那次 HTTP 状态在自己那个位上。"
        "读数（arms_matrix_r2 的 per_arm_readings.fixed）：屏上有原话的腿 "
        + json.dumps([c for c in D.LEG_KEYS if D.REA["fixed"][c]["needles_found"]], ensure_ascii=False)
        + "、缺自己状态的腿 "
        + json.dumps([c for c in D.LEG_KEYS if not D.REA["fixed"][c]["status_in_slot"]], ensure_ascii=False)
        + "、把别腿状态顶上的腿 "
        + json.dumps([c for c in D.LEG_KEYS if D.REA["fixed"][c]["foreign_status_found"]], ensure_ascii=False)
        + "。归因单独一枚反件：把所有机器位钉成 503，问 503 的那条腿照过、问别的立刻红（"
        + json.dumps([c for c in D.LEG_KEYS if D.REA["cell2_status_frozen"][c]["foreign_status_found"]],
                     ensure_ascii=False) + "）。"
        + Q68_SENTENCE)''' + b[j:]
    bl.write_text(b, encoding="utf-8", newline="\n")
    ast.parse(b)
    print("block: section two now reads the per-arm rows")
else:
    print("block: anchor not found -- leaving section two as it is")
