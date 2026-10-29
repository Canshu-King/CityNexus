"""Append ledger section 14: the whole-backend certificate, and the rule it has to be read under."""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "\u8fd9\u9053\u95e8\u7531\u6b64\u4e0d\u518d\u4f9d\u8d56\u6211\u8bb0\u6027" not in text:
    sys.exit("ABORT the §13.9 tail this section follows is not in the report")
if "## 14 \u672c\u73ed\u540e\u7aef\u6574\u5957" in text:
    sys.exit("ABORT section 14 already exists")
lines = [
    "",
    "## 14 本班后端整套证书（§14.1–§14.2）",
    "",
    "### 14.1 现读结果与写集零交集",
    "",
    "整套跑完并落盘：`trial/results/20261029_BACKEND_CERTIFICATE_24a342198d.md`（日志",
    "`trial/results/20261026_gozero/bt143-backend-full-24a342198d.log`、分组摘要",
    "`bt143-backend-digest.txt`）。分母先取：`--collect-only` 退出码 `0`、`2828 tests collected`；",
    "末行原样是 `255 failed, 2545 passed, 15 skipped, 1 xfailed, 12 errors in 270.29s`，",
    "五项相加正好等于分母 2828 —— 这个自校验是证书脚本硬要求的，缺任何一项它就不写文件。",
    "",
    "为什么这套红不算本班引入：`git diff --name-only 22106314c2..HEAD` 共五十七个文件，",
    "分布是 `.github` 一处、`frontend` 一处、`trial` 五十五处，`backend/` 与 `contracts/` **各零处**",
    "（证书 §一，数字由 git 现读）。本班唯一的产品文件改动仍是 `WorkspaceActions.tsx`。",
    "",
    "### 14.2 blocker 6 的十五枚逐条对上，但整套总数不拿来判新红",
    "",
    "三枚具名文件逐条现读：`test_sol_concurrency_and_remap.py` 9、`test_qoder_live_replans_endpoint.py` 5、",
    "`test_dsh_list_replans_bound.py` 1 —— 与交付件 blocker 6 记的 9／5／1 一模一样，合计十五枚，",
    "归属仍待裁，本班没有把任何一枚上膛成产品缺陷。",
    "",
    "整套的 255 枚只报总数：上一次同机记录（2026-10-26 的 261／2401／12 errors）出自当日记录、",
    "本次没有重跑那一代，也没有逐条基线在册 —— 按口径，**没有逐条基线就只能报总数与聚焦范围，不判新红**。",
    "要开始判新红，得先把这份 255 枚的逐条清单立成基线；`test_r64_member_side_quest.py` 一组 52 枚",
    "是最大的一块，它是否与 live provider 缺席有关，我没测，留作下一步。",
    "",
]
io.open(PATH, "w", encoding="utf-8", newline="").write(text + nl.join(lines) + nl)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("PREFIX_INTACT", after.startswith(text[:4000]))
print("SECTION_14_COUNT", after.count("## 14 本班后端整套"))
print("TAIL", repr(after[-28:]))
