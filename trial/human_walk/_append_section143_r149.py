"""Append ledger section 14.3 -- the fixture repair, with its before/after pair, and what the rest looks like."""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "\u7559\u4f5c\u4e0b\u4e00\u6b65" not in text:
    sys.exit("ABORT the §14.2 tail this section follows is not in the report")
if "### 14.3" in text:
    sys.exit("ABORT section 14.3 already exists")
lines = [
    "",
    "### 14.3 最大那一块红拆开了：夹具漏签名头，改一行多绿二十四枚",
    "",
    "`tests/test_r64_member_side_quest.py` 那 52 枚不是 live provider 的事。现读第一枚的栈：夹具",
    "`_active_shared_journey()` 在 `:113-118` 给 `plans/select` 带了 `_auth(traveler_id)`，到 `:120` 的",
    "`journeys/{id}/start` 却**一个头都不带**，于是 `401 Unauthorized` 卡在每枚臂真正要断言的事情之前。",
    "把那一处补成同一个签名（`trial/human_walk/_fix_r64_start_header_r148.py` 只改这一处，改前先数、",
    "改后立刻再数，两个数都印出来）：",
    "",
    "    BEFORE  52 failed, 7 passed in 5.53s",
    "    AFTER   28 failed, 31 passed in 15.92s",
    "",
    "同一条命令、同一个解释器（`pytest -q tests/test_r64_member_side_quest.py --tb=no -p no:warnings`，",
    "python 3.12.14）—— 多绿二十四枚，产品文件零改动。",
    "",
    "剩下 28 枚的第一枚现读是另一类东西：`tests/test_r64_member_side_quest.py:338` 断言",
    "`rendezvous.time_state == \"AVAILABLE\"`，实读 `'PAST'` —— 夹具里的时间点会随墙钟过期，属刀三那族",
    "「过期断言」，不是鉴权、也不是产品。逐枚把这一类挑出来重画是下一步；**整套 255 那个总数没有重跑，",
    "所以不推算它会降到多少**，只报这一枚文件实测的 52→28。",
    "",
]
io.open(PATH, "w", encoding="utf-8", newline="").write(text + nl.join(lines) + nl)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_143_COUNT", after.count("### 14.3"))
print("TAIL", repr(after[-24:]))
