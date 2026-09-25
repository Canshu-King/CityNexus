"""A short ADDENDUM to my own ORD-0288 T-1 ledger block - appended, never a rewrite of what I inserted.

Two facts arrived after that block went in: the authoritative tip moved again (so every number in my
block needs its generation pinned out loud), and ORD-0310's requirement 4 names a control I did not run.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
RC = json.loads((B / 'RECEIPT_O0288T1-1730.json').read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137', 'closing line authority changed'
NOREW = json.loads((B / 'no_rewrite_proof_o0288.json').read_text(encoding='utf-8'))
NOREW_COUNT = len(NOREW['blobs'])
NOREW_TIP = NOREW['tip_read']
import re as _re
_c = _re.search(r'共 ([\d,]+) 件', (B / 'coords_line_o0288_delivery.txt').read_text(encoding='utf-8'))
COORD_COUNT = int(_c.group(1).replace(',', ''))
TIP_REMOTE = subprocess.run(['git', 'ls-remote', 'origin',
                             'refs/heads/mirror/integration-frontend-apple-pass1'],
                            cwd='D:/moodle/CityNexus', capture_output=True, text=True,
                            encoding='utf-8', errors='replace').stdout.split()[0]
LED = io.open if False else None
L = []
w = L.append
w('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **补：上面那块 ORD-0288 T-1 的两条口径（追加，不重写那块）** '
  '@%s' % time.strftime('%Y-%m-%dT%H:%M', time.localtime()) + '+08')
w('')
w('1) **换代已经又走了一步**：我刚外读到 `refs/heads/mirror/integration-frontend-apple-pass1` = '
  '`%s`（%s 本机时刻），而那块里所有读数钉在 `%s` 上（`measured_on` / `frozen_tip` 都是它）。我没有拿新尖'
  '重跑任何一臂，也不替新尖签任何字——要在新尖上补测哪几格，点名即可，同一把尺我随时开。'
  % (TIP_REMOTE, time.strftime('%H:%M+08', time.localtime()), RC['measured_on']))
w('2) **ORD-0310 要件 4 的第三条本批没测，别拿我这块去交那份账**：那一条要的是**根本不发 `Idempotency-Key` '
  '那一形**（`idempotency_keys` 行数 from→to 具名报数）。我这批做的是**非法键**（值 `x`）在抢占之前被路由'
  '拒掉、0 行 —— 两形不是一回事，我不用后者冒充前者；而且按 Q54 的字，ORD-0310 排在 ORD-0306 之后，'
  '我不自启第三战线。缺的就是这一条，写在这里，不在那块里补。')
w('3) **件数对账（免得两块数字看起来打架）**：那块里"0 覆盖"那条写的是写历史件 `%s` 读到的 %d 枚路径各 1 '
  '次写入；而交付坐标那行（同一把尺、更晚现读）已经是 %d 枚 blob —— 差的 %d 枚是**那把尺跑完之后**才落架的'
  '两枚控制件（写历史件自己 + 清单 r2）。写历史件里逐枚记了它当时读到的尖 `%s`，所以两个数各自都有名，'
  '不是一个数被改过。'
  % ('no_rewrite_proof_o0288.json', NOREW_COUNT, COORD_COUNT, COORD_COUNT - NOREW_COUNT, NOREW_TIP))
w('')
w('（本块只追加这三条；那 %s B 的读数、闸、坐标、自曝 8 条都在上面那块和架上的件里。）'
  % format(len((B / 'RECEIPT_O0288T1-1730.md').read_bytes()), ','))
w('')
w(CLOSING.decode('utf-8'))
out = chr(10).join(L) + chr(10)
assert chr(0) not in out
(SRC / 'block_0288_t1_addendum.md').write_bytes(out.encode('utf-8'))
raw = (SRC / 'block_0288_t1_addendum.md').read_bytes()
print('addendum', len(raw), 'B | CRLF', b'\r' in raw, '| sha256', hashlib.sha256(raw).hexdigest())
print('tail ok:', raw.decode('utf-8').rstrip().endswith(CLOSING.decode('utf-8')))
