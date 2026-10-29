"""Insert blocker 13 into the delivery: the whole-suite red set now has a classified ledger, not just a count."""
import io

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261027_GO_FROM_BLANK_DELIVERY.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
anchor = "## 8. 纯净树上的账"
if text.count(anchor) != 1:
    raise SystemExit("ABORT section 8 anchor hits=%d" % text.count(anchor))
if "13. 整套后端红不再只是一个总数" in text:
    raise SystemExit("ABORT blocker 13 already present")
block = nl.join([
    "13. 整套后端红不再只是一个总数：本班在现尖跑完并落盘证书",
    "    （`trial/results/20261029_BACKEND_CERTIFICATE_24a342198d.md`，分母 2828、末行原样、五项相加等于分母），",
    "    并把最大那一块拆开归因（报告 §14.3–§14.4）：`tests/test_r64_member_side_quest.py` 原 52 枚红里，",
    "    夹具 `_active_shared_journey()` 给 `plans/select` 带了签名头、给同函数下一行的 `journeys/{id}/start`",
    "    **一个头都没带** ⇒ 每枚臂在真正断言之前就吃 `401`。补上那一处签名后实测 **52 failed → 28 failed、",
    "    7 passed → 31 passed**（同一命令同一解释器，改前改后各数一次；产品文件零改动）。剩下 28 枚按成因",
    "    现读分类：`CHECK constraint failed: end_at > start_at` 21 枚、`LIVE_MOMENT_SCOUT_RENDEZVOUS_TIME_PASSED`",
    "    4 枚、`time_state 'PAST'` 1 枚、`KeyError: 'active_plan'` 2 枚 —— 四类相加正好 28（生成脚本硬要求）。",
    "    前 26 枚是刀三那族「过期断言」：demo 种子行程的时刻与夹具写入的 now 谁跟着谁没定过口径，",
    "    **这条口径我不自取**（它影响所有共用 demo 重置的臂）；后 2 枚是另一类，未挖。",
    "    blocker 6 那十五枚另说：逐条对表仍是 9／5／1，一条未变、未上膛成产品缺陷。",
    "",
]) 
io.open(PATH, "w", encoding="utf-8", newline="").write(text.replace(anchor, block + anchor, 1))
after = io.open(PATH, encoding="utf-8", newline="").read()
print("INSERTED", "13. 整套后端红不再只是一个总数" in after, "SECTION8_KEPT", after.count(anchor) == 1)
print("BYTES", len(after.encode("utf-8")))
