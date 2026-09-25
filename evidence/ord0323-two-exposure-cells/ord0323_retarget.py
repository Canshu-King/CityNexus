"""Retarget the ORD-0323 receipt and block at the ten-cell candidate (commander 03:43 expansion).

Two cells are added (the eight legs D numbered; the re-cut onto the live tip), the cell that claimed a
residual is corrected -- because the residual it described is what this pass fixed -- and the block's section
two says the same thing in prose. Run once; it asserts every anchor occurs exactly once.
"""
from __future__ import annotations

import ast
import pathlib

S = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0323_stages.py")
B = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0323_block.py")


def rep(text, old, new, name):
    if text.count(old) != 1:
        raise SystemExit(f"anchor {text.count(old)}x in {name}: {old[:70]!r}")
    return text.replace(old, new)


s = S.read_text(encoding="utf-8")

s = rep(
    s,
    '''        + json.dumps(R3["shape_identity"]["shapes_new"], ensure_ascii=False) + "；剩下的形状是同一文件里那八处 "
        "catch 块读自己那条腿的异常正文，一行代码没动，只是被我新增的行推下去 "
        + json.dumps(sorted({d for x in R3["shape_identity"]["same_shape_renumbered"] for d in x["line_delta"]}))
        + " 行。那是图案判定不是内容判定，内容归 e2e 两向断言。")''',
    '''        + json.dumps(R3["shape_identity"]["shapes_new"], ensure_ascii=False) + "；改后仍报 "
        + str(len(R3["shape_identity"]["same_shape_renumbered"])) + " 类。尺只认图案，句子内容归 e2e 两向断言。")''',
    "r3-tail",
)

CELLS = '''    legs = REA["fixed"]["N4"]["legs"]
    flegs = REA["cell2_status_frozen"]["N4"]["legs"]
    asked = {l["cell"]: l["status_asked"] for l in legs}
    add("要件②扩到 D 数出的九格（T05-T13）：八条腿各自双向", "MET",
        {"triage_artifact": "evidence/ord0320-triage-d/ord0320_triage_r2.json",
         "triage_blob": D.TRIAGE_BLOB, "cells_named_by_D": D.TRIAGE_CELLS,
         "file": D.CELL2, "blob_at_candidate_parent": D.CELL2_BASE_BLOB,
         "blob_at_candidate": D.CELL2_CAND_BLOB,
         "leg_count": REA["fixed"]["N4"]["leg_count"], "legs": legs,
         "asked_status_per_leg": asked,
         "legs_with_a_needle_on_screen": [l["cell"] for l in legs if l["needles_found"]],
         "legs_missing_their_own_status": [l["cell"] for l in legs if not l["status_in_slot"]],
         "legs_showing_another_leg_status": [l["cell"] for l in legs if l["foreign_status_found"]],
         "channel": {"file": D.CHANNEL["path"],
                     "classifyReadFailure_at": D.CHANNEL["exports_helpers"][0],
                     "imported_only_by_before_this_order": D.CHANNEL["importers_in_src"]},
         "frozen_shape": {"N2": SH["cell2_status_frozen"]["per_arm"]["N2"],
                          "N3": SH["cell2_status_frozen"]["per_arm"]["N3"],
                          "N4": SH["cell2_status_frozen"]["per_arm"]["N4"],
                          "frozen_legs": [l["cell"] for l in flegs if l["foreign_status_found"]],
                          "legs_asking_503": [c for c, v in asked.items() if v == 503]},
         "arms_matrix_r2": DIR + "/ord0323_arms_matrix_r2.json"},
        "D 的分桶把这一枚文件数成九格：" + json.dumps(D.TRIAGE_CELLS, ensure_ascii=False)
        + "（T05 是那具折子，T06-T13 是八个 catch 站点；锚点行与逐行依据在她件里，blob " + D.TRIAGE_BLOB
        + "）。我第一趟只闭了源头 :88，r4 那时仍报 3 形：汇接的还是 `error.message` 这条流，而被拒的回复也可能"
          "以 fetch 的 TypeError 或正文解析异常的样子走进同一个汇。这一趟把八个站点全收敛到产品**已有**的通道 "
        + D.CHANNEL["path"] + ":" + str(D.CHANNEL["exports_helpers"][0])
        + " 的 classifyReadFailure 与 copyFor —— 句子查表得来、`status` 从错误对象上读，没有任何站点再把异常正文"
          "写进渲染态；机器位只放这台设备量到的 http_status / content_type / evidence kind。"
        "新臂 N4 逐腿驱动八条路由（各自一次全新状态码：" + json.dumps(asked, ensure_ascii=False)
        + "），每腿两问：自己那句原话不在 DOM 里、自己那次状态在自己那个位上。实测：屏幕找到原话的腿 "
        + json.dumps([l["cell"] for l in legs if l["needles_found"]], ensure_ascii=False) + "、缺自己状态的腿 "
        + json.dumps([l["cell"] for l in legs if not l["status_in_slot"]], ensure_ascii=False)
        + "、把别腿状态顶上的腿 " + json.dumps([l["cell"] for l in legs if l["foreign_status_found"]], ensure_ascii=False)
        + "。归因单独钉一枚反件：把所有机器位印成 503，问 503 的腿 "
        + json.dumps([c for c, v in asked.items() if v == 503], ensure_ascii=False) + " 照旧过，其余 "
        + json.dumps([l["cell"] for l in flegs if l["foreign_status_found"]], ensure_ascii=False)
        + " 立刻红（N3/N4 得 " + str(SH["cell2_status_frozen"]["per_arm"]["N3"]) + "/"
        + str(SH["cell2_status_frozen"]["per_arm"]["N4"]) + "）—— 说不清自己是哪条请求的汇不算量到。")

    add("代次：两格候选与新十格候选的字节关系", "MET",
        {"ordered_base": D.BASE, "prev_candidate": D.PREV_CAND, "prev_branch": D.PREV_BRANCH,
         "prev_remote_readback": D.PREV_REMOTE, "candidate": D.CAND, "branch": D.BRANCH,
         "candidate_parent": D.PARENT_LIVE, "parent_meta": D.TIP_META, "blob_identity": D.RECUT_BLOBS,
         "force_pushes_by_me": 0, "refs_created_by_me": [D.PREV_BRANCH, D.BRANCH]},
        "扩单要求基线现读。两格候选 " + D.PREV_CAND + " 挂在 " + D.PREV_BRANCH + "，架上回读 " + D.PREV_REMOTE
        + "，那枚 ref 我不移动也不 force（已发布坐标不重写）；十格候选重切到他当下的尖 " + D.PARENT_LIVE
        + "（" + str(D.TIP_META) + "）之上 = " + D.CAND + "，分支新名 " + D.BRANCH
        + "。重切是搬运不是改写：我碰过的三枚文件在两个候选上逐位相同（"
        + json.dumps(D.RECUT_BLOBS, ensure_ascii=False) + "）；矩阵、两把尺、e2e 全在新候选上重跑，旧读数不折算。")

'''
s = rep(s, "    A = D.ADJ\n    add(\"如实报的残留（本单没点名，我也没动）\", \"REPORTED_NOT_FIXED\",",
          CELLS + "    A = D.ADJ\n    add(\"如实报的残留（本单没点名，我也没动）\", \"REPORTED_NOT_FIXED\",",
          "insert-cells")

s = rep(
    s,
    '''        "三件如实报上去、我没有顺手改。其一，同一文件 " + D.CELL2 + " 里那八处 catch 块把这条腿自己的异常正文写进"
        "屏上文案（改后 r3 仍报 " + str(D.R3["after"]["hit_count"]) + " 处命中，行号见上一格）：内容上它现在拿到的是"
        "设备自造句，但图案尺看不见内容。其二，" + D.CELL2 + " 的 "''',
    '''        "两件如实报上去、我没有顺手改。其一，" + D.CELL2 + " 的 "''',
    "residual-1",
)
s = rep(
    s,
    '''        + " 这几行也能把非本单的原文带上屏（未设防的 json 解析异常、服务器的 reason 字段、reasoning_summary），"
          "本单只点名 :88 与 687/691/731，我只读数不动手。其三，" + D.CELL1 + " 的文案语言取自浏览器偏好（量到 "''',
    '''        + " 这几行也能把非本单的原文带上屏（未设防的 json 解析异常、服务器的 `reason` 字段、`reasoning_summary`）"
          "—— 不在本单点名的十格里，D 的分桶另有归类，我只读数不动手。其二，" + D.CELL1 + " 的文案语言取自浏览器偏好（量到 "''',
    "residual-2",
)
S.write_text(s, encoding="utf-8", newline="\n")
ast.parse(s)

b = B.read_text(encoding="utf-8")
b = rep(
    b,
    '''        f"**没修的那一半要说清**：r4 仍在这一枚文件报 3 形，就是 `frontend/src/features/inbox/JourneyInboxWorkbench.tsx:703`、"
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:707`、"
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:747` 三处 —— 与你点名的 687/691/731 同一批汇，"
        f"只是被我新增的 "
        f"{R4['per_file_lines'][0]['lines_after'][0] - R4['per_file_lines'][0]['lines_before'][0]} 行推下去。"''' ,
    '''        f"这一格按你 03:43 的扩单做到 D 数出的九格（T05-T13，她件 "
        f"{D.TRIAGE_BLOB} 的 rows，锚点行 " + json.dumps(D.TRIAGE_CELLS, ensure_ascii=False) + "）。"
        f"八个 catch 站点全部收敛到产品**已有**的那条通道 `frontend/src/lib/failureAttribution.ts`"
        f"（classifyReadFailure 在 :" + str(D.CHANNEL['exports_helpers'][0]) + "，句子由 copyFor 查表），"
        f"没有一个站点再把异常正文写进渲染态；机器位只放这台设备量到的 http_status / content_type / evidence kind。"
        f"新臂 N4 逐腿驱动八条路由，每腿两问：自己那句原话不在 DOM 里、自己那次 HTTP 状态在自己那个位上 —— "
        f"实测缺自己状态的腿 "
        f"{json.dumps([l['cell'] for l in D.MATRIX['per_arm_readings']['fixed']['N4']['legs'] if not l['status_in_slot']], ensure_ascii=False)}、"
        f"屏幕找到原话的腿 "
        f"{json.dumps([l['cell'] for l in D.MATRIX['per_arm_readings']['fixed']['N4']['legs'] if l['needles_found']], ensure_ascii=False)}。"
        f"归因单独一枚反件：把所有机器位钉成 503，问 503 的腿照过、问别的立刻红。"''' ,
    "block-2-head",
)
# the old sentence continued with the pre-fix flow text; drop the leftovers
b = rep(
    b,
    '''        f"它们仍然接的是 `catch (error) {{{{ setMessage(error.message) }}}}` 这条流：汇不变，源头换了我这句设备自造的话，"
        f"但 `fetch` 自己抛的 TypeError 或 `response.json()` 抛的解析异常（同一文件 "
        f"`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:{A['requestJson_unguarded_json_parse']['lines'][0]}` "
        f"那一行没有设防）也能走进同一个汇。要真把这三形关掉，得让八个 catch 站点改成"
        f"`classifyReadFailure` 那条既有通道，这不在你点名的 :88 那一行里，见第五节的方向冲突。")''',
    '''        f"这一格到此处闭口：两把尺在这两枚文件上都是 0 形（r3 改前 10 → 改后 {R3['after']['hit_count']}，"
        f"r4 改前 {R4['before']['hit_count']} → 改后 {R4['after']['hit_count']}）。")''',
    "block-2-tail",
)
B.write_text(b, encoding="utf-8", newline="\n")
ast.parse(b)
print("retarget applied")
