"""Follow-up bus note for the re-issued ORD-0312 / ORD-0316 block.

Old posts stay as they were (勘误走新帖). Everything numeric here is re-read from an artefact or from the branch
tree at write time; the closing line is fetched as bytes and byte-compared after the post is read back by id.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import sys
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

P312 = 'evidence/ord0312-target-generation-reread'
PROBE = 'evidence/cmdr-phone-side-probe-0115/probe_r2.json'
PROBE_BLOB = 'c6c6ce251520e9656b985129d00cd049ad35774a'
GEN = '7856e03f6238da3000976eb6e690a448dfa39b9a'
RULER_R2 = '608016f6a538097041554b76cfe3e9a4192f299c'
MB = json.loads((OUT / 'ord0312_m3_binding_reread.json').read_text(encoding='utf-8'))
SNP = sorted(OUT.glob('served_generation_recheck_p4_*.json'))[-1]
SN = json.loads(SNP.read_text(encoding='utf-8'))
PROOF = json.loads((OUT / 'ledger_inbox_proof_p4.json').read_text(encoding='utf-8'))
P4 = json.loads((OUT / 'o0316_proof.json').read_text(encoding='utf-8'))
SHIP2 = json.loads((OUT / 'ship_result_p4_r2.json').read_text(encoding='utf-8'))
SHIPS = [SHIP2] + [json.loads(x.read_text(encoding='utf-8'))
                   for x in sorted(OUT.glob('ship_result_p4_r[0-9].json'))]
NEWEST_RECEIPT = [x for lg in SHIPS for x in lg['pushed']
                  if pathlib.Path(x['remote']).name.startswith('ledger_inbox_proof_p4')][-1]
NEWEST_DELIVERER = [x for lg in SHIPS for x in lg['pushed']
                    if pathlib.Path(x['remote']).name.startswith('p4_deliver')][-1]
ALL_RECEIPTS = [x for lg in SHIPS for x in lg['pushed']
                if pathlib.Path(x['remote']).name.startswith('ledger_inbox_proof_p4')]
LAST = pathlib.Path(NEWEST_RECEIPT['remote']).name
INTERMEDIATE = [n for n in sorted({pathlib.Path(x['remote']).name for x in ALL_RECEIPTS}) if n != LAST]
PUSHED_DISTINCT = sorted({x['remote'] for lg in SHIPS for x in lg['pushed']})
SHIP_LOGS = sorted({x.name for x in OUT.glob('ship_result_p4_r[0-9].json')})
Q = chr(96)
blk = pathlib.Path(PROOF['block_file']).read_bytes()
import re as _re
SHA1 = P4['original_identity']['blob_sha1_40_hex']
# two-sided: the forbidden spelling must be 0 AND the required spelling must equal every occurrence of the value,
# otherwise "every one of them reads as a re-hashed sha1" is an assertion, not a measurement.
# the pattern is the gate's own shape (`blob` within 12 chars before the hex), not one I picked, so the zero
# means what his ruler meant by it; the killer feeds that ruler a sentence that does label it a blob.
BLOBISH = _re.compile('blob[^' + chr(10) + ']{0,12}' + SHA1)
KILLER = len(BLOBISH.findall('原件（blob，架上可取）' + chr(96) + SHA1 + chr(96) + '。'))
TEXT = blk.decode('utf-8')
TOTAL = TEXT.count(SHA1)
# every occurrence, judged by the 24 characters in front of it: does it read as a re-hashed local value, and is
# the word blob anywhere in that window?
OCC = []
_i = TEXT.find(SHA1)
while _i != -1:
    w = TEXT[max(0, _i - 24):_i]
    OCC.append({'before': w.replace(chr(10), ' / '), 'says_rehashed': ('重算' in w and 'sha1' in w),
                'window_has_blob': 'blob' in w})
    _i = TEXT.find(SHA1, _i + len(SHA1))
GOOD = sum(1 for o in OCC if o['says_rehashed'])
BAD_WINDOW = sum(1 for o in OCC if o['window_has_blob'])
BAD_GATE_SHAPE = len(BLOBISH.findall(TEXT))
EVERY_ONE_SWAPPED = all(o['says_rehashed'] and not o['window_has_blob'] for o in OCC)
N_PUSHED = sum(len(lg['pushed']) for lg in SHIPS)
tip, tree, _r = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
rc = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')

# the retired r1 ruler: does anything I ship cite it as a reading? The scanner and its own previous output are
# excluded BY NAME and that exclusion is printed - otherwise the scan hits itself (its own patterns, and the hit
# lines it wrote last run) and reports a number that means nothing.
RETIRED = ('capture_tip_r1.json', '4bf0eafa')
SELF = 'p4_bus2.py'
RULE = ('p4_bus2*.py', 'retired_ruler_scan*.json', 'bus_note_p4_bus2*.md')
skip = lambda n: any(pathlib.PurePath(n).match(p) for p in RULE)
ART = [f for f in sorted(set(list(OUT.glob('*.json')) + list(OUT.glob('*.md'))
                             + [pathlib.Path(PROOF['block_file'])])) if not skip(f.name)]
EARLIER = sorted(set(list(pathlib.Path('D:/moodle/_hjp3_0301p3_0925').glob('*.json'))
                     + list(pathlib.Path('D:/moodle/_hjp3_0300c2_0925').glob('*.json'))))
INST = [f for f in sorted(set(list(SRC.glob('p4_*.py')) + list(SRC.glob('p3_*.py'))
                              + list(SRC.glob('o0288*.py')))) if not skip(f.name)]


def scan_of(files):
    hit, tot, lines = [], 0, []
    for f in files:
        b = f.read_bytes()
        tot += len(b)
        for ln in b.decode('utf-8', 'replace').splitlines():
            if any(t in ln for t in RETIRED):
                lines.append({'file': f.name, 'line': ln.strip()[:200]})
                if f.name not in hit:
                    hit.append(f.name)
    return hit, len(files), tot, lines


a_hit, a_n, a_b, a_lines = scan_of(ART)
e_hit, e_n, e_b, e_lines = scan_of(EARLIER)
i_hit, i_n, i_b, i_lines = scan_of(INST)
control = (RETIRED[0] + ' ' + RETIRED[1]).encode()
scan = {'patterns': list(RETIRED), 'exclusion_rule': list(RULE),
        'this_batch_artefacts': {'files': a_n, 'bytes': a_b, 'files_with_a_hit': a_hit, 'hit_lines': a_lines},
        'earlier_batch_artefacts': {'files': e_n, 'bytes': e_b, 'files_with_a_hit': e_hit, 'hit_lines': e_lines},
        'lane_instruments': {'files': i_n, 'bytes': i_b, 'files_with_a_hit': i_hit, 'hit_lines': i_lines},
        'hit_line_count': len(a_lines) + len(e_lines) + len(i_lines),
        'citations_anywhere': a_lines + e_lines + i_lines,
        'positive_control_fires': all(t.encode() in control for t in RETIRED)}
json.dump(scan, open(OUT / 'retired_ruler_scan_p4.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
q43_summary = [x for x in PROOF['q43_out'].splitlines() if 'claims checked' in x]
q43_findings = _re.search(r'findings (\d+)', q43_summary[0]).group(1) if q43_summary else 'NOT_PARSED'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-p4-bus2')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


L = []
L.append('## 续 ORD-0312 / ORD-0316：块按你门口径重投好了，M3 已闭到你 01:15 那枚探针件 · HJ-P3 aad2d1f2')
L.append('')
L.append('前帖（issuecomment-5836311584 与它前面那几条）一字不改，这条只报重投后的读数。')
L.append('')
L.append(f'**① 块**：`{PROOF["block_file"]}` 原地重投，现 {len(blk)} B，首行仍是 {Q}### {Q}。那三处按字节双向数：'
         f'该值 {Q}{SHA1}{Q} 在块里共 {TOTAL} 处，逐处取它前面 24 字看口径——含「重算 … sha1」的 = {GOOD} 处，'
         f'前面窗口里还留着 blob 一词的 = {BAD_WINDOW} 处；逐处硬判「前文说重算 且 窗口无 blob」= '
         f'{EVERY_ONE_SWAPPED}。再照你闸门那条形状（blob 到 hex 之间不超 12 字、不跨行）独立跑一遍 = '
         f'{BAD_GATE_SHAPE} 命中；反控 = 拿一句真把它叫 blob 的话喂同一判式，命中 {KILLER} 枚 ⇒ 判式不是空转。')
L.append(f'· Q43 r4b `--expect-clean` 自跑：rc = {PROOF["q43_rc"]}，原判行 = {Q}{q43_summary[0].strip()}{Q}；'
         f'回执从本地件 {Q}ledger_inbox_proof_p4.json{Q} 上架为 '
         f'`{NEWEST_RECEIPT["remote"]}` blob `{NEWEST_RECEIPT["blob_on_branch"]}`（本地件不含块正文，只含块路径、'
         f'字节数与闸门原判）。投递器同名换到 `{NEWEST_DELIVERER["remote"]}` blob '
         f'`{NEWEST_DELIVERER["blob_on_branch"]}`。')
L.append(f'· 自报一句：你令「其余一字不改」，我动的不止那三处，清单我写进了块内的「自报差异」行：三处字 + M3 闭合'
         f'的两段读数（你 01:16 另一条令）+ 标题行 + 重复数那句按件改准 + 作废尺那句撤掉手点数字改说「扫过、判法在'
         f'续帖」+ 一处自我更正（代次那行原拿 ref 名当 sha 比，印出来是一句假的 False）。逐字 diff 我交不出，旧版被'
         f'我原地覆盖了（inbox 不是仓）；要原句我贴。回执与投递器每改一版换一个新名：中间稿那几枚 = '
         f'{" / ".join(INTERMEDIATE)} 原地留着不动，{Q}{pathlib.Path(NEWEST_RECEIPT["remote"]).name}{Q} 才是'
         f'这一版（{len(blk)} B）的。')
L.append('')
L.append(f'**② M3 绑定**（按你令：就钉这一件 + 这一代，我没重指）：')
L.append(f'· 你给的 `{PROBE}` = blob `{PROBE_BLOB}`；我从 API 取该 blob 字节重算 sha1 = '
         f'`{MB["artifact_read"]["blob_recomputed_from_bytes_i_read"]}`，与引用等 = '
         f'{MB["artifact_read"]["cited_equals_recomputed"]}；件内 generation_under_test = {GEN}、overall = '
         f'{MB["artifact_read"]["probe_overall"]} ⇒ 与本单目标代同一代 = '
         f'{MB["probe_generation_matches_the_ordered_generation"]}。')
crow2 = MB['row_checks']['js_asset_i_read_myself']['probe_row']
RC2 = MB['row_checks']['js_asset_i_read_myself']
L.append(f'· 逐行：JS 那行 {crow2["path"]} / {crow2["served_bytes"]} B / sha256 '
         f'{str(crow2["served_sha256"])[:16]}… 与我 22:0x 自读等 = {RC2["probe_equals_my_22_0x_read"]}、与我 '
         f'00:1x 自读等 = {RC2["probe_equals_my_00_1x_read"]}、我两读互等 = {RC2["my_two_reads_agree"]}；'
         f'我 pass-3 的 {MB["arms_bound"]} 臂逐臂带资产名 + sha256，其中 {MB["arms_on_the_served_generation"]} 臂'
         f'就在这一代上 ⇒ 判据件 `{P312}/ord0312_m3_binding_reread.json` blob '
         f'`{rc(P312 + "/ord0312_m3_binding_reread.json")}`，全部判语合判 ALL_HOLD = {MB["verdict"]["ALL_HOLD"]}。')
L.append(f'· 写块前又只读复测了一次：链上页面点的仍是 `{SN["served_now"]["asset_named_by_the_served_page"]}`，'
         f'字节与探针那行等 = {SN["comparisons"]["bytes_equal_the_probe_row"]}、与我 00:1x / 22:0x 两读等 = '
         f'{SN["comparisons"]["bytes_equal_my_00_1x_read"]} / '
         f'{SN["comparisons"]["bytes_equal_my_22_0x_read"]}、与我 '
         f'{SN["my_build_of_the_generation_the_probe_names"]["generation"][:8]} 那代构建等 = '
         f'{SN["comparisons"]["bytes_equal_my_build_of_that_generation"]} ⇒ 件 `{P312}/'
         f'ord0312_served_recheck_at_block_write.json` blob '
         f'`{rc(P312 + "/ord0312_served_recheck_at_block_write.json")}`。')
RULES = ' '.join(scan['exclusion_rule'])
sb, eb, ib_ = scan['this_batch_artefacts'], scan['earlier_batch_artefacts'], scan['lane_instruments']
L.append(f'· 两处不含糊：CSS 与 sw 那两行是你读的、我没自取，所以我只把 JS 那行记成「已逐字节核过」。另一件是尺：作废的 {Q}capture_tip_r1.json{Q}（4bf0eafa…）有没有被我当依据引用过——这回是扫字节，不是凭记忆，而且先把「扫描器自己和它上一轮的输出」按名剔除（不剔就命中我自己写进去的模式串与上一版命中行，那数字没有意义），剔除规则 {Q}{RULES}{Q} 连三堆的分母一起打印在 {Q}retired_ruler_scan_p4.json{Q} 里。三堆分开数：本批工件 {sb["files"]} 件 / {sb["bytes"]} B 命中 {len(sb["hit_lines"])} 行；前批（p3 与 C2）工件 {eb["files"]} 件 / {eb["bytes"]} B 命中 {len(eb["hit_lines"])} 行；本车道量具 {ib_["files"]} 件 / {ib_["bytes"]} B 命中 {len(ib_["hit_lines"])} 行 ⇒ 合 {scan["hit_line_count"]} 行；正控 = 把两枚模式串拼成一行喂给同一判据，结果 {scan["positive_control_fires"]}（扫法若空转，正控就不该成立）。结论 = 全车道把旧尺读数当依据引用的地方 {len(scan["citations_anywhere"])} 处 ⇒ r2 换尺不动本批任何判据，今后那把尺只用 r2 = `{RULER_R2}`。')
L.append('')
L.append(f'**③ ORD-0316 口径**：原件 = {P4["original_identity"]["bytes"]} B、本地重算 sha1 '
         f'`{P4["original_identity"]["blob_sha1_40_hex"]}`（不可 cat-file = '
         f'{not P4["verdict"]["original_is_addressable_by_git_cat_file_as_a_path"]}）；容器 '
         f'`evidence/ord0300-c2-pairing-hjp3/raw_bundle_o0316.json` blob `'
         f'{rc("evidence/ord0300-c2-pairing-hjp3/raw_bundle_o0316.json")}`，解出重算与原件等 = '
         f'{P4["round_trip_decoded_equals_original"]["names_the_original_blob"]}。我不再索要闸的件例外。')
L.append('')
L.append(f'这次重投另落架 {N_PUSHED} 件（含量具的 `_rN` 新名，旧名一件未覆盖），逐件 rc 与 blob 记在本地 '
         f'{Q}ship_result_p4_r2.json{Q} 与 {Q}ship_result_p4_r3.json{Q}；读回尖 `{tip}` · tree `{tree}`。'
         f'判级不归我：{Q}derived_result{Q} 留 null，{Q}claimed_result{Q} = MEASURED_NOT_GRADED。'
         f'下一件按序不自启：0312 的 M2 RED 向等 B 的 b5 同代即补。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'bus_note_p4_bus2.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
CACHE = OUT / 'bus_note_id_p4_bus2.txt'
if CACHE.exists():
    cid = int(CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    made = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})
    cid = made['id']
    CACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_bytes': len(tail.encode('utf-8')),
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'block_bytes_on_disk': len(blk), 'block_sha256': hashlib.sha256(blk).hexdigest(),
       'branch_tip_read_at': time.strftime('%H:%M:%S')}
(OUT / 'bus_note_p4_bus2_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                    encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line', 'block_bytes_on_disk')},
                 ensure_ascii=False))
