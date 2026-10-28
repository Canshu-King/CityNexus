"""Append ledger section 13.9 -- the commit gate's self-test, witnessed outside this machine.

Same byte rules as r120/r126/r129.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "\u4ee5\u540e\u540c\u5f62\u5236\u7684\u81c2\u4e00\u5f8b\u968f\u4e00\u5f20\u4ee3\u6b21\u7968\u843d\u76d8" not in text:
    sys.exit("ABORT the §13.8 tail this section follows is not in the report")
if text.count("### 13.9") > 0:
    sys.exit("ABORT section 13.9 already exists")
lines = [
    "",
    "### 13.9 提交门的自测已在 runner 上跑出原话（外读证据，不只本机）",
    "",
    "`dc7b5e6d5d` 把那步装进发布门之后，连着两代（`4d5895d89e`、`4d1eee472a`）都跑到 success。真正要看的",
    "不是 job 的绿，而是那一步自己印了什么 —— 取自 runner 日志（`gh run view 40756205676 --log`，",
    "步号 7，时刻 `19:41:32`），四行原话落盘在 `trial/results/20261026_gozero/r130-ci-gate-step-proof.txt:10-13`：",
    "",
    "    ROOT_ARM True",
    "    COMMIT_PATHS 1 ['mine.txt']",
    "    FOREIGN_STAGED before=1 after=1",
    "    SELFTEST_OK control swept theirs.tsx into the commit; the gate committed only mine.txt, "
    "left theirs.tsx staged, and refused a path that is not in the tree",
    "",
    "小票里另写了**怎么证它不是空转**：末句前半就是对照组 —— 一枚不带 pathspec 的提交在临时仓库里确实",
    "吃掉了别人暂存的文件；哪天这个形状不再吃文件，那步就红。这道门由此不再依赖我记性。",
    "",
]
block = nl.join(lines) + nl
io.open(PATH, "w", encoding="utf-8", newline="").write(text + block)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_139_COUNT", after.count("### 13.9"))
print("TAIL", repr(after[-26:]))
