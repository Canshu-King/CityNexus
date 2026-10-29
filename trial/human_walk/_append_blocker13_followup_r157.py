"""Insert the dated follow-up line under blocker 13 instead of rewriting the stale claim.

The previous line said the two KeyError reds were 'another class, unexplored'.  They are now
explored, so the correction is added as its own line and the original sentence stays readable as
what was known at that moment.
"""

import io
import sys

DOC = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"

ANCHOR = "后 2 枚是另一类，未挖。"

NEW_LINE = (
    "    **10-29 晨补（报告 §14.5）**：那 2 枚已挖到底，且这一族比 2 大。一把现读四枚文件"
    "（`tests/test_r64_member_side_quest.py`、`tests/stateful/test_journey_truth_state_machine.py`、"
    "`tests/test_provider_runtime_gate.py`、`tests/test_qoder_activity_identity_contract.py`）末行"
    "`42 failed, 42 passed in 14.21s`；观察探针 `trial/human_walk/_cmdr_unsigned_experience_probe_r155.py`"
    "包 `TestClient.get`，只记状态与 body 顶层键，不改请求、不改响应、不改产品字节；回执"
    "`trial/results/20261026_gozero/bu155-unsigned-experience-probe.txt`）：套件里 44 次私有读"
    "（`/experience` 34 次、`/events` 10 次）**一次带凭证的都没有**，全部 `401`，body 顶层只有 `error`。"
    "同一条腿里的分辨对照：`/experience` 不带 bearer ⇒ `401 body_keys=['error']`，带 ⇒ `200` 且 `active_plan` 在"
    "（id 见回执）；`/events` 不带 ⇒ `401` 的 dict，逐一遍历拿到的是 `str`（正是 stateful 那 10 枚"
    "`AttributeError: 'str' object has no attribute 'get'` 的成因），带 ⇒ `200` 的 list。"
    "所以这 16 枚（r64 2＋activity 身份契约 2＋provider 运行时门 2＋stateful 10）是同一族**夹具裸读**，"
    "不是契约改名、不是产品少发键（`active_plan` 由 `app/stay_mobility.py:2052` 无条件发出，"
    "挡人的 `app/main.py:10323` 拒得对）。16＋26＝42 与本次末行对齐。修法要给这些读补 bearer，"
    "而 stateful 整枚模块没有签名臂，属具名的夹具改动；**这一刀仍不自取**（超出刀三划下的范围）。"
)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(DOC, encoding="utf-8", newline="").read()
    if "10-29 晨补（报告 §14.5）" in text:
        print("ABORT the follow-up line is already in the delivery doc")
        return 4
    if text.count(ANCHOR) != 1:
        print("ABORT anchor hits=%d, expected exactly 1" % text.count(ANCHOR))
        return 5
    if "\r\n" in text:
        print("ABORT this doc is not LF-only; refusing to mix endings")
        return 6
    updated = text.replace(ANCHOR, ANCHOR + "\n" + NEW_LINE, 1)
    io.open(DOC, "w", encoding="utf-8", newline="").write(updated)
    read_back = io.open(DOC, encoding="utf-8", newline="").read()
    print("INSERTED chars_added=%d size=%d->%d hits=%d anchor_still_1=%s" % (
        len(NEW_LINE) + 1,
        len(text),
        len(read_back),
        read_back.count("10-29 晨补（报告 §14.5）"),
        read_back.count(ANCHOR) == 1,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
