"""Bus note for the same-generation re-run: ORD-0312's discriminating cells now belong to the serving bundle.

The re-point note said M3 was PARTIAL because my nine cells predated the cutover. They no longer do. This post
carries what changed, what the arms actually said on the new generation and on a private unguarded mutant of that
same commit, the one run I excluded and the mechanical test that caught it, and the single cell still owed.
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
R4 = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
P312 = 'evidence/ord0312-target-generation-reread'
RS = json.loads((R4 / 'r4_scored.json').read_text(encoding='utf-8'))
PROOF = json.loads((OUT / 'ledger_inbox_proof_p4.json').read_text(encoding='utf-8'))
G2 = json.loads((OUT / 'ord0312_m3_binding_reread_gen2.json').read_text(encoding='utf-8'))
BI = json.loads((OUT / 'ord0312_gen2_build_equals_served.json').read_text(encoding='utf-8'))
tip, tree, _r = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
bl = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
Q = chr(96)
SC = RS['cells']
J = RS['judgments']
B = RS['bundles']
NE = RS['named_code_emitters_on_this_commit']
EX = RS['runs_excluded'][0]
blk = pathlib.Path(PROOF['block_file']).read_bytes()
SCORE = P312 + '/ord0312_rerun_on_new_generation_scored_r2.json'
BIID = P312 + '/ord0312_gen2_build_equals_served.json'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-p4-bus4')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


L = []
L.append('## ORD-0312 九臂已在 serving 的那一代次重跑完：红向现在是同代产生的，不再是借旧包；十项判据全真 · '
         'HJ-P3 aad2d1f2（续 issuecomment-5838568315，那条的 PARTIAL 由本条收掉）')
L.append('')
L.append(f'四元组：**scope** = 带键写腿答复到达与否在屏幕上的归属，按正文类别分格；**generation** = '
         f'{Q}{RS["generation"]}{Q}；**artifact** = 下面每条 40 位；**method** = 与 pass-3 同一张臂表（定义一字'
         f'未改）、同一把 rig、同一个配对跳板，每臂一次一次性库 + 我自己的私有面，真 Chromium 读渲染文字与点开'
         f'后的技术详情，服务器侧取跳板自己为同一请求写的审计行（pair_id 一对一）。')
L.append('')
L.append(f'**① 三方字节同一（先把「同代」钉死）**')
L.append(f'· 我私有 outDir 构建该尖 = {B["deployed_guarded"]["asset"]} / {B["deployed_guarded"]["bytes"]} B = '
         f'链上此刻服务的字节（等值 {B["deployed_guarded"]["equals_what_the_phone_chain_serves"]}）= 你探针件那一行；'
         f'比较件 `{BIID}` blob `{bl(BIID)}`（含 {len(BI["comparisons"])} 条比较）。')
L.append(f'· 同代红向 = 私有副本里只删两处守卫后的构建 {B["private_unguarded_mutant_of_the_same_commit"]["asset"]} / '
         f'{B["private_unguarded_mutant_of_the_same_commit"]["bytes"]} B，两枚产物字节不同 = {B["the_two_bundles_differ"]}；'
         f'突变体事实件 `{P312}/gen2_same_generation_unguarded_mutant_facts.json` blob '
         f'`{bl(P312 + "/gen2_same_generation_unguarded_mutant_facts.json")}`。')
L.append('')
L.append(f'**② 九臂读数（{RS["arms_scored"]} 臂全在这一代次，十项判据全真 = {RS["verdict"]["ALL_JUDGMENTS_HOLD"]}）**')
L.append(f'· 同码不同类分得开：422 那一对 = {J["same_status_different_class_422"]}，500 那一对 = '
         f'{J["same_status_different_class_500"]}；渲染出的标签跟着正文类别走而不是跟着状态码走 = '
         f'{J["the_painted_label_tracks_the_body_class_not_the_status"]}。')
L.append(f'· 守卫一撤：只有非 JSON 那两臂掉成「连不上服务端」（{SC["old_hoplock"]["screen_side"]["card_status painted"]} / '
         f'{SC["old_nonjson_422"]["screen_side"]["card_status painted"]}），而跳板记到的状态码仍是 '
         f'{SC["old_hoplock"]["server_side"]["http_status"]} 与 {SC["old_nonjson_422"]["server_side"]["http_status"]}；'
         f'JSON envelope 那两臂仍说对（{SC["old_product"]["screen_side"]["card_status painted"]} / '
         f'{SC["old_json_500"]["screen_side"]["card_status painted"]}）= '
         f'{J["the_guard_flip_changes_attribution_only_for_non_json_bodies"]}。')
L.append(f'· 负控：根本没到跳板那一臂渲染出与红向同一张卡 = '
         f'{J["the_NETWORK_card_is_not_an_arrival_witness"]} ⇒ 卡片不证明到达，只有配对证明；每一臂 pair_id 一对一 = '
         f'{J["every_swept_arm_is_paired_by_one_request_one_id"]}；同臂重复一次一致 = {J["the_repeat_agrees"]}。')
L.append(f'· 我排除的那一次是被机械判据抓住的（{J["the_excluded_run_is_caught_by_a_mechanical_test"]}）：'
         f'{EX["run_id"]} 配对腿 {EX["paired_legs_recorded"]} 条、屏幕字段 {EX["screen_fields_null"]}/'
         f'{EX["screen_fields_read"]} 全空、种子文本点名缺 {EX["seed_named_path"]} ⇒ 根因是我导出目录集少了 '
         f'data/ 与 contracts/（这条我踩过一次又踩第二次，已写进量具的断言：缺就不跑）。')
L.append(f'· 暴露面：上架的只有 {"/".join(RS["whitelist_proof"]["fields_allowed"])} 这一组字段，正文片段按字段名丢掉；'
         f'拿被丢掉的片段回扫存活字符串 = {len(RS["whitelist_proof"]["fragments_still_present"])} 处，正控会命中 = '
         f'{RS["whitelist_proof"]["positive_control"]["test_fired_on_the_scratch_string"]}；逐臂原始文件因此留本地不上架。')
L.append('')
L.append(f'**③ 仍欠的一格与不归我定的一件事**')
L.append(f'· M2 的 RED 向 = NOT-MEASURED：这一代确实有具名码可发（backend/app/main.py:1668 与 '
         f'backend/app/main.py:1694 两枚 V13_DISCOVERY_*，同文件 reason_code 出现 {NE["reason_code_lines"]} 行；'
         f'「服务器回的原因编号是 …」那一支在 PlanWithAiSheet.tsx:218），但本批没有一条臂从用户路径真产出带码答复。')
L.append('· 相关且不属于我：那个槽里填的 X 是产品自有码还是服务端原话被截断大写，属 Q64 还开着的口径（E 的 AST 尺'
         '在查这一形）。我不替它定，也不拿它当 M2 已闭的证据。')
L.append(f'· 账本块已同步改到这一代次：`{PROOF["block_file"]}` 现 {len(blk)} B，Q43 r4b {Q}--expect-clean{Q} 自跑 '
         f'rc = {PROOF["q43_rc"]}，原判行 {Q}{[x for x in PROOF["q43_out"].splitlines() if "claims checked" in x][0].strip()}{Q}；'
         f'标题里那句 PARTIAL 已按本条改口为「九臂已在这一代重跑」，改口依据就是上面那十项。')
L.append(f'· 坐标：读数件 `{SCORE}` blob `{bl(SCORE)}`；打分量具 `{P312}/instruments/r4_score.py` blob '
         f'`{bl(P312 + "/instruments/r4_score.py")}`；被重新指的 rig 与臂表 `{P312}/instruments/r4_rig.py` blob '
         f'`{bl(P312 + "/instruments/r4_rig.py")}` / `{P312}/instruments/r4_arms.py` blob '
         f'`{bl(P312 + "/instruments/r4_arms.py")}`；导出与两份构建事实 '
         f'`{P312}/gen2_export_and_bundle_facts.json` blob `{bl(P312 + "/gen2_export_and_bundle_facts.json")}`。')
L.append('')
L.append(f'端口收尾：我这批自用端口（后端与两面孔）现在无监听；判级不归我：{Q}derived_result{Q} 仍 null，'
         f'{Q}claimed_result{Q} = MEASURED_NOT_GRADED。读回尖 `{tip}` · tree `{tree}`。ORD-0316 按你的次序在 0312 '
         f'之后，我这边下一格是等你对 M2 RED 向的口径（要我造带码答复就得给可发的具名码路径）。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'bus_note_p4_bus4.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
CACHE = OUT / 'bus_note_id_p4_bus4.txt'
if CACHE.exists():
    cid = int(CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    cid = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})['id']
    CACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'corrects': 5838568315,
       'created_at': back['created_at'], 'body_bytes': len(back['body'].encode('utf-8')),
       'remote_equals_local': back['body'] == body,
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'generation': RS['generation'], 'arms': RS['arms_scored'], 'block_bytes': len(blk),
       'branch_tip': tip, 'read_at': time.strftime('%H:%M:%S')}
(OUT / 'bus_note_p4_bus4_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                   encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
