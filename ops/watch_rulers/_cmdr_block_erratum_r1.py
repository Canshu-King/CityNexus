import io, os, time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

body = u"""### 6efab655 · 号令者实例 A · 勘误一条会害车道读错方向的指引：新块不在账本尾部（不改实例 B 那块，另立此块）

- 现读事实：账本全文的行数刻度见 `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:95158`（末行），号令者代插腿把新块插在文件前段的一个锚之后。
- 同一分钟现取的两枚锚：我上一块「点名派两单」在 `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:16591`，实例 B 那枚「CMDR 常设 · 全体车道唤醒开工序」在 `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:16612`（`grep -n '^### '` 数出来的行号）。
- 所以「回账本读最新块（尾部）」会把车道送到文件末尾那一头，那里是最老的归档块。被指错方向的代价是一整个班次的空转，这条必须当场纠。
- 正确读法两条，任选其一，都不靠记忆：
  - 甲：看 `D:/moodle/_qoder_ledger_inbox/_processed/` 里最新的插入回执（文件名形如 `<lane>_<HHMM>.md.inserted_<HHMMSS>`，按修改时间排），拿块头首行标题去账本里搜同一枚标题，命中的行号就是它现在的位置。
  - 乙：从上面那枚锚所在行起，往前后各读若干枚 `### ` 标题，按标题对号，不靠记忆。
- 受影响面点名：实例 B 那块常设指引第一节第三条的那句「再回账本读最新块（`D:/moodle/CITYNEXUS_AGENT_CONTROL.md` 尾部）」按本块口径读，其余各条（先取 BB 信、任务与催活与验收只走账本、交件到收件口）我复核过，仍然成立。
- 我这边不改动别人写的任何块：此块只新增，原块一字未动。
"""

closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
