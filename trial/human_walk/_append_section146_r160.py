"""Append section 14.6: blocker 6's fifteen reds stop being a bare count.

Same shape as the 14.5 append: CRLF block, refuses to run twice, and proves the bytes before the
insertion point are untouched.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
### 14.6 blocker 6 那十五枚也归到成因：九枚是同一族裸读、五枚是假 settings 少一个字段、一枚是过期的十二字段清单

跑法（现读，仪表 trial/human_walk/_cmdr_blocker6_attribution_r159.py 把三件事一次做完：跑测试、按栈尾行
分组、再从源码取真形制）：`python -m pytest -q tests/test_sol_concurrency_and_remap.py
tests/test_qoder_live_replans_endpoint.py tests/test_dsh_list_replans_bound.py --tb=line -p no:warnings`，
解释器 3.12.14、代次 `228e8db50ab8dafac035b367efcc57a4e2323c3c`，末行 `15 failed, 12 passed in 6.08s`、
退出码 `1`、栈尾记录十五条；分组与解析都写在
trial/results/20261026_gozero/bv159-blocker6-attribution.txt。

| 成因 | 分组数 | 栈尾与真形制的坐标 |
| --- | --- | --- |
| 私有读不带 bearer（§14.5 那一族） | 9 | backend/tests/test_sol_concurrency_and_remap.py:1005 |
| 假 settings 只带 `live_valhalla_url`，被产品侧新字段咬住 | 5 | backend/tests/test_qoder_live_replans_endpoint.py:65 |
| 测试里的「完整形制」清单停在十二个字段 | 1 | backend/tests/test_dsh_list_replans_bound.py:124 |

第二类的两头都摊开：读的一侧是 app/integrations/mobility/runtime.py:174 要 `settings.live_valhalla_test_provider`，
而真配置对象本来就有这一项（app/core/config.py:62），是夹具用 SimpleNamespace 造的替身少给了它 ——
所以这不是产品缺字段，也不是配置没读到，是替身跟不上形制。

第三类用 AST 从源码取数：`_replan_payload` 现在发十六个顶层键（app/main.py:22294 起），测试那份清单
（backend/tests/test_dsh_list_replans_bound.py:28 起）只有十二个，多出四个且一个不缺：
`recovery_epoch_id`、`source_agent_run_id`、`semantic_identity`、`canonical_proposal_id`
（回执里各带自己的 main.py 行）。也就是说「十二字段契约」这句话在屏外已经不成立，而失败消息打的是
`FULL_FIELDS - set(item)`，永远显示 `[]` —— 这把尺只会说「少了什么」，不会说「多了什么」，
所以它把一次形制增长读成了空差异。要收这一格得两头一起改：清单跟上十六，并把断言换成双向差异。

三类相加正好十五，与末行的 15 failed 对齐。三处都在测试面，产品字节零改动；改哪几处、
「十二字段契约」这句话要不要跟着换代，仍等点单（它牵涉对旅客的合同表述，不属本班自取）。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    original = io.open(REPORT, encoding="utf-8", newline="").read()
    if "### 14.6" in original:
        print("ABORT 14.6 is already in the report")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(original + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(original):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED 14.6 bytes_added=%d heading_hits=%d" % (
        len(block.encode("utf-8")),
        read_back.count("### 14.6"),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
