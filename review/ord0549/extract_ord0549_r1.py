"""Extract the ORD-0549 table from the ledger into machine-readable rows.

The row shape the commander publishes is:

  `frontend/src/x/Y.tsx` —— 5 枚
  - 第 42 行：中文「行前清单」／英文「Pre-trip checklist」→ 键 `detail.pretripAria`（zh `path:行`，en `path:行`）

Line numbers in that table are signposts against the tip the commander verified, so the extraction keeps
them but the inventory run below locates each pair by content, not by the quoted line number.
"""

from __future__ import annotations

import io
import json
import re

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
OUT = "D:/moodle/_qoder_lane_heyuegong_20261009/ord0549_rows.json"

FILE_HEAD = re.compile(r"^`(frontend/[^`]+)`\s*——\s*(\d+) 枚")
ROW = re.compile(
    r"^- 第 (\d+) 行：中文「(.+?)」／英文「(.+?)」→ 键 `([^`]+)`"
    r"（zh `([^`:]+):(\d+)`，en `([^`:]+):(\d+)`）"
)

lines = io.open(LEDGER, encoding="utf-8", newline="").read().split("\n")
rows: list[dict] = []
current_file = None
for index, line in enumerate(lines):
    head = FILE_HEAD.match(line)
    if head:
        current_file = head.group(1)
        continue
    match = ROW.match(line)
    if match and current_file:
        rows.append(
            {
                "ledger_line": index + 1,
                "file": current_file,
                "signpost_line": int(match.group(1)),
                "zh_text": match.group(2),
                "en_text": match.group(3),
                "key": match.group(4),
                "zh_ref": f"{match.group(5)}:{match.group(6)}",
                "en_ref": f"{match.group(7)}:{match.group(8)}",
            }
        )

io.open(OUT, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
by_file: dict[str, int] = {}
for row in rows:
    by_file[row["file"]] = by_file.get(row["file"], 0) + 1
print(f"rows_extracted={len(rows)} files={len(by_file)}")
for name, count in sorted(by_file.items(), key=lambda item: -item[1]):
    print(f"  {count}  {name}")
