"""门牌号 · ORD-0558 r3 落笔仪表：catalogueReadback.ts 那枚 A 档（英文面一处）＋配套 import。

形制沿用我这扇前两批那扇门，只把定位换成按内容：先在整枚文件里找「与草稿原文列逐字节相同」的那一行，
命中数必须正好一枚；改后列必须含 englishCountNoun；import 那行若已存在就 ABORT（说明别人已配套）。
文案不是我手打的，是从号令者盖章的草稿列里搬的。
"""

from __future__ import annotations

from pathlib import Path

DRAFT = Path("D:/moodle/_cn8_plural_fix_0126.txt")
TARGET = Path("D:/moodle/_qoder_menpaaihao_0558/frontend/src/features/planning/catalogueReadback.ts")
OUT = Path("D:/moodle/_qoder_menpaaihao_0558/review/门牌号-0558/apply_r3_readout_r1.txt")
DRAFT_ROW = 263          # 草稿第 185 行：这枚文件唯一那枚 A 档
DRAFT_IMPORT_ROW = 312   # 草稿第 3 节里这枚文件的 import 行

log: list[str] = []


def abort(why: str) -> None:
    log.append("ABORT " + why)
    OUT.write_text(chr(10).join(log) + chr(10), encoding="utf-8", newline=chr(10))
    print(chr(10).join(log))
    raise SystemExit(3)


fields = DRAFT.read_text(encoding="utf-8").split(chr(10))[DRAFT_ROW - 1].split(" | ")
if len(fields) < 7:
    abort(f"草稿第 {DRAFT_ROW} 行字段数不足")
coord, before, noun, tier, after, side = fields[1], fields[2], fields[3], fields[4], fields[5], fields[6]
if "catalogueReadback.ts" not in coord:
    abort(f"草稿第 {DRAFT_ROW} 行不是这枚文件：{coord}")
if "englishCountNoun" not in after:
    abort("改后列不含尺")

raw = TARGET.read_bytes()
log.append(f"target_bytes={len(raw)} cr_count={raw.count(bytes([13]))}")
if bytes([13]) in raw:
    abort("该文件带 CRLF，本仪表只按 LF 落笔")
lines = raw.decode("utf-8").split(chr(10))

imp_src = DRAFT.read_text(encoding="utf-8").split(chr(10))[DRAFT_IMPORT_ROW - 1]
imp_line = imp_src.split(" -> ", 1)[1].split("   锚点", 1)[0].strip()
imp_anchor_line = imp_src.split("锚点 ", 1)[1].split(" | 插在其前：", 1)[1].strip()
if "englishCountNoun" not in imp_line:
    abort("import 那行不含 englishCountNoun")
if any(imp_line == l for l in lines):
    abort("这枚文件已经带那行 import 了")

hits = [i for i, one in enumerate(lines) if one == before]
log.append(f"found_by_content={len(hits)}")
if len(hits) != 1:
    abort(f"按内容命中 {len(hits)} 枚，必须正好一枚；原文前 60 字：{before[:60]}")

anchor_hits = [i for i, one in enumerate(lines) if one.strip() == imp_anchor_line]
if len(anchor_hits) != 1:
    abort(f"import 锚点按内容命中 {len(anchor_hits)} 枚")

index = hits[0]
lines[index] = after
lines.insert(anchor_hits[0], imp_line)
log.append(
    f"OK 草稿行 {DRAFT_ROW}｜名词 {noun}｜档 {tier}｜侧 {side}\n"
    f"  改前 {index + 1}: {before}\n"
    f"  改后 {index + 2}: {after}\n"
    f"  import 插入 {anchor_hits[0] + 1}: {imp_line}"
)
new_text = chr(10).join(lines)
TARGET.write_text(new_text, encoding="utf-8", newline=chr(10))
log.append(f"written_bytes={len(new_text.encode('utf-8'))}")
OUT.write_text(chr(10).join(log) + chr(10), encoding="utf-8", newline=chr(10))
print(chr(10).join(log))
raise SystemExit(0)
