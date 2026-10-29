"""Append section 14.12: two guard reds resolved by the product's own scanner and its own metadata.

CRLF-dominant report, so the block is written with explicit CRLF and the run asserts that every byte
before the insertion point is untouched.
"""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.12（10-29 上午）：护壁句里剩下那两枚「两头都可能」的，用产品自己的扫描器与产品自己的表元数据判掉了。

- 「回执不落库」那一枚（`backend/tests/test_qoder_ord0332_error_receipt.py:207`）：现读 ORM 元数据里一共九十三张表，
  名字含 `receipt` 的三张（`trial/results/20261026_gozero/bw206-two-guard-resolutions.txt:20`）全部来自别的特征
  —— `collective_authority_receipts`（`backend/app/db/models.py:1664`）、
  `journey_rendezvous_buddy_execution_receipts`（`backend/app/db/models.py:2665`）、
  `member_live_moment_scout_receipts`（`backend/app/db/models.py:364`）；而名字里带 `error_receipt` 的表读数为零
  （`trial/results/20261026_gozero/bw206-two-guard-resolutions.txt:27`），代码里出现 `error_receipt` 的只有两处
  （`trial/results/20261026_gozero/bw206-two-guard-resolutions.txt:24`：`backend/app/error_receipt.py` 与
  `backend/app/main.py` 的日志出口）。⇒ 「设计已变」这一头排掉；红的成因是那条 `LIKE '%receipt%'` 太宽，
  把三张与错误回执无关的表也数了进去。修法（收窄成具名表断言，或改成断言 `error_receipt` 那张表不存在）等点单。
- 凭据门那一枚（`backend/tests/test_qoder_ord0307_credential_gate.py:187`）：直接把产品自己的扫描器叫起来扫一遍现读树
  （`backend/app/security/credential_literals.py`）—— 产物路径内的凭证字面量读数为零，
  但产物路径之外有十三枚 e2e 规格带着**未申报**的凭证形字面量，文件名逐枚在
  `trial/results/20261026_gozero/bw206-two-guard-resolutions.txt:6` 往下（计数行 `:5`，扫描器原话 `:4`）。
  ⇒ 套件里 conftest 会把 AI 键摘掉（`env_present` 读数零，见 `trial/results/20261026_gozero/bw204-two-guards-long.txt:28`），
  护壁句要的是 `CREDENTIAL_GATE_CLEAR`，扫描器给的是 `CREDENTIAL_LITERAL_OUTSIDE_PRODUCT_PATH` —— 红就红在这十三枚未申报的形上；
  而在我这趟直接调用里 `env_present` 读数为 1，所以同一条扫描器给出第三种判词 `LIVE_CREDENTIAL_IN_ENVIRONMENT`（`:4`），
  这正说明该护壁句的读数依赖环境，不是产品事实。
- 本班这条量法自带一道自锁：尺 `trial/human_walk/_cmdr_two_guard_resolutions_r206.py` 先把环境里名字含
  `KEY`/`TOKEN`/`SECRET`/`PASSWORD` 的值全部收下来（`trial/human_walk/_cmdr_two_guard_resolutions_r206.py:26`、
  `trial/human_walk/_cmdr_two_guard_resolutions_r206.py:29`），落盘前拿整篇报告逐一对拍，
  只要出现任何一枚就 ABORT、一个字都不写（`trial/human_walk/_cmdr_two_guard_resolutions_r206.py:89`）。
  现读这趟比对了五枚值，回执里只落文件名与指纹，不落任何键值 —— 「键只进进程、永不打印」从此不是我要小心的事，
  是写门不许它发生的事。
- 两枚的完整 traceback 留档在同尖现跑的回执 `trial/results/20261026_gozero/bw204-two-guards-long.txt:28` 与
  `trial/results/20261026_gozero/bw204-two-guards-long.txt:54`。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.12（10-29 上午）" in text:
        print("ABORT section 14.12 is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    hits = read_back.count("14.12（10-29 上午）")
    head_line = None
    for i, line in enumerate(read_back.splitlines(), 1):
        if line.startswith("14.12（10-29 上午）"):
            head_line = i
    print("APPENDED bytes_added=%d hits=%d section_head_line=%s"
          % (len(block.encode("utf-8")), hits, head_line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
