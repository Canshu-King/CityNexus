"""Append the shift's completion audit to the go-from-blank delivery.

Every line is either a reading taken this shift, with its coordinate, or a stated "not done".  The audit
refuses to run if section 8 has moved out from under the numbers, and writes with the file's own line
terminator.
"""
import io
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261027_GO_FROM_BLANK_DELIVERY.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "\u65e0\u5173\u3002\u91cd\u542f\u53ea\u6740" in text and False:
    sys.exit("unused")
if "| #339 \u540c\u4ee3\u6027 |" not in text:
    sys.exit("ABORT the section-8 table this audit cites is not where it was left")
if "## 9. \u672c\u73ed\u5b8c\u6210\u5ba1\u8ba1" in text:
    sys.exit("ABORT audit block already present")
lines = [
    "",
    "## 9. 本班完成审计（2026-10-29 凌晨 · 代次 `d45c5f3250`）",
    "",
    "三刀逐件，每件只写看到的与没看到的：",
    "",
    "| 件 | 状态 | 凭据（本班现读） |",
    "| --- | --- | --- |",
    "| 刀一 · 两档真实 Chrome 从空白走到 ACTIVE | 已交（前班） | 390 走到「行程执行中」且地图 6＝库 6（§339 闭，"
    "`#339` 行在本件第 8 节）；430 同代另有一趟（报告 §12.1） |",
    "| 刀二 2a · 可展开的 Agent 工具时间线 | 已交 | 事件线八十行可按开、无私有文本"
    "（`trial/results/20261026_gozero/bk116-agent-tool-timeline-430.txt:47-51`）；步骤行来源披露在两档各证一次并"
    "与只读探针一对一（`bl117…:15-21` 对 `bl118…:4-8`；`bn122…:20-22` 对 `bn123…:4-7`）；"
    "长页面形状滚后可按（`bo128…:20-23`）；代次负对照 `bo128-generation-ticket.txt:1-3` 与 `bo128…:16` |",
    "| 刀二 · 新旧差异摆在接受键旁 | 码在两处，屏上一格未证 | 出发卡 `DraftDepartureCard.tsx:376` 紧贴 `:377`；"
    "课堂面板 `ClassroomPresenterPanel.tsx:307-308` 两枝都写「未知」；本档证到的是「费用：不变」那一枝，"
    "**「费用：未知」仍无证词**（#344） |",
    "| 刀二 · 接受后主动刷新 | 已交（前班） | 整链 confirm→promote→freeze→replan→按这一版→`prepare-plan 201`"
    " 在两代各走通（`bf110…-r4.txt:75-81`、`bj115….txt:74-99`）；地图 6＝计划点 6（#335） |",
    "| 刀三 · 课堂手册过期断言与 QUICK_CARD | 已交（前班） | 本档未再动课堂线，未新增读数 |",
    "",
    "门禁与门的原话（都是本班内取的，不是沿用的）：",
    "",
    "一、宽面类型检查 `frontend/tsconfig.typecheck.json` 覆盖 `src/**/*.ts(x)`，退出码 `0`（回执"
    "`trial/results/20261026_gozero/r133-typecheck-broad-receipt.txt:1-4`，其中带测量时的尖 d45c5f3250 与被检文件的 blob 82a158d91bf0）；窄配置只含五枚具名文件的盲区已写在第 8 条，未擅自动。",
    "二、走查臂互不污染尺 `trial/human_walk/_arm_collision_ruler_r108.py`：`SELFTEST_OK`、"
    "`ARMS files=315 … COLLISIONS 0`。",
    "三、提交门 `trial/human_walk/_cmdr_pathspec_commit_gate_r119.py` 三格自测在 GitHub runner 上印出"
    "`ROOT_ARM True` / `COMMIT_PATHS 1` / `FOREIGN_STAGED before=1 after=1` / `SELFTEST_OK …`"
    "（`trial/results/20261026_gozero/r130-ci-gate-step-proof.txt:10-13`，run `40756205676` 步号 7）。",
    "四、发布门两代 `4d5895d89e`、`4d1eee472a` 的 backend / frontend-build / screen-text 三个 job 全 success；"
    "`dc7b5e6d5d` 那一代被并发取消（`cancel-in-progress` 的形状），所以那步的原话只认上面那一条。",
    "",
    "本班的写动作全部可取回：九笔提交 `599ed95b76`、`fb63b625f2`、`95997901dd`、`9a559d6c78`、"
    "`c35397222d`、`dc7b5e6d5d`、`4d5895d89e`、`4d1eee472a`、`d45c5f3250`（末笔含本审计前的账本 §13.9），"
    "其中产品文件只有 `frontend/src/trial/mobile/WorkspaceActions.tsx` 一枚、净增二十七行删零行；"
    "其余全是 `trial/` 仪表、证据与 workflow 定义。并发写者的二十二条 index 暂存条目在每一笔之后现读都还是"
    "二十二条。",
    "",
    "没做的事，直说：",
    "",
    "一、整套后端测试本档没有重跑 —— 本班没改后端，代次级后端读数来自 CI 的 backend job；"
    "第 6 条那十五枚红的归属仍待裁，没有把它算成已修。",
    "二、平板 `USER_VERIFIED` 仍是 PENDING，主人真机走过之前我不代按。",
    "三、课堂随机城市池仍 0/3；冻结公交事实 `route_geometry=[]` 那一格未变。",
    "四、`#283`、`#312`、`#330`、`#333` 等裁语未落，`#331` 镜像腿的 401 未修，`#332` 重启身份恢复仍未做"
    "（本班两次靠「另起一栈」绕过它，那是绕行不是修）。",
    "五、e2e 套件未跑：权威口径要 `npm run dev`，dev 数字不算交付证据，跑它只会多一张不可比的表。",
    "",
    "另一条勘误，不改旧正文、只在此登记：报告 §13.5 把拆笔后的第二笔写成 `bebdf21b72`，那枚是拆笔前的临时尖，现在 `git cat-file -t` 取不回；它对应的真提交是 `fb63b625f2`（五文件那笔）。坐标取不回就是坐标作废。",
    "",
]
io.open(PATH, "w", encoding="utf-8", newline="").write(text + nl.join(lines) + nl)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("BYTES_BEFORE", len(text.encode("utf-8")), "BYTES_AFTER", len(after.encode("utf-8")))
print("AUDIT_COUNT", after.count("## 9. 本班完成审计"))
print("TAIL", repr(after[-24:]))
