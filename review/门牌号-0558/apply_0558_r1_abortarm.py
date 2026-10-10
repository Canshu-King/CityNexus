"""门牌号 ORD-0558 落笔仪表：pendingSetCopy.ts 的三处 B 档文案 + 配套 import + 配套 resolver。

规矩装在这扇门里：每枚目标行都要先从号令者盖章的草稿（_cn8_plural_fix_0126.txt）里按行号取出「原文」与
「改后」两列，再与现读那一行逐字节比；任一枚不相等、或改后整行不含 {plural: 标记（resolver 那枚不含
expandPluralMarkers），就 ABORT 且一个字节都不落。文案不是我手打的，是从草稿列里搬的。
"""

from __future__ import annotations

import sys
from pathlib import Path

DRAFT = Path("D:/moodle/_cn8_plural_fix_0126.txt")
TARGET = Path("D:/moodle/_qoder_menpaaihao_0558/frontend/src/features/pending/pendingSetCopy.ts")
OUT = Path("D:/moodle/_qoder_menpaaihao_0558/review/门牌号-0558/apply_abortarm_readout_r1.txt")

# 草稿第 2 节里属于这枚文件的三行（行号是草稿文件的物理行），字段以 " | " 分隔
DRAFT_ROWS = (109, 110, 111)
# 草稿第 4 节里这枚文件的 resolver 那行
DRAFT_RESOLVER = 319
# 草稿第 3 节里这枚文件的 import 那行
DRAFT_IMPORT = 298

log: list[str] = []


def abort(why: str) -> None:
    log.append("ABORT " + why)
    OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(log))
    raise SystemExit(3)


draft_lines = DRAFT.read_text(encoding="utf-8").split("\n")
target_lines = TARGET.read_text(encoding="utf-8").split("\n")
raw_bytes = TARGET.read_bytes()
log.append(f"target_bytes={len(raw_bytes)} has_cr={b'\r' in raw_bytes}")
if b"\r" in raw_bytes:
    abort("这枚文件带 CRLF，本仪表只按 LF 落笔")

edits: list[tuple[int, str, str, str]] = []
for row_no in DRAFT_ROWS:
    fields = draft_lines[row_no - 1].split(" | ")
    if len(fields) < 7:
        abort(f"草稿第 {row_no} 行字段数不足")
    coord, before, noun, tier, after, side = fields[1], fields[2], fields[3], fields[4], fields[5], fields[6]
    if not coord.startswith("frontend/src/features/pending/pendingSetCopy.ts:"):
        abort(f"草稿第 {row_no} 行不是这枚文件的坐标：{coord}")
    _, line_no = coord.rsplit(":", 1)
    index = int(line_no) - 1
    if target_lines[index] != before:
        abort(f"第 {row_no} 行原文与现读不符\n  草稿：{before}\n  现读：{target_lines[index]}")
    if "{plural:" not in after:
        abort(f"第 {row_no} 行改后列不含标记")
    edits.append((index, before, after, f"草稿行 {row_no}｜名词 {noun}｜档 {tier}｜侧 {side}"))

# 配套 resolver（草稿第 4 节：坐标 | 原文 | 改后）
res_fields = draft_lines[DRAFT_RESOLVER - 1].split(" | ")
res_coord, res_before, res_cell = res_fields[0], res_fields[1], res_fields[2]
if not res_cell.startswith("改后"):
    abort(f"resolver 那格的改后列形状不对：{res_cell[:24]}")
# 草稿那一格把代码自己的两格缩进连同「改后」分隔空格一起吃掉了；缩进按原文列补回，语义字节仍照草稿。
res_indent = res_before[: len(res_before) - len(res_before.lstrip(" "))]
if not res_indent:
    abort("原文列没有缩进，补形无法判定")
res_after = res_indent + res_cell[len("改后"):].strip()
if not res_coord.endswith(":179") or "pendingSetCopy.ts" not in res_coord:
    abort(f"resolver 那行坐标不对：{res_coord}")
res_index = 178
if target_lines[res_index] != res_before:
    abort(f"resolver 原文与现读不符\n  草稿：{res_before}\n  现读：{target_lines[res_index]}")
if "expandPluralMarkers(" not in res_after:
    abort("resolver 改后列不含 expandPluralMarkers")
edits.append((res_index, res_before, res_after, "配套 resolver（草稿第 4 节）"))

# 配套 import（草稿第 3 节：文件 -> import 行   锚点 路径:行 | 插在其前：<原文>）
imp_src = draft_lines[DRAFT_IMPORT - 1]
imp_line = imp_src.split(" -> ", 1)[1].split("   锚点", 1)[0].strip()
imp_anchor = imp_src.split("锚点 ", 1)[1].split(" | 插在其前：", 1)[0]
imp_at = int(imp_anchor.rsplit(":", 1)[1]) - 1
if "expandPluralMarkers" not in imp_line:
    abort("import 那行不含 expandPluralMarkers")
if target_lines[imp_at] != "export const pendingSetCopy = {":
    abort(f"import 锚点现读不是那句 export：{target_lines[imp_at]}")
if any("from \"../../lib/plural\"" in line for line in target_lines):
    abort("这枚文件已经有 plural 的 import 了")

# 全部现读都过了，才落笔：先换文案与 resolver，再在锚点前插 import
for index, before, after, tag in edits:
    target_lines[index] = after
    log.append(f"OK {tag}\n  改前 {index + 1}: {before}\n  改后 {index + 1}: {after}")
target_lines.insert(imp_at, imp_line)
log.append(f"OK 配套 import\n  插入 {imp_at + 1}: {imp_line}")

new_text = "\n".join(target_lines)
TARGET.write_text(new_text, encoding="utf-8", newline="\n")
log.append(f"written_bytes={len(new_text.encode('utf-8'))}")
OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
print("\n".join(log))
raise SystemExit(0)
