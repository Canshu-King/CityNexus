"""Append section 14.16: the fake-settings reds as an executable five-attribute repair table.

Each row pairs the attribute the product tried to read with the test that produced the crash, joined
by order from pytest's own line-traceback output and gated on both lists matching pytest's failed
count.  CRLF-dominant report: explicit CRLF plus the byte-identity assertion.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.16（10-29 上午）：「假设置缺字段」那一族十六枚，摊成一张能直接下刀的表（五枚属性、九枚测试文件）。

- 拼法与闸：`--tb=line` 的崩溃行与 `FAILED` 摘要行按执行顺序一一对应，本尺要求两串都等于 pytest 自报的那枚数
  （`trial/results/20261026_gozero/bw226-fake-settings-table.txt:3` 记这条已验），十六枚与普查表同码
  （`trial/results/20261026_gozero/bw226-fake-settings-table.txt:4`），另有「解析不出属性名就丢行并报尺自己的缺陷」那一支，
  本趟现读丢零枚（`:5`）。逐枚 node id 与产品帧在 `trial/results/20261026_gozero/bw226-fake-settings-table.txt:6` 往下。
- 五个属性各自的刀口：

| 缺的属性 | 产品在哪读 | 红在哪些测试（枚数） |
| --- | --- | --- |
| `live_valhalla_test_provider` | `backend/app/integrations/mobility/runtime.py:174` | `tests/test_qoder_live_replans_endpoint.py`（五枚）、`tests/test_qoder_live_hard_fallback.py`（两枚）、`tests/test_rx2_mock_hard_laundering_gate.py`（两枚） |
| `traveler_id` | `backend/app/agent/goal_artifacts.py:33` | `tests/test_bootstrap_photon_draft_exploration.py`（两枚）、`tests/test_r102_shared_city_outing.py`（一枚） |
| `objective_codes_json` | `backend/app/agent/runtime.py:454` 与 `backend/app/agent/gateway.py:683` | `tests/test_r21_autonomous_future_synthesis.py`（一枚）、`tests/test_r26_decision_critical_clarification.py`（一枚） |
| `intent_kind` | `backend/app/agent/journey_intent.py:391` | `tests/test_journey_intent.py`（一枚） |
| `simulation_enabled` | `backend/app/main.py:28442` | `tests/test_in_transit_reroute.py`（一枚） |

- 这张表的意义在于它把「十六枚红」换成「五枚属性、九枚文件里各加一个字段」——一刀能全罩，不必逐枚试。
  `live_valhalla_test_provider` 一枚就罩住九枚，而这一枚正是 blocker 6 里那五枚（`test_qoder_live_replans_endpoint.py`）的同一根因：
  夹具的 SimpleNamespace 没跟上产品新增的设置名。
- 本班没自取这一刀：改的是夹具不是产品，且与 #345/#346/#351 同属「夹具侧」一族，建议一起裁一次，省得四轮返工。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.16（10-29 上午）" in text:
        print("ABORT section 14.16 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.16（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.16（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
