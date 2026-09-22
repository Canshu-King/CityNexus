"""ORD-0210 机制层 · **共享判据模块**：把 `GATE_ACCEPTANCE_STREAK` 十条里**能被机器判的那几条**
写成一份可复用的纯函数，常驻门 `test_qoder_db_isolation_same_verdict.py` 与交付收据共用同一把尺。

来源（照录，不改词）：
* 仲裁 15:58:48 冻结八条（总线 `5773071703`，账本「commander 执行令 @16:0x」①）。
* 仲裁 16:40:22 追加第 9/10 条（总线 `5773588112`，账本「commander 执行令（第四条）@17:5x」①）。
* 16:10 冻结顺序（总线 `5773209274`）里点名的两件机制交付：
  `FLIP_WITHOUT_SHARED_STATE classification` + `acceptance-streak logic wired`。

**本模块刻意不做的事（分工，不是遗漏）**：
第 10 条要求"分类的范围是 (exact SHA, target node id, run shape)"，并且
**"Whole-command/file exit is not a proxy for the target node"**。把逐 run 的**目标节点**判定
从一条容器命令的输出里**抽出来**这件事，commander 17:5x 已自行认领（`live_checks/gate_streak.py`）。
所以这里**不解析任何多节点容器的输出**：本模块只**接收**已经逐 run 抽好的 `node_outcome`，
并且**拒绝**在拿不到逐 run 目标节点判定时给目标节点定性（判 `UNCLASSIFIED_IN_THIS_SHAPE`）。
⇒ 一份"整文件 0/10 绿"的收据，在这里得到的不是 `STABLE_RED(whole-file)`，
而是"这条数据不足以给目标节点定性"。这正是他 17:5x 自纠的那类错。

名字与 commander 工具**保持一致**（`STREAK_MET` / `STREAK_NOT_MET` / `HARNESS_INVALID_no_resolved_db_path`
/ `STREAK_INVALID_shared_db_path` / `ABORT_FORBIDDEN_TARGET`）是为了两边不各说各话；
本模块多加的只有 `RECEIPT_INCOMPLETE(...)`（第 4/9 条的收据完整性）与 `OBSERVATION_ONLY`（第 8 条）。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# ======================================================================================
# 冻结词表（第 9 条：形制是收据的一部分；第 10 条：定性只有这四个名字）
# ======================================================================================

#: 三种跑法形制 —— 原文照录仲裁 16:40 的第 9 条列举。
SINGLE_NODE = "single-node"
NODE_WITH_PRECEDING_DOORS = "node-with-preceding-doors-in-one-process"
WHOLE_FILE = "whole-file"
RUN_SHAPES: tuple[str, ...] = (SINGLE_NODE, NODE_WITH_PRECEDING_DOORS, WHOLE_FILE)

#: 目标节点在**某一个 run** 里自己的结果。`NOT_OBSERVED` 是必须的第三态：
#: 收集 0 条 / 中断 / 用法错误都"没有红"，把它们当绿就是"没有分母却报了判定"。
NODE_OUTCOMES: tuple[str, ...] = ("GREEN", "RED", "NOT_OBSERVED")

#: 第 10 条的四个定性名字（形状写进结论文本里，不另起一名）。
CLASSIFICATIONS: tuple[str, ...] = (
    "STABLE_GREEN",
    "STABLE_RED",
    "FLIP_WITHOUT_SHARED_STATE",
    "UNCLASSIFIED_IN_THIS_SHAPE",
)

#: 仲裁 15:58 的另一半分类：**同一个解析库** + 判定随状态变化 ⇒ 不能叫 FLIP。
SHARED_STATE_CLASSIFICATIONS: tuple[str, ...] = (
    "ISOLATION_BREACH",
    "DIRTY_DB_FALSE_GREEN",
    "DIRTY_DB_FALSE_RED",
)

#: 永不许被门碰的库（与 conftest 的 ORD-0211 边界、commander 工具的 FORBIDDEN_BASENAMES 同名单）。
FORBIDDEN_DB_NAMES: tuple[str, ...] = ("_live.db", "_preview.db", "citynexus_live.db")

#: 仲裁 19:10 源审计 ①：结案要有**独立**的反向证据，不是只把"10 连绿"改名成 STREAK_GREEN。
#: 未交反向证据 ⇒ closure_eligible 恒 False；交了但不是这两值 ⇒ 收据不合法。
REVERSE_MUTATION_RESULTS: tuple[str, ...] = (
    "KILLED", "STREAK_BROKEN", "SURVIVED", "NOT_MEASURED", "NOT_APPLICABLE_NO_ANCHOR",
)
#: 只有这两枚算"保护点被破坏后门会重新变红/断 streak"。
CLOSURE_GRADE_REVERSE_RESULTS: tuple[str, ...] = ("KILLED", "STREAK_BROKEN")

#: 解码链可能留下的坏字符：U+FFFD（静默替换）与 surrogateescape 造出的孤立低代理（U+DC80-U+DCFF）。
CORRUPTION_MARKS: tuple[str, ...] = ("\ufffd",)
SURROGATE_RANGE = (0xDC80, 0xDCFF)


def has_decoding_damage(text: Any) -> str:
    """这段文本里有没有"解码过程动过手脚"的痕迹？返回一句具名原因，干净就返回空串。"""

    blob = str(text or "")
    if "\ufffd" in blob:
        return "含 U+FFFD（errors='replace' 的产物：那一行的原字节已经丢了）"
    for ch in blob:
        if SURROGATE_RANGE[0] <= ord(ch) <= SURROGATE_RANGE[1]:
            return f"含 surrogateescape 的孤立代理 {hex(ord(ch))}（原字节还在，但这条值不是真字符）"
    return ""


def normalize_db_path(path: Any) -> str:
    """Windows 文件名**大小写不敏感**：`_live.db`、`_LIVE.DB`、`C:/Users/…/_Preview.db`
    都必须是同一枚靶子。用 normcase+casefold 比较，别拿裸 `Path.name` 撞字面。"""

    import os

    text = str(path or "").strip().replace("sqlite:///", "", 1)
    return os.path.normcase(text).casefold()


def path_is_forbidden(path: Any) -> str:
    """返回命中的被保护库名（没命中返回空串）。比较用归一化后的名字。"""

    import os

    name = normalize_db_path(os.path.basename(normalize_db_path(path)))
    for guarded in FORBIDDEN_DB_NAMES:
        if name == guarded.casefold():
            return guarded
    return ""


def resolved_path_problems(path: Any) -> list[str]:
    """第 1 条边界的"resolved absolute DB path"到底该长什么样 —— 逐条可判，别只写一句口号。"""

    import os

    text = str(path or "").strip()
    problems: list[str] = []
    if not text or text == "NOT_PRINTED":
        return ["没有解析出的绝对路径（NOT_PRINTED/空）"]
    damaged = has_decoding_damage(text)
    if damaged:
        problems.append(f"路径解码受损：{damaged} ⇒ 这条路径不能当收据值用")
    if not os.path.isabs(text):
        problems.append(f"路径不是绝对的：{text[:80]!r}")
    if not text.lower().endswith((".db", ".sqlite", ".sqlite3")):
        problems.append(f"路径不像一个 SQLite 库文件：{text[:80]!r}")
    if path_is_forbidden(text):
        problems.append(f"命中被保护的库：{path_is_forbidden(text)}")
    return problems

#: 第 4 条 + 第 9 条要求的逐 run 字段。少了任何一项，收据就不完整（不是"少写点说明"）。
REQUIRED_RUN_FIELDS: tuple[str, ...] = (
    "run_index",
    "exit_code",
    "node_outcome",
    "resolved_absolute_db_path",
    "initial_row_counts",
    "final_row_counts",
)

#: 收据头必须有的四项：第 1 条（SHA）、第 9 条（形制 + 精确 nodeid + 命令）、第 6 条（自证）。
REQUIRED_RECEIPT_FIELDS: tuple[str, ...] = (
    "sha",
    "target_nodeid",
    "run_shape",
    "command",
)

#: pytest 的进程退出码里，只有这两个能读出"那一条用例的结果"（且仅限单节点形制）。
_EXIT_TO_OUTCOME = {0: "GREEN", 1: "RED"}


# ======================================================================================
# 文本读取权威（仲裁源审计 5775293071 ①）
# 一句话：**先完整字节、再显式解码、按 UTF-8 → gb18030 → surrogateescape 回退，绝不静默 U+FFFD。**
# 今天栽过的三处（gate_streak.py:46-60 的 read_text、我 9514eb7:246 的 replace、
# ledger_anchor_guard 的 bytes.split）都是同一件事：**解码失败被当成"没有命中"**。
# ======================================================================================

#: 回退顺序写死成常量，免得出第二份链。
TEXT_CODECS: tuple[str, ...] = ("utf-8", "gb18030")

#: 收据行的前缀（app 在收集期打印的 ORD-0211 那一行）。
RECEIPT_PREFIX = "ORD-0211 test database: resolved="


def read_text_bytes(path: Any) -> bytes:
    """只读字节。**任何** reader 的第一步都该是这样：解码决定必须显式、可追溯。"""

    with open(str(path), "rb") as handle:
        return handle.read()


def read_text(path: Any) -> str:
    """按 §4 的回退链解码一个文件；**永不抛**，也永不返回被替换字符污染的内容。

    顺序：utf-8 严格 → gb18030 严格 → utf-8/surrogateescape → gb18030/surrogateescape
    → latin-1/surrogateescape（兜底，它必成，且 surrogateescape 保字节可逆）。
    严格那两档优先 ⇒ 能真解出来的绝不进"未知字符"档；surrogateescape 档**保留原字节**，
    所以下游 `resolved=` 路径不会因为一个坏字节而被改坏。
    """

    return decode_child_text(read_text_bytes(path))[0]


def decode_child_text(data: bytes) -> tuple[str, str]:
    """解码一段子进程输出/文件字节，返回 (文本, 实际用的 codec)。

    codec 要进收据：`utf-8` 和 `gb18030/surrogateescape` 出来的字符串可能长度相同、内容不同，
    只有把"用哪档解的"记下来，别人才复核得了这条读数是不是被解码改过。
    """

    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"期望 bytes，实际 {type(data).__name__} —— 别把已解码的 str 喂进来")
    blob = bytes(data)
    for codec in TEXT_CODECS:
        try:
            return blob.decode(codec), codec
        except UnicodeDecodeError:
            continue
    for codec in TEXT_CODECS:
        try:
            return blob.decode(codec, errors="surrogateescape"), f"{codec}/surrogateescape"
        except UnicodeDecodeError:  # pragma: no cover - surrogateescape 不该失败
            continue
    return blob.decode("latin-1", errors="surrogateescape"), "latin-1/surrogateescape"


def parse_resolved_path(stdout: str, stderr: str = "") -> tuple[str, str]:
    """从**子进程 stdout** 里取 app 自己解析并打印的绝对路径。

    两条硬规矩：
    1. **不许把 stdout 与 stderr 拼成一坨再找**（`gate_streak.py:50/:82` 的错）—— pytest 的
       header 走 stdout、进度/警告可能走 stderr，拼接后一条 `resolved=` 会被跨流粘连成
       `<日志前缀>resolved=…`，路径当场被改坏。所以两路分开扫。
    2. 命中行必须是**干净的一行**：不以 URL/路径常见粘连字符开头，且带 `| declared_by=`
       （conftest 那行的固定尾巴）。宁可报"没捕到"也不要交一条被污染的路径。
    返回 (路径 或 空串, 原因)。
    """

    def scan(text: str, stream: str) -> tuple[str, str]:
        for line in text.splitlines():
            if RECEIPT_PREFIX not in line:
                continue
            stripped = line.strip()
            head, _, tail = stripped.partition(RECEIPT_PREFIX)
            if head.strip():
                # 前缀前面还有内容 ⇒ 这是一条被粘连/截断的行，不能用。
                return "", f"{stream} 里那行 `resolved=` 前面还有内容（跨流粘连或被截断）：{stripped[:60]!r}"
            raw, _, rest = tail.partition("|")
            path = raw.strip()
            if not path:
                return "", f"{stream} 命中了前缀但路径为空"
            if "declared_by=" not in rest:
                return "", f"{stream} 那行缺 `| declared_by=` 尾巴，不像完整的收集期收据"
            return path, f"{stream} 里的收集期收据行"
        return "", "stdout 里没有 ORD-0211 收集期收据行"

    path, why = scan(stdout or "", "stdout")
    if path:
        return path, "app_printed_receipt_line"
    err_path, err_why = scan(stderr or "", "stderr")
    if err_path:
        # 收据行走错了流：仍然是 app 打印的原样一行，可以用，但要写明是哪条流。
        return err_path, "app_printed_receipt_line_on_stderr"
    return "", f"{why}；{err_why}"


#: 摘要行里能读到的计数名字（pytest 的 `N passed / N failed / N skipped / …`）。
SUMMARY_COUNTERS: tuple[str, ...] = (
    "passed", "failed", "skipped", "xfailed", "xpassed", "deselected", "error", "errors",
)


def summarize_pytest_counts(text: str) -> dict[str, int]:
    """从子进程输出末尾那行摘要里读**计数**（不是逐 nodeid verdict —— 那仍是抽取器的活）。

    只要一个数就够钉住今天这格假绿：`passed`。所以这一句不解析多节点结果，
    也就不与 commander 那份抽取器长成两把尺。
    """

    import re

    counts: dict[str, int] = {}
    for line in reversed([ln for ln in str(text or "").splitlines() if ln.strip()]):
        if not any(f" {c}" in line for c in SUMMARY_COUNTERS):
            continue
        for unit in SUMMARY_COUNTERS:
            found = re.search(rf"(\d+)[=~]? ?{unit}\b", line)
            if found:
                counts["errors" if unit == "error" else unit] = int(found.group(1))
        if counts:
            counts["summary_line"] = 1 if any(k in counts for k in SUMMARY_COUNTERS) else 0
            return counts
    return counts


def corroborate_node_outcome(outcome: str, *, run_shape: str,
                             counts: dict[str, int] | None) -> tuple[str, str]:
    """用**摘要计数**佐证一次退出码；佐不到就把结论降级成 `NOT_OBSERVED`。

    实测出来的假绿通道（2026-09-22 19:5x–20:0x，我自己那把尺）：靶子整条 `@pytest.mark.skip`
    ⇒ pytest **exit 0** ⇒ `node_outcome_from_exit()` 报 `GREEN`，而那条用例一次都没跑。
    同一形状还有 exit 1 来自收集错误而非用例失败。第 10 条要的是"目标节点自己的结果"，
    没跑过就没有结果 ⇒ 一律 `NOT_OBSERVED`（宁可让 streak 判 `HARNESS_INVALID`，
    也不能让 10 次 skipped 报成 `STREAK_MET(10)`）。
    这份函数是**唯一实现**：commander 的 `gate_streak.py` 现在直接 import 共享模块，
    所以他那条通道跟着一起修好，不需要第二处改。
    """

    if run_shape != SINGLE_NODE:
        return outcome, "非单节点形制：逐 nodeid verdict 由抽取器负责，这里不动"
    got = counts or {}
    if not got:
        return "NOT_OBSERVED", "没有可读的摘要计数 ⇒ 退出码无法佐证（fail-closed）"
    ran = got.get("passed", 0) + got.get("failed", 0) + got.get("error", 0) \
        + got.get("errors", 0) + got.get("xfailed", 0) + got.get("xpassed", 0)
    if ran == 0:
        return "NOT_OBSERVED", (f"摘要里没有任何执行计数（{got}）"
                               f"；skipped={got.get('skipped', 0)} ⇒ 目标节点没跑过，不算结果")
    if outcome == "GREEN" and got.get("passed", 0) < 1:
        return "NOT_OBSERVED", (f"exit 0 但 passed=0（skipped={got.get('skipped', 0)} "
                               f"xfailed={got.get('xfailed', 0)} xpassed={got.get('xpassed', 0)}）"
                               " ⇒ 不许当绿")
    if outcome == "RED" and got.get("failed", 0) + got.get("errors", 0) + got.get("error", 0) < 1:
        return "NOT_OBSERVED", f"exit≠0 但摘要里没有 failed/error 计数（{got}）⇒ 红来自中断还是失败分不清"
    return outcome, "退出码与摘要计数一致"


#: 三种形制的**精确**命令面。第 9 条说形制是收据的一部分；那命令面就得能逐字对得上，
#: 否则"我声明了 single-node"和"我跑的其实是别的形状"分不开（仲裁源审计 ③ 的那句：
#: "single-node may currently run with cross isolation and may then classify itself STABLE_GREEN"）。
SHAPE_ARGV: dict[str, tuple[str, ...]] = {
    SINGLE_NODE: ("-m", "pytest"),                       # 加**恰好一条** nodeid + 下面两个开关
    NODE_WITH_PRECEDING_DOORS: ("-m", "pytest"),         # ≥2 条 nodeid，同进程
    WHOLE_FILE: ("-m", "pytest"),                        # 一个文件路径，不点名单条
}
SHAPE_REQUIRED_FLAGS: dict[str, tuple[str, ...]] = {
    SINGLE_NODE: ("--tb=short", "--import-mode=importlib"),
    NODE_WITH_PRECEDING_DOORS: ("--tb=short", "--import-mode=importlib"),
    WHOLE_FILE: ("--tb=short", "--import-mode=importlib"),
}
#: 单节点形制里**不许**出现的开关：`-rA` 会把逐 run 报告混进 stdout，
#: `-p no:cacheprovider` 之类是"改跑法"而不是"记读数"。
SHAPE_FORBIDDEN_FLAGS: dict[str, tuple[str, ...]] = {
    SINGLE_NODE: ("-rA", "-rf", "-rp", "--randomly", "-p"),
    NODE_WITH_PRECEDING_DOORS: ("-rA", "-rf", "-rp", "--randomly", "-p"),
    WHOLE_FILE: ("-rA", "-rf", "-rp", "--randomly", "-p", "--deselect", "-k"),
}


def shape_command(run_shape: str, nodeids: Sequence[str], python: str = "") -> list[str]:
    """按形制生成**唯一合法**的命令面（给引用方对齐用，别各自攒一份 argv）。"""

    if run_shape not in RUN_SHAPES:
        raise ValueError(f"未知形制 {run_shape!r}")
    ids = [str(n) for n in nodeids if str(n).strip()]
    if run_shape == SINGLE_NODE and len(ids) != 1:
        raise ValueError(f"single-node 必须恰好一条 nodeid，实际 {len(ids)} 条")
    if run_shape == WHOLE_FILE and len(ids) != 1:
        raise ValueError("whole-file 形制的 targets 是一个文件路径，不是多条 nodeid")
    if run_shape == NODE_WITH_PRECEDING_DOORS and len(ids) < 2:
        raise ValueError("node-with-preceding-doors 至少要两条 nodeid（否则它就是 single-node）")
    argv = [python] if python else []
    argv += [*SHAPE_ARGV[run_shape], *ids, *SHAPE_REQUIRED_FLAGS[run_shape]]
    return argv


#: 会吃掉后一个参数作为自己取值的开关（不在此列的 `-x value` 才是 selector）。
FLAGS_TAKING_VALUE: tuple[str, ...] = (
    "--tb", "-m", "--rootdir", "--configFile", "--opcodes", "--ignore", "--exclude", "-k", "-n",
)


def parse_pytest_selectors(argv: Sequence[str]) -> tuple[list[str], list[int]]:
    """从 argv 里**精确**抽出 pytest 的 positional selector（含 nodeid / 文件路径）。

    仲裁第四次源审（`5775970359`）点名的洞：`verify_run_shape()` 原来只查"声明的 target
    有没有出现在 argv 里"，于是 `[TARGET, "tests/seed.py::test_seed"]` 这种**多带一条 selector**
    的命令仍被签成 `single-node` ⇒ 形制声明与实际跑的东西不是一回事。这里不查"包含"，
    而是把 selector 序列整个抽出来，再要求它**逐项等于**声明集合。
    注意 `-m pytest` 与 `--tb short` 这类取值不是 selector。
    返回 (selectors, 它们在 argv 里的下标)。
    """

    args = [str(a) for a in argv]
    selectors: list[str] = []
    positions: list[int] = []
    i = 1  # argv[0] 是解释器
    while i < len(args):
        a = args[i]
        if a == "-m":                      # -m pytest：两个都不是 selector
            i += 2
            continue
        if a.startswith("-"):
            if "=" in a:                   # --tb=short 这种自带头值
                i += 1
                continue
            if a in FLAGS_TAKING_VALUE:    # `--tb short`：值也要跳掉
                i += 2
                continue
            i += 1
            continue
        selectors.append(a)
        positions.append(i)
        i += 1
    return selectors, positions


def verify_run_shape(
    *,
    run_shape: str,
    argv: Sequence[str],
    nodeids: Sequence[str],
    nodeids_in_command: Sequence[str],
    streams_separate: bool,
    decoder: str,
) -> dict[str, Any]:
    """逐 run 的证据**是否真属于声明的那个形制**。不过就没有 streak 结论（第 9 条）。

    这里只验**命令面与流的形状**，不重跑、不解析别人的输出：形制声明与 argv 对不上，
    或者 stdout/stderr 被拼成一坨，或者解码用了静默替换，都算量具不合法。
    """

    problems: list[str] = []
    args = [str(a) for a in argv]
    ids = [str(n) for n in nodeids if str(n).strip()]
    if run_shape not in RUN_SHAPES:
        problems.append(f"形制不在冻结词表里：{run_shape!r}")
    else:
        for flag in SHAPE_REQUIRED_FLAGS[run_shape]:
            if flag not in args:
                problems.append(f"{run_shape} 的 argv 缺必需开关 {flag}")
        for flag in SHAPE_FORBIDDEN_FLAGS[run_shape]:
            if flag == "-p":
                if any(a == "-p" for a in args):
                    problems.append(f"{run_shape} 的 argv 不许带 -p（它在改跑法，不是在记读数）")
            elif any(a == flag or a.startswith(f"{flag}=") for a in args):
                problems.append(f"{run_shape} 的 argv 带了被禁的 {flag}")
        if args[1:3] != list(SHAPE_ARGV[run_shape]):
            problems.append(f"argv 的调用面不是 `-m pytest`：实际 {args[:3]}")
        selectors, sel_positions = parse_pytest_selectors(args)
        derived_selectors = selectors
        if run_shape == SINGLE_NODE and len(ids) != 1:
            problems.append(f"single-node 声明了 {len(ids)} 条 target（必须恰好一条）")
        if run_shape == NODE_WITH_PRECEDING_DOORS and len(ids) < 2:
            problems.append("带前序门的形制只声明了 1 条 target ⇒ 它其实是 single-node")
        if run_shape == WHOLE_FILE and len(ids) != 1:
            problems.append(f"whole-file 应声明恰好一个文件，实到 {len(ids)} 条：{ids}")
        if not selectors:
            problems.append(f"{run_shape} 的 argv 里抽不出任何 positional selector："
                            f"{args[:5]} —— 没有 selector 就没有'跑的是哪一条'可证")
        elif run_shape == SINGLE_NODE:
            if len(selectors) != 1:
                problems.append(
                    f"single-node 声明却抽到 {len(selectors)} 条 selector {selectors}"
                    f"（argv 下标 {sel_positions}）⇒ 多带 selector 的命令不是单节点形制")
            elif ids and selectors[0] != ids[0]:
                problems.append(f"single-node 实际 selector {selectors[0]!r} ≠ 声明的 {ids[0]!r}")
        elif run_shape == NODE_WITH_PRECEDING_DOORS:
            if len(selectors) != len(ids):
                problems.append(
                    f"带前序门形制的 selector 条数({len(selectors)}) 与声明({len(ids)})不等："
                    f"{selectors}")
            elif selectors != ids:
                problems.append(
                    f"带前序门形制要求 selector **逐项同序等于**声明集合：实到 {selectors} ≠ 声明 {ids}")
        elif run_shape == WHOLE_FILE:
            if len(selectors) != 1:
                problems.append(f"whole-file 只允许一个文件 selector，实到 {selectors}")
            elif "::" in selectors[0] or not selectors[0].endswith(".py"):
                problems.append(f"whole-file 的 selector 应是一个 .py 文件路径（不含 ::）："
                                f"实到 {selectors[0]!r}")
            elif ids and selectors[0] != ids[0]:
                problems.append(f"whole-file 实际文件 {selectors[0]!r} ≠ 声明的 {ids[0]!r}")
        extra = [s for s in selectors if s not in set(ids)]
        if extra:
            problems.append(f"argv 里有声明之外的 selector：{extra}（形制声明不能靠'包含'成立）")
        if not nodeids_in_command:
            problems.append("命令里没有目标节点，却给了 node 级 verdict")
        elif run_shape == SINGLE_NODE and [str(x) for x in nodeids_in_command] != ids:
            problems.append(
                f"命令里的 nodeid 与声明的 targets 逐项不等：{list(nodeids_in_command)} vs {ids}")
        elif run_shape == SINGLE_NODE and nodeids_in_command and derived_selectors \
                and [str(x) for x in nodeids_in_command] != derived_selectors:
            problems.append(
                f"调用方声称的 nodeids_in_command {list(nodeids_in_command)} ≠ 从 argv 抽出的 "
                f"{derived_selectors} ⇒ 声称不被采信")
    if not streams_separate:
        problems.append("stdout 与 stderr 被拼成了一坨 ⇒ `resolved=` 可能被跨流粘连改坏（第 9 条）")
    if "replace" in decoder or not decoder:
        problems.append(f"解码器 {decoder!r} 会静默替换坏字节：路径/锚点可能被改而无人报警")
    return {"run_shape_verified": not problems, "problems": problems,
            "run_shape": run_shape, "decoder": decoder,
            "nodeids": ids, "streams_separate": bool(streams_separate),
            "argv_selectors": list(derived_selectors), "selector_positions": list(sel_positions)}


# ======================================================================================
# 逐 run：从进程退出码读目标节点的结果（只在单节点形制下允许，且必须证明命令里就一条）
# ======================================================================================
def node_outcome_from_exit(
    exit_code: int | None,
    *,
    run_shape: str,
    nodeids_in_command: Sequence[str],
) -> str:
    """把**一个进程**的退出码读成**目标节点**的判定。

    只有在同时满足两件事时才敢读：形制是 `single-node`，且命令里点名的就是那一条 nodeid。
    其余情形一律 `NOT_OBSERVED` —— 多节点容器"整体红了"可能是邻居红的（第 10 条原话）。
    退出码 5（collected 0）/ 2（中断）/ 3（内部错）/ 4（用法错）**不是绿**：
    一条都没跑不等于跑绿了，这是本模块最容易骗自己的一格。
    """

    if not isinstance(exit_code, int):
        return "NOT_OBSERVED"
    if run_shape != SINGLE_NODE:
        return "NOT_OBSERVED"
    if len(nodeids_in_command) != 1 or not str(nodeids_in_command[0]).strip():
        return "NOT_OBSERVED"
    return _EXIT_TO_OUTCOME.get(exit_code, "NOT_OBSERVED")


# ======================================================================================
# 第 10 条：给目标节点定性（范围 = exact SHA + target node id + run shape）
# ======================================================================================
def classify_target_node(
    *,
    sha: str,
    target_nodeid: str,
    run_shape: str,
    node_outcomes: Sequence[str],
    resolved_db_paths: Sequence[str | None],
) -> dict[str, Any]:
    """按仲裁冻结的两则分类法给**目标节点**定性。返回的每个字段都是从入参算出来的，无字面结论。

    ```text
    same resolved DB path + state changes verdict  => DIRTY_DB_FALSE_* / ISOLATION_BREACH
    different fresh DB paths + verdict still flips => FLIP_WITHOUT_SHARED_STATE(<shape>)
    ```
    """

    runs = list(node_outcomes)
    paths = list(resolved_db_paths)
    green = sum(1 for o in runs if o == "GREEN")
    red = sum(1 for o in runs if o == "RED")

    out: dict[str, Any] = {
        "sha": sha,
        "target_nodeid": target_nodeid,
        "run_shape": run_shape,
        "runs": len(runs),
        "green": green,
        "red": red,
        "not_observed": len(runs) - green - red,
        "classification": "UNCLASSIFIED_IN_THIS_SHAPE",
        "reason": "",
        "sample_note": "",
    }

    def name(cls: str, reason: str) -> dict[str, Any]:
        out["classification"] = cls
        out["reason"] = reason
        out["named_shape"] = f"{cls}({run_shape})" if run_shape else cls
        return out

    def stable(cls: str, reason: str) -> dict[str, Any]:
        """`STABLE_*` 只有在样本够分时才不是误导：第 2 条把 10 写死，正是为了
        把"恒红"和"1/10 翻绿"分开。2 个 run 全红印成 STABLE_RED，明天就有人拿它当结案读数。"""

        result = name(cls, reason)
        if len(runs) < 10:
            result["sample_note"] = (
                f"样本只有 {len(runs)} 个 run：这句'稳定'是在这 {len(runs)} 次里成立，"
                f"**分不开『恒红』与『1/10 才翻一次绿』**。要谈稳定/结案按第 2 条跑满 10 个独立进程。")
        return result

    # —— 先判"有没有资格定性"：范围三件缺一件都不许定（第 10 条 + 无分母不报数）——
    if not str(sha or "").strip() or str(sha).strip().upper() == "UNKNOWN":
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"没有 exact SHA（sha={sha!r}）：定性范围的第一把键就缺，判不了")
    if not str(target_nodeid or "").strip():
        return name("UNCLASSIFIED_IN_THIS_SHAPE", "没有点名 target node id：不知道在给谁定性")
    if run_shape not in RUN_SHAPES:
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"形制未声明或不在冻结词表里（run_shape={run_shape!r}）—— 第 9 条")
    if not runs:
        return name("UNCLASSIFIED_IN_THIS_SHAPE", "一次都没跑：没有分母，红绿都无从谈起")
    if out["not_observed"]:
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"{out['not_observed']}/{len(runs)} 个 run 拿不到目标节点自己的判定"
                    "（整条容器命令的 exit 不是目标节点的代理 —— 第 10 条）")
    if len(runs) < 2:
        # 第 8 条：一次孤立观测只是观察，不是结案。一次绿不能说"稳定绿"，一次红也不能说"恒红"。
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"只有 1 个 run（{runs[0]}）：第 8 条 —— 单次孤立观测只是观察，永不结案")

    bad_paths = [i + 1 for i, p in enumerate(paths) if not str(p or "").strip()
                 or str(p).strip() in {"NOT_PRINTED", "None"}]
    if len(paths) != len(runs) or bad_paths:
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"这些 run 没有解析出的临时库绝对路径（run_index={bad_paths or '数量不符'}）："
                    "无法证明各 run 之间不共享状态")
    forbidden = [p for p in paths if path_is_forbidden(p)]
    if forbidden:
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"解析路径里出现被保护的库（{forbidden[:2]}）：这批读数不属本门，判不了")

    dupes = sorted({str(p) for p in paths if list(paths).count(p) > 1})

    # —— 三态齐了，才谈"稳不稳/翻不翻" ——
    if green and red:
        if dupes:
            # 两则分类的第一条：同一个解析库 + 判定会变 ⇒ 那不是"无共享状态也翻"。
            return name("ISOLATION_BREACH",
                        f"判定翻转（{green}绿/{red}红）但出现重复解析路径（{dupes[:2]}）："
                        "⇒ ISOLATION_BREACH / DIRTY_DB_FALSE_*，不是 FLIP_WITHOUT_SHARED_STATE")
        return name("FLIP_WITHOUT_SHARED_STATE",
                    f"目标节点自己两种结果都出现过（{green} 绿 / {red} 红），"
                    f"且 {len(set(map(str, paths)))} 个 run 各自一个不同的临时库")
    if dupes:
        return name("UNCLASSIFIED_IN_THIS_SHAPE",
                    f"判定虽一致但 run 之间共享了解析路径（{dupes[:2]}）：这批 run 不是独立观测")
    if green and not red:
        return stable("STABLE_GREEN", f"{green}/{len(runs)} 全绿（逐 run 目标节点判定）")
    return stable("STABLE_RED", f"{red}/{len(runs)} 全红（逐 run 目标节点判定）—— 恒红不是翻转")


def flips_without_shared_state(result: Mapping[str, Any]) -> bool:
    """给引用方的一句判据：只有 classification 恰好等于 FLIP_WITHOUT_SHARED_STATE 才算翻。"""

    return str(result.get("classification")) == "FLIP_WITHOUT_SHARED_STATE"


# ======================================================================================
# 第 2/4/5/6/7/9 条：streak 结论（"验收已接线"里被机器判的那几条）
# ======================================================================================
def run_freshness_problems(row: Mapping[str, Any]) -> list[str]:
    """第 3 条"每进程一个 app 解析的新临时库"——**放在共享模块里**，不是放在某扇门里。

    仲裁第三次源审（`5775917170` §3）把 freshness 判 `RED` 的原话要点：
    检查只在 test 文件里 ⇒ `streak_verdict()/receipt_problems()` 本身没有机械判据，
    **别的引用方仍可绕过**；"10 个不同但**预先存在**的库全绿仍可能 `STREAK_MET(10)`"。
    所以这一支必须长在结论函数里：谁调 `streak_verdict` 都躲不过。
    键名同时兼容门内（`child_decoder`）与 commander 适配器（`stdout_codec`/`stderr_codec`），
    这样两边共用一把尺，不需要第二份实现。
    """

    problems: list[str] = []
    source = str(row.get("path_source") or "")
    if not source.startswith("app_printed_receipt_line"):
        problems.append(f"path_source={source!r} 不是 app 打印的收集期收据"
                        "（差集猜出来的路径不算隔离证据）")
    initial = row.get("initial_row_counts")
    if not isinstance(initial, dict):
        problems.append("没有 initial_row_counts ⇒ 跑前状态没量过")
    elif "path_did_not_exist_before_this_run" not in initial:
        problems.append("initial_row_counts 里没有 `path_did_not_exist_before_this_run`"
                        " ⇒ 不知道这库是不是本次新建的")
    elif initial.get("path_did_not_exist_before_this_run") is not True:
        problems.append(f"该临时库在本次进程之前就存在（{initial}）"
                        " ⇒ 不是 fresh 的 app 解析库，这一 run 不配当独立观测")
    elif not initial.get("absent", True):
        problems.append(f"跑前库里已有表/行（{initial}）⇒ 起始状态不为零，判定可能被喂绿")
    path = str(row.get("resolved_absolute_db_path") or "")
    path_problems = (row.get("resolved_path_problems")
                     if isinstance(row.get("resolved_path_problems"), list)
                     else resolved_path_problems(path))
    problems.extend(f"resolved 路径不合规：{p}" for p in (path_problems or []))
    decoder = str(row.get("child_decoder")
                  or f"stdout={row.get('stdout_codec', '')};stderr={row.get('stderr_codec', '')}")
    if "replace" in decoder:
        problems.append(f"解码器 {decoder!r} 会静默替换坏字节（路径/锚点可能被改而无人报警）")
    for key in ("stdout_damage", "stderr_damage"):
        if row.get(key):
            problems.append(f"{key} 量到解码受损：{row[key]}")
    return problems


def streak_verdict(
    *,
    runs: Sequence[Mapping[str, Any]],
    rounds: int,
    sha: str,
    target_nodeid: str,
    run_shape: str,
    command: str,
    independence_declared: bool = False,
    clause6_declared: bool = False,
    clause6_command_surface_clean: bool = True,
    clause6_command_surface_hits: Sequence[str] = (),
    run_shape_verified: bool = False,
    run_shape_problems: Sequence[str] = (),
    reverse_mutation_required: bool = False,
    reverse_mutation_result: str = "",
) -> dict[str, Any]:
    """算 `GATE_ACCEPTANCE_STREAK` 的结论。**结论全部从逐 run 读数派生**，不写死 PASS。

    第 6 条拆成两半，免得像 commander 工具里那句免责声明一样被当成"整条判不了"：
    * `clause6_command_surface_clean` —— **可机械判的那半**：跑靶子的命令面里不许出现
      sleep/重试/退避/降并发/放宽断言的开关。脏了就是量具不合法（两种模式都硬判）。
    * `clause6_declared` —— 交付方在收据里写明"我用什么手段达成 streak"。**它不改变 streak 的
      绿/红数字**，只决定**能不能结案**：没声明 ⇒ 最多签 `STREAK_GREEN`，不许签 CLOSED
      （仲裁 15:58 的反向要求正是这个意思）。
    """

    rows = list(runs)
    outcomes = [str(r.get("node_outcome") or "NOT_OBSERVED") for r in rows]
    paths = [r.get("resolved_absolute_db_path") for r in rows]
    greens = sum(1 for o in outcomes if o == "GREEN")
    reds = sum(1 for o in outcomes if o == "RED")

    missing_field_rows = [
        r.get("run_index") for r in rows
        if any(k not in r for k in REQUIRED_RUN_FIELDS)
    ]
    not_printed = [rows[i].get("run_index") for i, p in enumerate(paths)
                   if not str(p or "").strip() or str(p).strip() == "NOT_PRINTED"]
    dupes = sorted({str(p) for p in paths if p and list(paths).count(p) > 1})
    forbidden = [str(p) for p in paths if path_is_forbidden(p)]
    freshness = {r.get("run_index"): run_freshness_problems(r) for r in rows}
    stale_rows = [idx for idx, probs in freshness.items() if probs]
    indices = [r.get("run_index") for r in rows]
    checks = {
        "all_runs_reported": len(rows) == rounds,
        "run_indices_contiguous": indices == list(range(1, rounds + 1)),
        "exact_sha_named": bool(str(sha or "").strip())
        and str(sha).strip().upper() != "UNKNOWN",
        "target_nodeid_named": bool(str(target_nodeid or "").strip()),
        "run_shape_named": run_shape in RUN_SHAPES and bool(str(command or "").strip()),
        "every_run_resolved_a_db": not not_printed,
        "every_run_fresh": not stale_rows,
        "no_two_runs_share_a_temp_db": not dupes,
        "no_forbidden_target": not forbidden,
        "row_counts_recorded": not missing_field_rows,
        "every_run_has_a_node_outcome": all(o in NODE_OUTCOMES for o in outcomes),
        "no_unobserved_run": all(o != "NOT_OBSERVED" for o in outcomes),
        "all_green": greens == rounds,
        "run_shape_verified": bool(run_shape_verified),
        "run_shape_problems": sorted(set(str(p) for p in run_shape_problems)),
        "reverse_mutation_value_valid": (not str(reverse_mutation_result or "").strip()
                                         or str(reverse_mutation_result).strip()
                                         in REVERSE_MUTATION_RESULTS),
        "clause6_command_surface_clean": bool(clause6_command_surface_clean),
        "clause6_declared_for_closure": bool(clause6_declared),
    }

    out: dict[str, Any] = {
        "sha": sha,
        "target_nodeid": target_nodeid,
        "run_shape": run_shape,
        "command": command,
        "rounds": rounds,
        "green": greens,
        "red": reds,
        "not_observed": len(rows) - greens - reds,
        "duplicate_db_paths": dupes,
        "runs_missing_db_path": not_printed,
        "runs_missing_fields": missing_field_rows,
        "forbidden_targets": forbidden,
        "checks": checks,
        "verdict": "",
    }

    # 顺序很重要：先判"靶子不合法"，再判"量具不合法"，最后才判"绿没绿"。
    if forbidden:
        out["verdict"] = "ABORT_FORBIDDEN_TARGET"
    elif not checks["run_shape_named"] or not checks["target_nodeid_named"]:
        out["verdict"] = (f"RECEIPT_INCOMPLETE(第 9 条：形制是收据的一部分 —— "
                          f"run_shape={run_shape!r}, target_nodeid={target_nodeid!r})")
    elif not checks["exact_sha_named"]:
        out["verdict"] = "RECEIPT_INCOMPLETE(第 1 条：没有 exact SHA，streak 无从锚定)"
    elif missing_field_rows:
        out["verdict"] = (f"RECEIPT_INCOMPLETE(第 4 条：这些 run 缺逐 run 字段 "
                          f"{missing_field_rows} —— 行数/判定没记就不算收据)")
    elif not checks["run_shape_verified"]:
        out["verdict"] = ("HARNESS_INVALID_run_shape_unverified(第 9 条：形制证据没过校验 ⇒ "
                          f"不出 streak 结论；{checks['run_shape_problems'][:3]})")
    elif not checks["every_run_resolved_a_db"]:
        out["verdict"] = (f"HARNESS_INVALID_no_resolved_db_path(run_index={not_printed})")
    elif stale_rows:
        # 第 3 条：库不是本次新建的 / 路径不是 app 打印的 ⇒ 这一批不配当独立观测。
        # 放在 all_green **之前**：仲裁点名的洞正是"10 个不同但预先存在的库全绿 ⇒ STREAK_MET(10)"。
        first = freshness[stale_rows[0]]
        out["verdict"] = (f"HARNESS_INVALID_run_not_fresh(第 3 条：这些 run 的临时库不是本次新建"
                          f"或路径不是 app 打印的 run_index={stale_rows}；首个原因：{first[0]})")
    elif not checks["clause6_command_surface_clean"]:
        out["verdict"] = (f"HARNESS_INVALID_relaxed_command_surface(第 6 条可机械判的那半："
                          f"命令面出现放宽开关 {list(clause6_command_surface_hits) or ['未列出命中项']})")
    elif not checks["run_indices_contiguous"] or not checks["all_runs_reported"]:
        out["verdict"] = (f"HARNESS_INVALID_run_numbering(期望 1..{rounds}，"
                          f"实际 {indices[:3]}…共 {len(rows)})")
    elif not checks["no_unobserved_run"]:
        out["verdict"] = (f"HARNESS_INVALID_target_verdict_not_scoped({out['not_observed']} 个 run "
                          "拿不到目标节点判定 ⇒ 第 10 条：整条命令的 exit 不能当代理)")
    elif not checks["no_two_runs_share_a_temp_db"]:
        out["verdict"] = (f"STREAK_INVALID_shared_db_path(第 7 条：两个 run 落在同一个解析库 "
                          f"{dupes[:2]})")
    elif not checks["all_green"]:
        out["verdict"] = f"STREAK_NOT_MET({greens}/{rounds}_green)"
    else:
        out["verdict"] = f"STREAK_MET({rounds})"

    reverse_value = str(reverse_mutation_result or "").strip()
    out["acceptance_reached"] = out["verdict"] == f"STREAK_MET({rounds})"
    out["reverse_mutation_required"] = bool(reverse_mutation_required)
    out["reverse_mutation_result"] = reverse_value
    out["reverse_mutation_closure_grade"] = bool(
        reverse_value in CLOSURE_GRADE_REVERSE_RESULTS)
    out["closure_allowed"] = bool(out["acceptance_reached"]
                                  and rounds >= 10
                                  and checks["every_run_fresh"]
                                  and checks["clause6_declared_for_closure"]
                                  and independence_declared
                                  and out["reverse_mutation_closure_grade"])
    if out["closure_allowed"]:
        out["closure_grade"] = "CLOSED"
    elif out["acceptance_reached"]:
        out["closure_grade"] = "STREAK_GREEN"
    else:
        out["closure_grade"] = "NOT_MET"
    out["clause6_note"] = (
        "第 6 条：命令面已扫（干净）" if checks["clause6_command_surface_clean"]
        else "第 6 条：命令面不干净，见 verdict"
    ) + ("；自证文本已声明 ⇒ 可谈结案" if checks["clause6_declared_for_closure"]
         else "；自证文本未声明 ⇒ 最多 STREAK_GREEN，不签 CLOSED")
    out["closure_note"] = (
        f"10/10 绿 ⇒ 判级 {out['closure_grade']}：结案还需要**独立**的反向突变证据"
        f"（∈ {list(CLOSURE_GRADE_REVERSE_RESULTS)}）；"
        f"本次 required={out['reverse_mutation_required']} result={reverse_value or '（未交）'}。"
        "把『10 连绿』改名叫 STREAK_GREEN 只是换字，不产生新证据 —— 这一格只把两者分开写死。")
    return out


#: 靶子命令里出现这些开关，就是"把门哄绿"的形状（第 6 条可机械判的那半）。
#: 只按**整项参数**匹配，不做全文子串扫描 —— nodeid 里带 "retry" 这种词不该被判成放宽。
#: `--collect-only` 在内：一条"十次全绿"如果每次只做了收集，那是从空分母里报出来的绿。
FORBIDDEN_COMMAND_FLAGS: tuple[str, ...] = (
    "--maxfail", "-x", "--reruns", "--timeout", "--deselect", "-k", "-n", "--collect-only",
)

#: 允许出现的 `-p` 值：只许关掉随机器与缓存，关掉别的一律算放宽跑法。
ALLOWED_DISABLE_PLUGINS: tuple[str, ...] = ("no:randomly", "no:cacheprovider")


def clause6_command_surface(argv: Sequence[str]) -> tuple[bool, list[str]]:
    """扫一遍跑靶子的 argv：有没有重试 / 退避 / 降并发 / 少跑 / 只收集 的开关。

    返回 (干净?, 命中项)。只查**命令面**——测试体里有没有偷偷加 `sleep` 属于 diff 复核，
    那一半仍要交付方自证（见 `streak_verdict` 的 `clause6_note`）。
    """

    hits: list[str] = []
    args = [str(a) for a in argv]
    for token in FORBIDDEN_COMMAND_FLAGS:
        if any(a == token or a.startswith(f"{token}=") for a in args):
            hits.append(token)
    for i, a in enumerate(args):
        if a == "-p" and i + 1 < len(args) and args[i + 1] not in ALLOWED_DISABLE_PLUGINS:
            hits.append(f"-p {args[i + 1]}")
    return (not hits), sorted(set(hits))


def receipt_problems(receipt: Mapping[str, Any]) -> list[str]:
    """把一份收据读成"哪几条不合规"（空 = 合规）。给门用，判词必须是算出来的。"""

    problems: list[str] = []
    verdict = str(receipt.get("verdict") or "")
    if not verdict:
        problems.append("收据里没有 verdict")
    for field in REQUIRED_RECEIPT_FIELDS:
        if not str(receipt.get(field) or "").strip():
            problems.append(f"收据缺第 9/1 条要求的字段 {field}")
    checks = receipt.get("checks") or {}
    for key, ok in checks.items():
        # `clause6_declared_for_closure` 是**结案**闸门，不是收据合规项：机制模式下它天然是
        # False（还没交单）。把它算成"不合规"会让每张机制收据都读成红 —— 那是教会人忽略判词。
        if key == "clause6_declared_for_closure":
            continue
        # `all_green` 是**第 5 条的结果**，由 verdict（STREAK_MET / STREAK_NOT_MET）表达。
        # 把它算进"收据不合规"会让每张诚实的 STREAK_NOT_MET 收据都额外背一条不合规，
        # 真仪器缺陷就藏在这堆预期项里没人看了。
        if key == "all_green":
            continue
        if ok is False:
            problems.append(f"check {key} = False")
    if verdict.startswith(("HARNESS_INVALID", "RECEIPT_INCOMPLETE", "STREAK_INVALID", "ABORT")):
        problems.append(f"verdict 具名不合法：{verdict}")
    if receipt.get("closure_allowed") and not receipt.get("acceptance_reached"):
        problems.append("closure_allowed=True 但 streak 未达成：结案比验收还宽，方向错了")
    return problems


def observation_only(result: Mapping[str, Any]) -> tuple[bool, str]:
    """第 8 条的一句判词：一次孤立观测（哪怕绿）永不能结案。返回 (是否只算观察, 原话)。"""

    runs = int(result.get("runs") or 0)
    if runs <= 1:
        return True, ("一次孤立 GREEN 只是观察，不是结案（第 8 条）；"
                      "结案需要 streak 达成 + 反向突变证明门咬得住")
    return False, f"{runs} 个独立 run 已够谈稳定/翻转，但结案仍要 streak + 反向突变"


def _self_check() -> None:  # pragma: no cover
    """`python _qoder_streak_receipt.py` 打一遍两向自检：不依赖 pytest。"""

    flip = classify_target_node(
        sha="50b35e0", target_nodeid="X::g3", run_shape=SINGLE_NODE,
        node_outcomes=["RED"] * 9 + ["GREEN"],
        resolved_db_paths=[f"/tmp/cnx_{i}/suite.db" for i in range(10)],
    )
    print("1绿/9红(不同新库) =>", flip["named_shape"], "|", flip["reason"])
    whole = classify_target_node(
        sha="50b35e0", target_nodeid="X::g3", run_shape=WHOLE_FILE,
        node_outcomes=["NOT_OBSERVED"] * 10, resolved_db_paths=[f"/tmp/{i}" for i in range(10)],
    )
    print("整文件 0/10 绿(邻居红) =>", whole["named_shape"], "|", whole["reason"])


if __name__ == "__main__":  # pragma: no cover
    _self_check()
