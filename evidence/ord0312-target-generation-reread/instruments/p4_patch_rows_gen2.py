"""Give every byte-count its own nearby coordinate.

Q43's window is ±200 characters around a numeric claim, and a path in backticks is not a coordinate - only a
40-hex, a `blob`+hex pair, a run id, `refs/heads/...` or `file.ext:NNN` is. Last run the three served rows were
smashed into one sentence, so the third row's byte count sat outside the reach of the blob I cited at the end.
One row per line, each carrying the probe's blob, is the shape that satisfies the ruler without deleting a digit.
"""
import ast
import pathlib

p = pathlib.Path('D:/moodle/HJ-P3_evidence/p4_deliver.py')
s = p.read_text(encoding='utf-8')


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


# 1. per-row table: one line per row, with the probe blob on the same line
sub("""g2rows = '; '.join(f'{k} 我读 {v["my_read"]["bytes"]} B/{v["my_read"]["http_status"]} vs 件里 '
                   f'{v["probe_row"]["bytes"]} B/{v["probe_row"]["http_status"]} 等值 = '
                   f'{v["bytes_equal"] and v["sha256_equal"] and v["status_equal"]}'
                   for k, v in sorted(g2r.items()))""",
    """G2PROBE = G2['cmdr_artefacts_read_back']['phone_probe_after_r1']
g2rows = '\\n  · '.join(
    f'{Q}{k}{Q} 我读 {v["my_read"]["bytes"]} B / {v["my_read"]["http_status"]} / '
    f'{v["my_read"]["content_type"]}，件里 {v["probe_row"]["bytes"]} B / {v["probe_row"]["http_status"]}，'
    f'字节与 sha256 全等 = {v["bytes_equal"] and v["sha256_equal"]}，状态等 = {v["status_equal"]}'
    f'（件 {G2PROBE["path"]} blob {Q}{G2PROBE["cited_blob"]}{Q}）'
    for k, v in sorted(g2r.items()))""")

# 2. the row paragraph: the numbers now live in the per-row lines, so this line only carries the合判
sub("""L.append(f'  三行这回全部我自己只读取回（一次读页取资产名 + 每行一次 GET，经 :4781 那一跳，0 写 0 凭据）：{g2rows} '
         f'⇒ 三行逐字节等值 = '
         f'{g2v["all_three_rows_match_my_own_read_byte_for_byte"]}、状态等值 = '
         f'{g2v["and_every_row_returns_the_status_the_probe_recorded"]}、链上页面点的正是探针那枚资产 = '
         f'{g2v["the_chain_now_serves_the_asset_the_probe_names"]}（上一版我只能核 JS 那一行，CSS 与 sw 是你读的）。')""",
    """L.append('  三行这回全部我自己只读取回（一次读页取资产名 + 每行一次 GET，经 :4781 那一跳，0 写 0 凭据）：')
L.append('  · ' + g2rows)
L.append(f'  三行合判：逐字节等 = {g2v["all_three_rows_match_my_own_read_byte_for_byte"]}、状态等 = '
         f'{g2v["and_every_row_returns_the_status_the_probe_recorded"]}、链上页面点的正是探针那枚资产 = '
         f'{g2v["the_chain_now_serves_the_asset_the_probe_names"]}（上一版我只能核 JS 那一行，CSS 与 sw 是你读的）')""")

# 3. retention line: name the artefact and its blob on the same line as the two numbers
sub("""L.append(f'  你说的「union 不删」我也量了：旧资产 `{g2old["path"]}` 现在仍回 {g2old["http_status"]} / '
         f'{g2old["bytes"]} B，sha256 与我 pass-3 那代字节等 = '
         f'{g2old["equals_the_generation_i_measured_pass3"]} ⇒ 旧读数作为历史读数成立，架没被拆。')""",
    """L.append(f'  你说的「union 不删」我也量了（同一只读法）：旧资产 {Q}{g2old["path"]}{Q} 现在仍回 '
         f'状态 {g2old["http_status"]}、{g2old["bytes"]} B，sha256 与我 pass-3 那代字节等 = '
         f'{g2old["equals_the_generation_i_measured_pass3"]} ⇒ 旧读数作为历史读数成立，架没被拆'
         f'（这条读数在 {P312}/{G2P} blob {Q}{B(P312 + "/" + G2P)}{Q}）。')""")
p.write_text(s, encoding='utf-8')
ast.parse(s)
print('PATCHED + PARSES')
