import io, os, time

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

body = u"""### 6efab655 · 号令者实例 A · 勘误（不改上一块）：我在账本里引了一枚行号锚，它已经被我自己那次插入推走

- 上一块（块头「SYNTHETIC_DEFAULT 那格在现尖上再钉一次」）第一节里我写「现读在 `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:20751`」。那枚行号在我写下的那一刻是对的（`grep -n` 现取），但我随后在 17:42 又插了一枚块，账本整文件重写，同一句现在落在第 20789 行——**我自己就是那次漂移的制造者**。
- 正确读法（常设，对所有车道与两扇号令者）：账本里的锚只用**块头标题的名字形**，不用行号。要找那句判语，搜块头「四、SYNTHETIC_DEFAULT 那格再钉一次」；要找我的闭单件，看 `_processed/6efab655_1925.md.inserted_202426`（这枚文件名带插入时刻，不受重写影响，本轮现读存在）。
- 受影响的已发布读数：只有那一枚行号；第一节另外两枚坐标（`frontend/src/lib/displayVocabulary.ts:165` 与 `frontend/src/features/planning/PlanRankingPanel.tsx:144`）是源码锚，源码本轮一字未动，仍然可回读。判语本身不变：那格在现尖上是修好的，无字节可改。
- 这条不新起任何工作，也不改上一块任何字节：按常设，勘误另立一块，旧块原样留着。
"""

closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
