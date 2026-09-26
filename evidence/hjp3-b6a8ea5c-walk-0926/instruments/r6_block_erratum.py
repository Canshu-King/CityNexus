"""Erratum block for aad2d1f2_1817.md: one line of the heading named the wrong generation.

What was wrong: the heading of the delivered block read 「(27f963a7… that generation)」 because it interpolated
the mirror tip I had just re-read for the drift section. The five cells were NOT walked on that tip - they were
walked on the one the commander named (`b6a8ea5c…`) against the bundle the chain served then
(`/assets/index-BOIAHTWw.js`). The four-tuple inside the block says this correctly; the heading could still send a
dispatcher to grade the wrong generation, so it gets corrected.

Applied blocks are immutable, so this is a new block, and nothing in the old one is rewritten or deleted. Counts
that were not on the block when it was applied are added here (they were measured after it): the write counter over
the finished prefix and the coordinate pre-flight over the block itself. The gate is run before delivery and the
closing line is read from file.
"""
import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
GATE = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4d.py')
PFX = 'evidence/hjp3-b6a8ea5c-walk-0926'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

tip = pub.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if e.get('type') == 'blob'}
B = lambda n: tree[PFX + '/' + n]
applied = sorted(INBOX.glob('_processed/aad2d1f2_1817.md.inserted_*'))
assert applied, 'the block I am correcting is not in _processed'
applied_path = applied[0]
PRF = json.loads((OUT / 'ledger_inbox_proof_r6.json').read_text(encoding='utf-8'))
WL = json.loads((OUT / 'write_ledger_r6b.json').read_text(encoding='utf-8'))
HX = json.loads((OUT / 'hex_preflight_r6.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r6_walked_asset_witness.json').read_text(encoding='utf-8'))
applied_text = applied_path.read_text(encoding='utf-8')
head_line = [l for l in applied_text.splitlines() if l.startswith('### ')][0]
ledger_lines = [i for i, l in enumerate(
    pathlib.Path('D:/moodle/CITYNEXUS_AGENT_CONTROL.md').read_text(encoding='utf-8').splitlines(), 1)
    if l.startswith('### ') and 'SESSION=aad2d1f2' in l and l[:64] == head_line[:64]]

stamp = time.strftime('%H%M')
cache = OUT / 'r6_erratum_block_name.txt'
name = cache.read_text(encoding='utf-8').strip() if cache.exists() else 'aad2d1f2_' + stamp + '.md'
cache.write_text(name, encoding='utf-8', newline='\n')

BODY = f"""### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **勘误：上一块标题里那枚代次指错了 —— 我走的是 {WA['asset_path_recorded_by_the_browser_passes']} 那一代，不是漂移现尖那一代；旧块一字不改** @{time.strftime('%H:%M')}+08

```text
was / now（只改标题的指代，正文一字不动）：
· was = 已插入那一块的标题行现在长这样：`{head_line[:96]}…`，全文在 `{applied_path.name}`（{applied_path.stat().st_size} B，落在账本第 {ledger_lines} 行）
· now = 本批五格读数走的代次 = 号令者点名的 b6a8ea5c625d7e3e82f7348fad57d595a8a403c0，链上当时服务的 bundle = `{WA['asset_path_recorded_by_the_browser_passes']}`，字节与 sha256 由每趟浏览器记下的名字回读钉住（见证件 blob {B('r6_walked_asset_witness.json')}，字段 `re_read_over_the_local_hop`）；`27f963a77edc4d508a39b0a07c76927d0512c724` 是我在该块⑥里报的「镜子漂移现尖」，不是我走的那一代（漂移件 blob {B('r6_drift.json')}，字段 `named_by_the_commander` 与 `tip_read_now` 各归各）
· 为什么会被指错：标题那格我插的是「评分时读到的现尖」，而不是「走路那代」——我的插值取错了字段，这一格以后按 `named_by_the_commander` 写（评分件里两条字段都在，blob {B('r6_readings_scored.json')}）

补三条旧块应用之后才量到、当时不在块上的事实：
· 本前缀写入计数：{WL['files_under_prefix']} 枚路径，每枚都只有一笔提交 = {all(v == 1 for v in WL['commits_per_path'].values())}，三枚已知双发的反控各读到 {WL['controls_known_to_hold_two_writes'][0]['commits']} 笔（件 blob {B('write_ledger_r6b.json')}）；中间那次 409 乐观并发拒投没有落笔，两轮日志也上架了（blob {B('ship_result_r6.json')} 与 {B('ship_result_r6b.json')}）
· 旧块里每一枚 40 位都取得回来：{HX['hexes_found']} 枚全部解析为 blob 或 commit（预飞件 blob {B('hex_preflight_r6.json')}）
· 旧块自己的 Q43 r4d 原判：rc {PRF['q43_rc']}、claims {json.loads(PRF['q43_out'].split('claims checked ')[1].split(' ')[0])}、findings {json.loads(PRF['q43_out'].split('findings ')[1].split(' ')[0])}（回执件 blob {B('ledger_inbox_proof_r6_q43r4d.json')}）；本块同样自跑现行门，回执随后按新名上架

总线那条续帖的编号是 issuecomment-5845469270，里面 generation 一格写的就是 b6a8ea5c625d7e3e82f7348fad57d595a8a403c0，与上面 now 一致，无需改帖。

**纪律**：旧块一字不改、不删、不覆盖；产品字节 0 改；权威线 0 写；ref 0 推别人的；链上四层一行没动；本块只纠正我自己那一格指代。
```

坐标（写时从分支 tree 现读，写时尖 {tip}）：见证件 `{PFX}/r6_walked_asset_witness.json` {B('r6_walked_asset_witness.json')} · 评分件 `{PFX}/r6_readings_scored.json` {B('r6_readings_scored.json')} · 漂移件 `{PFX}/r6_drift.json` {B('r6_drift.json')} · 写入计数 `{PFX}/write_ledger_r6b.json` {B('write_ledger_r6b.json')} · 坐标预飞 `{PFX}/hex_preflight_r6.json` {B('hex_preflight_r6.json')} · 旧块回执 `{PFX}/ledger_inbox_proof_r6_q43r4d.json` {B('ledger_inbox_proof_r6_q43r4d.json')} · 两轮发布日志 `{PFX}/ship_result_r6.json` {B('ship_result_r6.json')} 与 `{PFX}/ship_result_r6b.json` {B('ship_result_r6b.json')} · 本块构建件 `{PFX}/instruments/r6_block_erratum.py`（名字在此，blob 在本块之后按新名上架）。

"""
text = BODY + CLOSING.read_text(encoding='utf-8').strip() + '\n'
path = INBOX / name
path.write_text(text, encoding='utf-8', newline='\n')
rb = subprocess.run(['python', str(GATE), '--text', str(path), '--out', str(OUT / 'r6_erratum_gate_r4d.txt'),
                     '--expect-clean'], capture_output=True, text=True, encoding='utf-8', errors='replace')
receipt = {'block_file': str(path), 'bytes': path.stat().st_size, 'gate': GATE.name, 'q43_rc': rb.returncode,
           'q43_out': rb.stdout, 'q43_err': rb.stderr, 'corrects': applied_path.name,
           'generation_walked': 'b6a8ea5c625d7e3e82f7348fad57d595a8a403c0',
           'mirror_tip_at_this_write': '27f963a77edc4d508a39b0a07c76927d0512c724',
           'branch_tip_at_block_write': tip, 'ledger_written_by_this_lane': False}
(OUT / 'ledger_inbox_proof_r6_erratum.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1),
                                                        encoding='utf-8', newline='\n')
print(json.dumps({'block': name, 'bytes': receipt['bytes'], 'rc': rb.returncode}, ensure_ascii=False))
print(rb.stdout[-1500:])
print('ERR:', rb.stderr[-300:])
