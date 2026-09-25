"""One-shot editor for p4_deliver.py: re-points the block's generation story to the 03:32 order.

Done as a script rather than in-shell so the CJK text and the f-strings survive intact; every replacement is
asserted to match exactly once, so a silent no-op is impossible.
"""
import ast
import pathlib

p = pathlib.Path('D:/moodle/HJ-P3_evidence/p4_deliver.py')
s = p.read_text(encoding='utf-8')


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)


# 1. headline: the generation moved, and the three rows are now mine
sub("M3 曾撞进它自己写的『停下上报』（要件钉的代次 ≠ '\n         '链上在跑的代次），现已闭到你 01:15 那枚探针件、写块前又只读复测一次；M4 已量；",
    "M3 的代次你 03:32 改指了（B 的 b5 落地 + 手机链已切代），新探针件三行我这回全部自己只读取回并逐字节对上；"
    "代价是我 pass-3 那九臂属于上一代，本格因此记 PARTIAL 不记已闭；M4 已量；")

# 2. the four-tuple generation line
sub("L.append(f'· generation = 我所有读数钉的是绑定件那一代 {M34[\"generation_as_ordered\"]}（你 01:16 令「就钉这一件 + '\n"
    "         f'这一代，不要重指」，我照做）。另记一支现读，因为它已经动了：`{MIRROR_REF}` 在写本块时（{MIRROR_AT}+08 '\n"
    "         f'由 {Q}git ls-remote origin {MIRROR_REF}{Q} 只读取回）= {Q}{MIRROR_SHA}{Q}，与你 00:36 那一读 '\n"
    "         f'{Q}{CMDR_0036}{Q} 同号 = {not moved} ⇒ 这支尖在 00:36 之后动过（动了几步我没数，那归你的账）。'\n"
    "         f'本块所有读数仍钉探针那一代，一件都没重指。')",
    "L.append(f'· generation = 按你 03:32 的令改指绑定件那代 {Q}{G2[\"generation_under_test\"]}{Q}（不是我挑的：'\n"
    "         f'探针件里 generation_under_test 与你口头那枚同号 = {G2[\"generation_field_equals_his_number\"]}）。'\n"
    "         f'`{MIRROR_REF}` 我写本块时再只读取回 = {Q}{MIRROR_SHA}{Q}，与那代同号 = '\n"
    "         f'{G2[\"mirror_tip_equals_the_ordered_generation\"]}；上一版块钉的 {M34[\"generation_as_ordered\"]} '\n"
    "         f'现在已是「被服务过的一代」，链上换成了 {G2[\"served_page\"][\"names_this_asset\"]}。')")

# 3. after the 01:15-binding paragraphs, add the 03:32 re-point section
anchor = ("L.append(f'  写本块时又只读复测了一次（又一个时间戳）：链上 `index.html` 里点的仍是 '")
assert s.count(anchor) == 1
i = s.index(anchor)
j = s.index("L.append('  两处不糊", i)
new_section = (
    "L.append(f'  【03:32 你改指代次，这版照做】新探针件 `{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"path\"]}` '\n"
    "         f'blob `{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"cited_blob\"]}`，我按 API 取字节重算 sha1 = '\n"
    "         f'`{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"recomputed_from_bytes_i_read\"]}`（与引用等 = '\n"
    "         f'{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"cited_equals_recomputed\"]}）；件内 probed_at_local '\n"
    "         f'{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"probed_at_local\"]}、overall '\n"
    "         f'{G2[\"cmdr_artefacts_read_back\"][\"phone_probe_after_r1\"][\"overall\"]}。另两件也一并回读重算：部署回执 '\n"
    "         f'`{G2[\"cmdr_artefacts_read_back\"][\"deploy_receipt_r1\"][\"cited_blob\"]}` = '\n"
    "         f'{G2[\"cmdr_artefacts_read_back\"][\"deploy_receipt_r1\"][\"cited_equals_recomputed\"]}、落地预检 '\n"
    "         f'`{G2[\"cmdr_artefacts_read_back\"][\"landing_preflight_r1\"][\"cited_blob\"]}` = '\n"
    "         f'{G2[\"cmdr_artefacts_read_back\"][\"landing_preflight_r1\"][\"cited_equals_recomputed\"]}。')\n"
    "L.append(f'  三行这回全部我自己只读取回（一次读页取资产名 + 每行一次 GET，经 :4781 那一跳，0 写 0 凭据）：{g2rows} '\n"
    "         f'⇒ 三行逐字节等值 = '\n"
    "         f'{g2v[\"all_three_rows_match_my_own_read_byte_for_byte\"]}、状态等值 = '\n"
    "         f'{g2v[\"and_every_row_returns_the_status_the_probe_recorded\"]}、链上页面点的正是探针那枚资产 = '\n"
    "         f'{g2v[\"the_chain_now_serves_the_asset_the_probe_names\"]}（上一版我只能核 JS 那一行，CSS 与 sw 是你读的）。')\n"
    "L.append(f'  你说的「union 不删」我也量了：旧资产 `{g2old[\"path\"]}` 现在仍回 {g2old[\"http_status\"]} / '\n"
    "         f'{g2old[\"bytes\"]} B，sha256 与我 pass-3 那代字节等 = '\n"
    "         f'{g2old[\"equals_the_generation_i_measured_pass3\"]} ⇒ 旧读数作为历史读数成立，架没被拆。')\n"
    "L.append(f'  但不糊你的地方：{G2[\"generation_of_my_pass3_arms\"][\"what_this_means\"]} 本块判据件 '\n"
    "         f'`{P312}/{G2P}` blob `{B(P312 + \"/\" + G2P)}`，量具 `{P312}/instruments/p4_m3_bind_gen2.py`；'\n"
    "         f'{len(G2[\"verdict\"]) - 1} 条判语合判 ALL_HOLD = {g2v[\"ALL_HOLD\"]}。'\n"
    "         f'所以 M3 这一格我记 PARTIAL：代次与三行已按新件钉死，九臂读数要在 {G2[\"generation_under_test\"][:8]}… '\n"
    "         f'上重跑才敢说同代，重跑的代价与下一步在同一条总线帖里给。')\n")
s = s[:j] + new_section + s[j:]

# 4. the 01:38 re-check paragraph must be labelled as the previous generation, or it reads as a contradiction
sub("L.append(f'  写本块时又只读复测了一次（又一个时间戳）：链上 `index.html` 里点的仍是 '",
    "L.append(f'  写上一版块时（01:38）也这样只读复测过一次，那时代次还没换、结论当时为真；这条现在只算上一代的'\n"
    "         f'历史读数，保留它是为了让两侧读数都在。当时链上 `index.html` 里点的仍是 '")

# 5. M2's cited lines must be content-anchored, not line-number-anchored, because the file moved
sub("阻塞具名：那句承诺在 `PlanWithAiSheet.tsx:287`'\n"
    "         '（:203 是另一支无本地文案的 BLOCKED 码），要落那一支得让 mission 存下一个具名数据成因；'",
    "阻塞具名按内容锚定（行号随代次漂）：那句「服务器说这次没排出可行方案…」在新尖 '\n"
    "         '`9a669c8b…` 的 `PlanWithAiSheet.tsx:315`，上一代 `7856e03f…` 里它在 :287；另一支「这条我们还没有本地文案」'\n"
    "         '现在在 :218（原 :203）。要落那一支得让 mission 存下一个具名数据成因；'")

p.write_text(s, encoding='utf-8')
ast.parse(s)
print('PATCHED + PARSES')
