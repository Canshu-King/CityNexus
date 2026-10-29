"""Append a dated morning update to the delivery document.

Three of the delivery doc's "what was not done" lines went stale during this shift -- the whole
backend suite now has a generation certificate, and the unexplained-red bucket is empty.  The old
lines are kept verbatim; the update is a separate dated section, with LF preserved because this
document is LF-only (checked by byte count before writing, asserted after).
"""

import io
import sys

DOC = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"

BLOCK = """
10-29 上午补（这一节取代上面「没做的事」里第一条的旧说法；其余各条照旧有效，旧行照留、不改写）

一、后端整套不再是「本档没有重跑」：现尖那一套已经跑过并留了逐行日志，末行读数在
`trial/results/20261026_gozero/bw163-backend-full-tbline.txt:566`；整套红的成因表在报告 §14.10
（`trial/results/20261026_GO_FROM_BLANK_REPORT.md:3213`）、九枚护壁句逐枚点名在 §14.11
（`trial/results/20261026_GO_FROM_BLANK_REPORT.md:3249`）、两枚含糊判词的现读结论在 §14.12
（`trial/results/20261026_GO_FROM_BLANK_REPORT.md:3278`）。「未定性」那一桶现在读数为零。

二、主人按平板的落点已定档：课堂树 `E:/_cmdr_clean_1028` 停在 `88b891d22c`（porcelain 现读零行），
vite 交出的 `WorkspaceActions.tsx` 带来源披露串（`trial/results/20261026_gozero/bz187-stack-generation.txt:5`），
停在旧代的那只 vite 不带（`trial/results/20261026_gozero/bz187-stack-generation.txt:6`）；两只后端健康读数都是
`status=ok`（`trial/results/20261026_gozero/bz187-stack-generation.txt:7`）。代次要现读，别信文档里的静态值 ——
这条自锁写在交接件 `trial/results/20261029_HANDOFF_GO_FROM_BLANK_r185.md:60`。

三、新量出来、等点单的四条修单（本班一条没自取）：`backend/tests/test_qoder_ord0332_error_receipt.py:207` 那条
`LIKE '%receipt%'` 太宽（名字带 error_receipt 的表现读为零，`trial/results/20261026_gozero/bw206-two-guard-resolutions.txt:27`）；
两处真出网调用在 `backend/tests/test_qoder_catalog_hydration.py:609` 与 `backend/tests/test_qoder_provider_identity.py:363`；
生成客户端落后契约六枚 operationId（`trial/results/20261026_gozero/bw201-contract-client-gap.txt:6`，逐字名单在同文件往下）；
两条基线型护壁句 `backend/tests/test_qoder_ord0402_recycle_bin.py:160`、`backend/tests/test_qoder_ord0434_share_grants.py:238`
究「门动过」还是「基线该重登记」。

四、仍然没变好的，照直说：课堂随机城市池仍 0/3，这一格要有高德键才能现测，本班没代跑；「费用：未知」仍等甲/乙裁语；
账本往 GitHub 的镜像腿仍未推（多 MB 件的共享可见写，等主人点头）；平板 `USER_VERIFIED` 仍空 —— 那是主人亲自按的一格，
本班只把落点、代次与点击路径摆好，不代判。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raw = io.open(DOC, "rb").read()
    if raw.count(b"\r\n"):
        print("ABORT this document is not LF-only, the appender would change its shape")
        return 4
    text = raw.decode("utf-8")
    if "10-29 上午补" in text:
        print("ABORT the morning update is already appended")
        return 5
    block = BLOCK.strip("\n") + "\n"
    io.open(DOC, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(DOC, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 6
    if read_back.count("\r\n"):
        print("ABORT the write introduced CRLF")
        return 7
    print("APPENDED bytes_added=%d hits=%d lines_now=%d"
          % (len(block.encode("utf-8")), read_back.count("10-29 上午补"),
             len(read_back.splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
