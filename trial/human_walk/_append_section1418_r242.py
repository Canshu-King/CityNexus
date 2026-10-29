"""Append section 14.18: the eight validation reds name one required field, and the contract is silent about it.

CRLF-dominant report: explicit CRLF block and the byte-identity assertion before writing.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.18（10-29 上午）：那八枚「答复被验口拒绝」不再是谜 —— 缺的是同一枚必填字段，而契约对它一言不发。

- 现读 traceback：八枚的 422 体里都写着同一句 `{"loc": ["body", "consented_provider"], "msg": "Field required", "type": "missing"}`；
  该字段在 `backend/app/schemas.py:356` 声明为必填（`Literal["overpass", "photon"]`，无默认值）。
  那八枚测试送的是没有这枚字段的旧体形 ⇒ 与 #352 同族（夹具侧过期），不是屏上会踩的坑。
- 旅客侧先排掉：同一个字串在前端三处有读者（`frontend/src/features/discovery/BootstrapDiscoveryPanel.tsx:960`、
  `frontend/src/trial/RevolutionQuickExplore.tsx:631`、类型声明 `frontend/src/api/citynexus.ts:3708`），
  逐枚出现次数现读各为一（尺 `trial/human_walk/_cmdr_contract_field_gap_r241.py`、回执
  `trial/results/20261026_gozero/bw241-contract-field-gap.txt:22` 往下）⇒ 这一门对真人是通的。
- 契约侧另有一格要报：同一把尺把该请求模型的十二枚字段逐个对契约点名
  （`trial/results/20261026_gozero/bw241-contract-field-gap.txt:4` 往下），结论是**六枚没进契约**，
  其中两枚还是必填 —— `source_kind`（`backend/app/schemas.py:354`）与 `consented_provider`
  （`backend/app/schemas.py:356`）；汇总行 `trial/results/20261026_gozero/bw241-contract-field-gap.txt:25`
  现读必填缺席为二。⇒ 生成的客户端与契约都不能描述这扇门真正收什么，与 §14.11 那「六枚 operationId 没读者」是同一处漏。
- 顺手记一枚可能是产品自己的不一致（等裁，不自取）：同一模型里并排站着 `provider_consent`（可空布尔，
  `backend/app/schemas.py:355`）与 `consented_provider`（必填枚举，`backend/app/schemas.py:356`）——
  两枚同意语义并存，一枚可有可无、一枚非此即彼；要不要合成一枚、以及旧字段留不留由号令者定。
- 本班零产品字节、零测试改动：这一节只把 422 体原文、三处读者与十二枚字段的对契约点名摆出来。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.18（10-29 上午）" in text:
        print("ABORT section 14.18 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.18（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d line=%s" % (len(block.encode("utf-8")), head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
