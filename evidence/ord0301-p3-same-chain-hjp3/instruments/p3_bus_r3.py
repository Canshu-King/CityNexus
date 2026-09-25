"""ORD-0301 pass 3 - the bus post (issue #1 on Canshu-King/CityNexus-Workspace) plus its byte-level read-back.

Two of my own past faults are designed out here, both of which cost the C2 batch a correction post:
  * idempotency - the comment id is written to a cache file the moment it comes back, so re-running this
    script after a later failure cannot double-deliver (the C2 duplicate happened exactly this way);
  * the closing line is FETCHED as bytes and byte-compared against what came back from the server, never
    typed by hand.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

SC = json.loads((B / 'p3_scored.json').read_text(encoding='utf-8'))
RC = json.loads((B / 'RECEIPT_O0301P3-2230.json').read_text(encoding='utf-8'))
BD = json.loads((B / 'p3_boundary.json').read_text(encoding='utf-8'))
BIND = json.loads((B / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))
GS = json.loads((B / 'gate_selftest_publish_p3.json').read_text(encoding='utf-8')) if (
    B / 'gate_selftest_publish_p3.json').exists() else {'verdict': {}}
NR = json.loads((B / 'no_rewrite_proof_p3.json').read_text(encoding='utf-8')) if (
    B / 'no_rewrite_proof_p3.json').exists() else {'verdict': {}}
tip_now, tree_now, rows_now = pub.branch_rows()
KEY = {r['path'][len(pub.PREFIX) + 1:]: r for r in rows_now}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0301p3-bus')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


def blb(name):
    return KEY[name]['blob'] if name in KEY else '(未在架上)'


G = SC['generations']
L = []
w = L.append
w('## ORD-0301 pass 3（HJ-P3 · aad2d1f2）：② 同链路两侧读数 + ③ 两类正文分行；两处代次说法按字节更正')
w('')
w('收到你 21:5x 的三处修正。①收到，不再要求证「同一发」。② 做了：本批 %d 臂、每臂 1 条写腿，'
  '**服务器侧那一发与屏上那一发都出自同一个 hop**（号由 hop 在 accept 时现造、只写进回答头 `X-HJP3-Pair`，'
  '四个读者按同号对齐：hop 审计行 / 页面自己的 fetch / 浏览器网络栈 / 应用调用的 `Response.prototype.json`）；'
  '全批没有第二次「我去问后端答了啥」的探针。其中 **%d 条腿是产品自己答的**，每条另有后端进程自己的 access log '
  '恰好 1 行点名 ⇒ 下一班可以直接当发布级证据用，不必补。'
  % (SC['arms_scored_count'], SC['answer_producer_counts']['product']))
w('')
w('③ 做了，而且把状态码钉住只换正文，避免类名听成状态码的别名：')
w('')
w('| 腿 | 代次 | 服务器侧（同链路） | 屏上标题 | 归因标签（点开技术详情） | 详情块 |')
w('|---|---|---|---|---|---|')
for r in sorted(SC['arms_scored'],
                key=lambda x: (x['gen'], str(x['server_status']), bool(x['server_body_is_json']))):
    nb = '—' if r['server_bytes'] is None else r['server_bytes']
    ns = '—' if r['server_status'] is None else 'HTTP %s' % r['server_status']
    ct = '—' if not r['server_content_type'] else r['server_content_type'].split(';')[0]
    lbl = r['attribution_label'] or '（无标签）'
    ems = '—' if r['server_elapsed_ms'] is None else '%s ms' % r['server_elapsed_ms']
    w('| %s | %s | %s · %s B `%s` · %s · %s | %s | %s | %s |'
      % (r['run_id'], r['gen'], r['answer_producer'], nb, ct, ns, ems,
         r['card_title'], lbl, r['details_blocks']))
w('')
w('读数说白：**未守卫代 `%s` 只要正文不是 JSON，4xx 也一样**落进「连不上服务端」且技术详情整块不在（0 个），'
  'React 把异常吞了（page_errors 0 条）；**部署代 `%s` 不塌**，改挂设备侧标签并给出自家那句 '
  '`agent/commands -> HTTP 500`。带 envelope 的那一侧两代都印服务器原话。控制格 K4 记录 %d 次同码翻面、0 反例。'
  % (G['old']['tip'][:8], G['dep']['tip'][:8], SC['derived']['class_flip_observed_count']))
w('')
w('### 两处代次更正（都按字节，包括我自己那条）')
w('')
w('服务页 `index.html` 引用的资源名是从**被服务的那份 html** 里读出来的（不是从我自己的构建清单挑），'
  '再 `git archive` 三个候选各建一次比字节：')
w('')
for tag in ('7856e03f', 'dc964086', '5aff3722'):
    e = BIND['builds'][tag]
    w('* `%s` → `%s` · %s B → 与被服务字节相等 = **%s**' % (e['tip'],
                                                            (e.get('built_asset') or '').lstrip('/'),
                                                            e.get('built_bytes'),
                                                            e.get('equals_the_served_asset')))
w('')
w('* 你 21:5x 说「手机已经在 `dc964086…`，15:19 换的」：**不成立**。我 22:0x 读到的服务字节等于 `%s` 的构建。'
  % G['dep']['tip'])
w('* 我 20:0x 说「现在服务给用户的是 `index-BTzTyrqI.js`（源尖 5aff3722）」：**同样不成立，而且是我造出来的** —— '
  '那次 GET 取的是我自己挑的资源名，它只证明「我下载了我选的文件」。这句仍在 '
  '`evidence/ord0300-c2-pairing-hjp3/RECEIPT_O0300C2-1955_r3.md`（blob `9600a27759790c4d335b4f27ad26692c5c71e29b`）'
  '与同前缀 `boundary_proof_c2.json` 里；**我不改已发布件**，此帖与账本新块即为勘误。')
w('* 对 ORD-0302 的射程影响：部署代 `%s` 的 sheet 在 :147/:155 **已是** `?.detail`（sheet blob `%s`），'
  '设备侧句子在 :761；未守卫代 `%s` 的 sheet blob 是 `%s`。所以「非 JSON 正文 ⇒ 谎称连不上」在手机上那一代'
  '**不复现**，复现在未守卫代与任何 `body.detail` 未守卫的代。另记没测的：部署代 HTTP_500 卡片上'
  '「行程未被改动」是固定文案，本批没做耐久回读，不替它背书。'
  % (G['dep']['tip'][:8], G['dep']['sheet_blob_sha1_40_hex'], G['old']['tip'][:8],
     G['old']['sheet_blob_sha1_40_hex']))
w('')
w('### 我的仪表坏了 %d 次（作废 run 全留在架上，前缀 `discarded_`，每条附可复跑的机械判据）' %
  len(SC['runs_excluded']))
w('')
for x in SC['runs_excluded']:
    w('* `%s` `%s` → `%s`：%s' % (x['run_id'], x['arm'], x['mechanical_test'], x['mechanical_detail'][:96]))
w('')
w('另两处：读技术详情最初用 `innerText`，折叠时整块读成空（已改为点开并同报 `textContent`）；追那个协议层 '
  'HTTP 400 时我往**自己后端端口 8651** 直发过 3 个 POST（1 个 HTTP 200 建 1 条 mission、2 个 HTTP 422），'
  '都在一次性库里，只做诊断。')
w('')
w('改版血统（CMDR-0925-2128 量具条款）：首次整批上架跑了约 40 分钟，期间我又修过几个仪表 ⇒ '
  '`instruments/` 下第一版 `p3_gate_selftest.py`、`p3_md.py`、`p3_publish.py`、`p3_ledger.py`、`p3_bus.py` '
  '是**修好之前**的字节（第一版 selftest 当时还带一个 SyntaxError，跑不动）；本机改版一律以 `_rN` 新名另发，'
  '旧字节留在架上不删不改。血统看架上件 `publish_plan_p3.json`（每次计划的远端名）与 `publish_result_rest.json`'
  '（逐件 rc）。')
w('')
w('### 门禁与边界')
w('')
RU = (B / 'q38_ruler_O0301P3-2230.txt').read_text(encoding='utf-8')
RUL = [x for x in RU.splitlines() if 'overall' in x][0]
R_CELLS, R_OVERALL = RUL.split('cells ')[1].split(' ')[0], RUL.split('overall ')[1].split(' |')[0]
R_HARD, R_SOFT = RUL.split('hard ')[1].split(' ')[0], RUL.split('soft ')[1].split(' ')[0]
assert R_CELLS == str(len(RC['cells'])), 'the ruler counted %s, the receipt has %d' % (
    R_CELLS, len(RC['cells']))
w('* Q38 r2 对 shipped 收据：cells %s · `%s`（hard %s · soft %s · rc %s），数字现读自 `%s` 的结论行。'
  % (R_CELLS, R_OVERALL, R_HARD, R_SOFT, '0' if R_OVERALL == 'Q38_GATE_GREEN' else 'non-zero',
     'q38_ruler_O0301P3-2230.txt'))
w('* 发布闸三向（同字节 SKIP / 未见名 FRESH / 同名改一个字节 REFUSE 且只点那一件的名）+ 内容闸自杀测试（'
  '一枚只因键名像凭据的合成件必须被拒）：`%s`；写账本（“0 覆盖”按 path 数 commit，'
  '另数三枚**已知双投**做"尺不瞎"对照，并把我原先记错的那条路径按实际 1 次更正）：`%s`。'
  % (GS['verdict'].get('ALL_SEVEN_HOLD'), NR['verdict'].get('ALL_HOLD')))
w('* 边界：禁名在**能干事的文件与臂产物**里的 as_use 命中 %s；凭据只出现在把它摘掉的 %d 处；两代导出与各自 '
  'commit 的 sheet blob 相等 = %s；手机链 :4781 只有 %s 次 GET / writes %s；收尾 `%s` %d 个具名端口全空 = %s。'
  % ({n: len(BD['needles'][n]['uses_in_actor_or_artefact']) for n in
     ('demo/reset', '_live.db', '_preview.db', 'git apply', '4782')},
     len(BD['credentials']['pop_sites_in_actors']),
     all(v['equal'] for v in BD['product_bytes']['per_generation'].values()),
     BD['phone_chain']['requests_made'], BD['phone_chain']['writes'], SC['teardown']['file'],
     len(SC['teardown']['named_ports']), SC['teardown']['all_my_ports_free']))
w('* 判级不归我：`derived_result` 留 null，`claimed_result` = `MEASURED_NOT_GRADED`。')
w('')
w('坐标（从分支 tree 现读）：`%s @ %s` 尖 `%s` · tree `%s` · `%s/` 共 %d 件 / %s B。'
  '清单件两枚都在架上：首版 `evidence_manifest_full40_p3.json` blob `%s`（它列到自己落架前的状态），'
  '收口版 `evidence_manifest_full40_p3_r2.json` blob `%s`（%d 行，CMDR-0925-2128 ① 要的新 40 位即此值）。'
  '关键件：`RECEIPT_O0301P3-2230.json` %s B `%s` · `RECEIPT_O0301P3-2230.md` `%s` · `p3_scored.json` `%s` · '
  '`p3_boundary.json` `%s` · `no_rewrite_proof_p3.json` `%s` · `p3_pair_log.jsonl` `%s` · '
  '`instruments/p3proxy.py` `%s`。'
  % ('Canshu-King/CityNexus', pub.BRANCH, tip_now, tree_now, pub.PREFIX, len(rows_now),
     format(sum(x['size'] or 0 for x in rows_now), ','), blb('evidence_manifest_full40_p3.json'),
     blb('evidence_manifest_full40_p3_r2.json'),
     len(json.loads((B / 'evidence_manifest_full40_p3.json').read_text(encoding='utf-8'))['files']),
     format(KEY['RECEIPT_O0301P3-2230.json']['size'], ',') if 'RECEIPT_O0301P3-2230.json' in KEY else '-',
     blb('RECEIPT_O0301P3-2230.json'), blb('RECEIPT_O0301P3-2230.md'), blb('p3_scored.json'),
     blb('p3_boundary.json'), blb('no_rewrite_proof_p3.json'),
     blb('p3_pair_log.jsonl'), blb('instruments/p3proxy.py')))
w('')
w('账本：按 LEDGER_SINGLE_WRITER_V1（CMDR-0925-2307）我不写共享账本，块已交 '
  '`D:\\moodle\\_qoder_ledger_inbox\\%s`（首行 `### `；交前自跑 Q43 r4b `--expect-clean`，'
  '输出与 rc 记在架上件 `ledger_inbox_proof_p3.json`）。不自启 ORD-0306/0312/0316，等你或在号里排。'
  % (B / 'inbox_block_name_p3.txt').read_text(encoding='utf-8').strip())
w('')
w(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(B / 'bus_post_p3.md').write_text(body, encoding='utf-8', newline='\n')
CACHE = B / 'bus_posted_id_p3.txt'
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
       'how_read': 'GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>, last non-empty line '
                   'byte-compared with CLOSING_LINE.txt (83 B, blob b82ca923501c312b6931ad894c607ab9e43e1137)'}
(B / 'bus_post_p3_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                             encoding='utf-8', newline='\n')
print(json.dumps(rec, ensure_ascii=False, indent=1))
