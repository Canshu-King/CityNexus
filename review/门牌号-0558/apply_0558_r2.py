"""门牌号 ORD-0558 r2 落笔仪表：pendingSetCopy.ts 第四枚（名词 stop，草稿第 80 行）。

与前一批同一扇门形制，但更硬一点：不再按行号定位，而是先在整枚文件里找「与草稿原文列逐字节相同」的那一行，
命中数必须正好一枚；命中零枚或多枚都 ABORT。改后行必须含 {plural: 标记。取词与英文全部从草稿列搬，不手打。
resolver 与 import 已在 r1 落过，本批只动这一行。
"""

from __future__ import annotations

from pathlib import Path

DRAFT = Path("D:/moodle/_cn8_plural_fix_0126.txt")
TARGET = Path("D:/moodle/_qoder_menpaaihao_0558/frontend/src/features/pending/pendingSetCopy.ts")
OUT = Path("D:/moodle/_qoder_menpaaihao_0558/review/门牌号-0558/apply_r2_readout_r1.txt")
DRAFT_ROW = 112  # 草稿里这枚文件第四行的物理行号

log: list[str] = []


def abort(why: str) -> None:
    log.append("ABORT " + why)
    OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(log))
    raise SystemExit(3)


fields = DRAFT.read_text(encoding="utf-8").split("\n")[DRAFT_ROW - 1].split(" | ")
if len(fields) < 7:
    abort(f"草稿第 {DRAFT_ROW} 行字段数不足")
coord, before, noun, tier, after, side = fields[1], fields[2], fields[3], fields[4], fields[5], fields[6]
if not coord.startswith("frontend/src/features/pending/pendingSetCopy.ts:"):
    abort(f"草稿第 {DRAFT_ROW} 行不是这枚文件：{coord}")
if "{plural:" not in after:
    abort("改后列不含标记")

raw = TARGET.read_bytes()
log.append(f"target_bytes={len(raw)} has_cr={raw.count(bytes([13]))}")
if bytes([13]) in raw:
    abort("这枚文件带 CRLF，本仪表只按 LF 落笔")

lines = TARGET.read_text(encoding="utf-8").split("\n")
hits = [i for i, one in enumerate(lines) if one == before]
log.append(f"found_by_content={len(hits)}")
if len(hits) != 1:
    abort(f"按内容命中 {len(hits)} 枚，必须正好一枚；原文：{before[:70]}")
index = hits[0]
if lines[index] == after:
    abort("这一行已经是改后形状，本批不该再落")
lines[index] = after
TARGET.write_text("\n".join(lines), encoding="utf-8", newline="\n")
log.append(
    f"OK 草稿行 {DRAFT_ROW}｜名词 {noun}｜档 {tier}｜侧 {side}\n"
    f"  落点现读 {index + 1}（草稿坐标写的是 {coord.rsplit(':', 1)[1]}，r1 那批顶过一格）\n"
    f"  改前 {before}\n  改后 {after}"
)
log.append(f"written_bytes={len(TARGET.read_bytes())}")
OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
print("\n".join(log))
raise SystemExit(0)
