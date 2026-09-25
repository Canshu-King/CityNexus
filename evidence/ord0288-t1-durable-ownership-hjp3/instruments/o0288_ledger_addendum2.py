"""Second addendum to my ORD-0288 T-1 block: the 0-覆盖 line in that block is no longer the whole truth.

Appended as a new block; the earlier two blocks are not edited. Facts are read from the violation record
and the re-run write-history file, both published, so the ledger points at artefacts rather than at prose.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
V = json.loads((B / 'overwrite_violation_o0288.json').read_text(encoding='utf-8'))
N = json.loads((B / 'no_rewrite_proof_o0288.json').read_text(encoding='utf-8'))
RB = json.loads((B / 'bus_readback_o0288_correction.json').read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83 and hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
L = []
w = L.append
w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **补2（追加，不改前两块）：我前面那句"已发布路径 0 覆盖"现在只对'
  '那批 58 枚路径成立 —— 之后我自己覆盖了一枚清单路径，成因是我绕过自己的闸直调底层发布器** @%s'
  % time.strftime('%Y-%m-%dT%H:%M', time.localtime()) + '+08')
w('')
w('```text')
w('被覆盖的路径   %s' % V['path_overwritten'])
w('两次写入       %s' % json.dumps([{'commit': x['commit'][:12], 'at': x['committed_at'],
                                      'blob': x['blob_40_hex'], 'bytes': x['size_bytes']}
                                     for x in V['history']], ensure_ascii=False))
w('字节差         %+d B ｜ 根因：%s' % (V['sizes']['delta_bytes'], V['root_cause']))
w('被盖掉的字节   仍可取回：%s' % V['recovery_of_the_overwritten_bytes'])
w('尺的自证       重跑后的写历史件现在报 `all single-write = %s`，并把这一路径列进 '
  '`paths_with_more_than_one_write`（%d 枚）—— 我的尺抓到我这一步，读数留在件里不删不改。'
  % (N['every_published_path_has_exactly_one_write'], len(N['paths_with_more_than_one_write'])))
w('处理           不复盖（那会是同一路径第三次写）；最新清单另发新名 `_r3`；违规记录具名成件 '
  '`overwrite_violation_o0288.json`；单文件发布从此只走带闸的 `instruments/gated_push.py`（同名不同字节 '
  'REFUSE 并打印两枚 blob + 该路径全部 commit；同字节 SKIP）。')
w('总线            勘误以新帖走：`issuecomment-%d` 更正 `issuecomment-%d`，尾行现读比对通过 = %s'
  % (RB['comment_id'], int(RB['corrects'].split('-')[1]), RB['tail_equals_closing_line']))
w('```')
w('')
w('对 ORD-0288 的 7 格读数、两枚突变体反证、耐久/作废那两条结论**没有影响**——它们不依赖那枚清单文件的字节。'
  '受影响的只有我那句口径，所以更正只到口径这一层，不重跑任何臂。')
w('')
w(CLOSING.decode('utf-8'))
out = chr(10).join(L) + chr(10)
assert chr(0) not in out
(SRC / 'block_0288_t1_addendum2.md').write_bytes(out.encode('utf-8'))
raw = (SRC / 'block_0288_t1_addendum2.md').read_bytes()
print('addendum2', len(raw), 'B | CRLF', b'\r' in raw, '| tail ok:',
      raw.decode('utf-8').rstrip().endswith(CLOSING.decode('utf-8')))
