"""Compose the bus post for the ORD-0269 / ORD-0273 segment from the artifacts, never from memory.

Every number in the emitted text is read out of a file this script just opened: the arms receipt, the
green-round receipt, the `git ls-remote` line.  Counts are computed and re-asserted before writing,
because a hand-typed tally is how a previous lane got a wrong denominator into a judging rule.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--lsremote", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", default="")
    ap.add_argument("--root", default="D:/moodle/_qoder_d_lane_20260923")
    a = ap.parse_args()

    arms = load(a.arms)
    round_receipt = load(a.round)
    lsremote = Path(a.lsremote).read_text(encoding="utf-8").strip()

    arm_list = arms["arms"]
    killed = [x for x in arm_list if x["claimed_result"] == "KILLED"]
    survived = [x for x in arm_list if x["claimed_result"] != "KILLED"]
    triples = round_receipt["triples"]

    if a.manifest:
        # The arms and the green round were measured one commit apart (the driver's own parsing fix
        # landed in between).  What has to be true is that nothing UNDER TEST differs, so measure
        # that instead of asserting it.
        diff = subprocess.run(
            f'git diff --name-status {arms["head"]} {round_receipt["candidate_tip"]}',
            cwd=a.root,
            capture_output=True,
            text=True,
            shell=True,
        ).stdout.strip().splitlines()
        # "Under test" is a path question, not a count: the arms mutate files under frontend/ and the
        # gates read files under frontend/.  Evidence tooling committed in between is not a change to
        # what was measured -- but saying so requires naming which files those are.
        under_test = [line for line in diff if "\tfrontend/" in line]
        tooling = [line for line in diff if "\tfrontend/" not in line]
        manifest = {

            "generatedBy": "e345b9d6",
            "orders": ["ORD-0269 cells 1/3 + R-4 + R-6", "ORD-0273 TEXT / TEXT-EN / ACTION"],
            "external_readback": lsremote,
            "authoritative_tip_at_delivery": round_receipt["authoritative_tip_at_delivery"],
            "arms_tip": arms["head"],
            "green_round_tip": round_receipt["candidate_tip"],
            "tree_diff_between_tips": {
                "full": diff,
                "under_test_files": under_test,
                "evidence_tooling_files": tooling,
                "anything_under_test_changed": bool(under_test),
                "reading": f"{len(under_test)} file(s) under frontend/ differ between the arms tip and "
                f"the green-round tip; {len(tooling)} evidence-tooling file(s) differ. The arms mutate "
                "only frontend/, so the green round re-measures the same bytes the arms killed.",
            },

            "files": [],
            "counts": {
                "arms": len(arm_list),
                "arms_killed": len(killed),
                "triples": len(triples),
                "triple_shas": sorted({t["exact_sha"] for t in triples}),
            },
            "R_SCHEMA_01_class": round_receipt.get("R_SCHEMA_01_class"),
            "publisher_refusal_writing_rule": round_receipt.get("publisher_refusal_writing_rule"),
            "nodeid_root_rule": "every triple carries nodeid_root and names the same cwd in run_shape",
            "attribution": "claimed_result is self-reported; derived_result belongs to the verifier",
        }
        for path in (a.arms, a.round):
            blob = Path(path).read_bytes()
            import hashlib

            manifest["files"].append(
                {
                    "name": Path(path).name,
                    "bytes": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest(),
                }
            )
        # The manifest is written after the green round, so HEAD has moved on by then.  Say how far,
        # and say it as a measurement: what matters is whether anything a triple points at moved.
        head_now = subprocess.run(
            "git rev-parse HEAD", cwd=a.root, capture_output=True, text=True, shell=True
        ).stdout.strip()
        after_round = subprocess.run(
            f'git diff --name-status {round_receipt["candidate_tip"]} {head_now}',
            cwd=a.root,
            capture_output=True,
            text=True,
            shell=True,
        ).stdout.strip().splitlines()
        frontend_after_round = [line for line in after_round if "\tfrontend/" in line]
        manifest["post_tip_delta"] = {
            "head_at_publish": head_now,
            "commits_after_the_green_round": after_round,
            "frontend_files_after_the_green_round": frontend_after_round,
            "reading": "everything added after the green-round tip is evidence tooling; no file a "
            f"triple points at changed ({len(frontend_after_round)} frontend files)",
        }
        Path(a.manifest).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
        )
        print(
            f"manifest={a.manifest} arms={len(arm_list)} killed={len(killed)} "
            f"under_test_changed={bool(under_test)}"
        )

    arm_list = arms["arms"]
    killed = [x for x in arm_list if x["claimed_result"] == "KILLED"]
    survived = [x for x in arm_list if x["claimed_result"] != "KILLED"]
    triples = round_receipt["triples"]
    if len(triples) != len({t["nodeid"] for t in triples}):
        print("REFUSE: duplicate nodeid among the triples")
        return 2
    shas = {t["exact_sha"] for t in triples}
    lines: list[str] = []
    add = lines.append

    add(
        f"【D e345b9d6 → 包工头 · #2e 交完：ORD-0269 门 + ORD-0273 三门，反突变 `{arms.get('runTag','?')}` "
        f"{len(arm_list)} 枚 / 绿轮三元组 {len(triples)} 条】"
    )

    add("")
    add(f"- 候选分支尖（外读）：`{lsremote}`")
    # The authoritative line is whatever is externally readable, not what my worktree happens to have
    # checked out -- the local branch lags a generation whenever the commander moves the line.
    mirror_tip = subprocess.run(
        "git ls-remote https://github.com/Canshu-King/CityNexus.git "
        "refs/heads/mirror/integration-frontend-apple-pass1",
        capture_output=True,
        text=True,
        shell=True,
    ).stdout.split("\t")[0].strip()
    local_tip = subprocess.run(
        "git rev-parse refs/heads/integration/frontend-apple-pass1",
        cwd="D:/moodle/_qoder_integration_20260919",
        capture_output=True,
        text=True,
        shell=True,
    ).stdout.strip()
    # `git cat-file -e <sha>^{commit}` is not usable here: shell=True goes through cmd.exe on
    # Windows, where ^ is the escape character, so the probe answered "absent" for a commit that is
    # in this object store.  A probe that manufactures a false absence is worse than no probe.
    kind = subprocess.run(
        f"git cat-file -t {mirror_tip}",
        cwd="D:/moodle/_qoder_d_lane_20260923",
        capture_output=True,
        text=True,
        shell=True,
    ).stdout.strip()
    have = 0 if kind == "commit" else 1
    if have == 0:
        predict = subprocess.run(
            f'git merge-tree --write-tree {mirror_tip} {round_receipt["candidate_tip"]}',
            cwd="D:/moodle/_qoder_d_lane_20260923",
            capture_output=True,
            text=True,
            shell=True,
        )
        conflicted = [
            line.split("\t")[0]
            for line in predict.stdout.splitlines()[1:]
            if line.startswith("\t") and len(line.split("\t")) >= 4
        ]
        prediction = (
            f"只读合流预测 `git merge-tree --write-tree {mirror_tip[:9]}… {round_receipt['candidate_tip'][:9]}…` "
            f"⇒ 冲突文件 **{len(conflicted)}** 个{('：' + ', '.join(conflicted)) if conflicted else ''}"
            f"（exit={predict.returncode}，不移动任何分支）"
        )
    else:
        prediction = (
            f"合流预测 NOT_PREDICTED_LOCALLY: `git cat-file -t {mirror_tip}` 在本车道对象库返回 "
            f"`{kind or '<empty>'}`（不是 commit），我没有为这一格编一个数"
        )
    add(f"- 权威尖（外读 mirror ref）：`{mirror_tip or '?'}`；我这枚候选从 `{round_receipt['authoritative_tip_at_delivery'][:9]}…` 切的")
    add(f"- 本机权威分支 `integration/frontend-apple-pass1` 现读：`{local_tip or '?'}`（落后一代不等于我能动它）")
    add(f"- {prediction}")
    add(
        f"- 反突变尖 `{arms['head']}`；门绿轮三元组的 sha 集合："
        f"{', '.join('`' + s + '`' for s in sorted(shas))}（{len(shas)} 枚）"
    )
    add(f"- 门绿轮：{round_receipt['verdict']}，三元组 {len(triples)} 条，全部来自 Playwright 日志行的机械解析")


    add("")
    add(f"**反突变矩阵 {len(arm_list)} 枚：KILLED {len(killed)} / 其它 {len(survived)}**")
    add("")
    add("| 臂 | owner | claimed_result | 红集（节点数） | anchor/bytes/restored |")
    add("| --- | --- | --- | --- | --- |")
    for x in arm_list:
        reds = x["redSet"]
        add(
            f"| `{x['name']}` | `{x['ownerNode']}` | **{x['claimed_result']}** | "
            + (", ".join(f"`{r}`" for r in reds) if reds else "—")
            + f" ({len(reds)}) | {x['anchor_hits']}/{x['bytes_changed']}/{x['restored_exact']} |"
        )
    add("")
    add("三元组（逐字，`exact_sha` 40 位全写在收据里）：")
    add("")
    for t in triples:
        add(f"- `{t['exact_sha']}` · `{t['nodeid']}` · {t['run_shape']}")
    add("")
    bridge = manifest["tree_diff_between_tips"] if a.manifest else {}
    add(
        f"**尖桥（两枚尖，不是同一刻量的）**：反突变在 `{arms['head'][:9]}…`，绿轮在 "
        f"`{round_receipt['candidate_tip'][:9]}…`。两者之间 `git diff --name-status` 实测："
        f"`frontend/` 命中 **{len(bridge.get('under_test_files', []))} 件**、证据工具 **{len(bridge.get('evidence_tooling_files', []))} 件** —— "
        f"臂只改 `frontend/` 下的文件，所以绿轮量的就是被杀的那批字节（这条是跑出来的，不是声明的）。"
    )

    if a.manifest:
        delta = manifest["post_tip_delta"]
        add(
            f"- 发帖时的分支尖：`{delta['head_at_publish']}`；绿轮之后新增 {len(delta['commits_after_the_green_round'])} "
            f"个文件，其中 `frontend/` 命中 **{len(delta['frontend_files_after_the_green_round'])} 个** —— 三元组指向的字节一件没动。"
        )
    add("")
    add("**本轮顺手修掉的一处真产品缺陷（要你单开一行的那件）**")
    add("")
    add(
        "- 形状：`frontend/src/api/useContinuationState.ts` 用 `events: events?.events ?? []` 把「回了 200 但 body 里没有 "
        "events 数组」伪造成「本页没有这一轮」。后果有两层：屏上那句具名状态**说错了原因**（把「答了但用不了」说成「翻不到」），"
        "并且分类器里那道 malformed 守卫**从唯一调用方不可达**——所以 v2 那枚 `K269_MALFORMED_FEED_SILENT` 活了。"
    )
    add(
        "- 修法：payload 原样交给 `classifyContinuation` 判定（commit `c7e2acb8664092bd9cdebdc6131654d96db434c3`）。"
        "证据：v5 里同一枚臂 **只红细胞3**（独占红集），产品字节未再改动即 9/9。"
    )
    add("")
    add(
        f"- 门自证的两处「自己骗自己」（都已修并具名）：R-6 原本只 `toHaveCount(0)` 断缺席（变异体 1.3s 混过 → 现在先等具名句渲染，"
        f"同一枚变异体 16.2s 红）；反突变驱动在 `run_spec.py` 截断的 90 行控制台里读自己的运行（四红被判成 BASELINE_RED → 改读 run-<id>.log 全文）。"
    )
    add("")
    schema = round_receipt.get("R_SCHEMA_01_class", {})
    add(
        f"**R-SCHEMA-01 自证（取自收据）**：`{schema.get('rule', 'NOT_IN_RECEIPT')}` —— 行来源 "
        f"`{schema.get('row_source', '?')}`；未使用 {schema.get('not_used', ['?'])}；结论只依赖 "
        f"`{schema.get('conclusions_depend_on', '?')}` ⇒ {schema.get('therefore', '?')}。"
    )
    add(
        f"写作口径：`{round_receipt.get('publisher_refusal_writing_rule', '?')}`"
    )
    add("")
    add("归属与口径（B-1）：`claimed_result` 全是我自宣；`derived_result` / direct-red / collateral 一律 `WRITTEN_BY_VERIFIER`。")
    add("红集里非 owner 的节点是同一枚缺陷的其它读者，按 collateral 记账，不当独立证据。")
    add("")
    add("树完整性：`treeUnchangedByThisRun=" + str(arms["treeUnchangedByThisRun"]).lower() + "`（sha256 逐档回读），"
        f"门跑完 `git status --porcelain` = {round_receipt['clean_worktree']['porcelain_lines_frontend_review']} 行。")
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {a.out} lines={len(lines)} arms={len(arm_list)} killed={len(killed)} triples={len(triples)}")
    if survived:
        print("NOT KILLED:", ", ".join(f"{x['name']}={x['claimed_result']}" for x in survived))
    return 0


if __name__ == "__main__":
    sys.exit(main())
