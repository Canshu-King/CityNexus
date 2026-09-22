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
    forbidden = [p for p in paths if str(p).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                 in FORBIDDEN_DB_NAMES]
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
    forbidden = [str(p) for p in paths
                 if str(p or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] in FORBIDDEN_DB_NAMES]
    indices = [r.get("run_index") for r in rows]
    checks = {
        "all_runs_reported": len(rows) == rounds,
        "run_indices_contiguous": indices == list(range(1, rounds + 1)),
        "exact_sha_named": bool(str(sha or "").strip())
        and str(sha).strip().upper() != "UNKNOWN",
        "target_nodeid_named": bool(str(target_nodeid or "").strip()),
        "run_shape_named": run_shape in RUN_SHAPES and bool(str(command or "").strip()),
        "every_run_resolved_a_db": not not_printed,
        "no_two_runs_share_a_temp_db": not dupes,
        "no_forbidden_target": not forbidden,
        "row_counts_recorded": not missing_field_rows,
        "every_run_has_a_node_outcome": all(o in NODE_OUTCOMES for o in outcomes),
        "no_unobserved_run": all(o != "NOT_OBSERVED" for o in outcomes),
        "all_green": greens == rounds,
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
    elif not checks["every_run_resolved_a_db"]:
        out["verdict"] = (f"HARNESS_INVALID_no_resolved_db_path(run_index={not_printed})")
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

    out["acceptance_reached"] = out["verdict"] == f"STREAK_MET({rounds})"
    out["closure_allowed"] = bool(out["acceptance_reached"]
                                  and rounds >= 10
                                  and checks["clause6_declared_for_closure"]
                                  and independence_declared)
    out["clause6_note"] = (
        "第 6 条：命令面已扫（干净）" if checks["clause6_command_surface_clean"]
        else "第 6 条：命令面不干净，见 verdict"
    ) + ("；自证文本已声明 ⇒ 可谈结案" if checks["clause6_declared_for_closure"]
         else "；自证文本未声明 ⇒ 最多 STREAK_GREEN，不签 CLOSED")
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
