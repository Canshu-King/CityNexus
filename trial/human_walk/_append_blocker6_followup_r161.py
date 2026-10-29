"""Add the dated blocker 6 follow-up line under the same 'keep the old sentence' rule as r157."""

import io
import sys

DOC = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"

ANCHOR = "blocker 6 那十五枚另说：逐条对表仍是 9／5／1，一条未变、未上膛成产品缺陷。"

NEW_LINE = (
    "    **10-29 晨补二（报告 §14.6）**：这十五枚也归到成因了，数没变、成因第一次落地"
    "（仪表 `trial/human_walk/_cmdr_blocker6_attribution_r159.py`，回执"
    "`trial/results/20261026_gozero/bv159-blocker6-attribution.txt`，末行 `15 failed, 12 passed in 6.08s`）："
    "九枚属 §14.5 那族**私有读不带 bearer**（backend/tests/test_sol_concurrency_and_remap.py:1005）；"
    "五枚属**假 settings 少一个字段**——夹具只给 `live_valhalla_url`"
    "（backend/tests/test_qoder_live_replans_endpoint.py:65），而产品侧要读 `settings.live_valhalla_test_provider`"
    "（app/integrations/mobility/runtime.py:174），真配置本来就有这一项（app/core/config.py:62）；"
    "一枚属**过期的十二字段清单**：`_replan_payload` 现发十六个顶层键（app/main.py:22294），"
    "清单停在十二个（backend/tests/test_dsh_list_replans_bound.py:28），多出的四个是 "
    "`recovery_epoch_id`、`source_agent_run_id`、`semantic_identity`、`canonical_proposal_id`，"
    "而失败消息只打 `FULL_FIELDS - set(item)`，把一次形制增长读成空差异 —— 这把尺单向，要双向才看得见。"
    "三处都在测试面、产品字节零改动；「十二字段契约」这句话要不要跟着换代牵涉对旅客的合同表述，仍等点单。"
)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(DOC, encoding="utf-8", newline="").read()
    if "10-29 晨补二（报告 §14.6）" in text:
        print("ABORT the follow-up line already exists")
        return 4
    if text.count(ANCHOR) != 1:
        print("ABORT anchor hits=%d" % text.count(ANCHOR))
        return 5
    if "\r\n" in text:
        print("ABORT this doc is not LF-only")
        return 6
    io.open(DOC, "w", encoding="utf-8", newline="").write(
        text.replace(ANCHOR, ANCHOR + "\n" + NEW_LINE, 1)
    )
    read_back = io.open(DOC, encoding="utf-8", newline="").read()
    print("INSERTED hits=%d anchor_still_1=%s size=%d->%d" % (
        read_back.count("10-29 晨补二（报告 §14.6）"),
        read_back.count(ANCHOR) == 1,
        len(text),
        len(read_back),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
