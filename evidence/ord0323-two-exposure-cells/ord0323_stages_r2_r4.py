"""ORD-0323 delivery stages, on top of `ord0323_deliver.py`'s measured state.

Importing that module re-reads git, proves the candidate's lineage, and publishes the review ref; this file
adds publish -> receipt -> block -> post. Kept in two files because the shell here mangles long quoted
heredocs, not because the logic is separable.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0323_deliver as D  # noqa: E402

ARMS = D.ARM_KEYS
REA, SH = D.REA, D.SH
DIR = D.DIR


def publish(local: pathlib.Path, name: str):
    original = name
    want = D.blob_of(local)
    taken = {r["path"]: r["blob"] for r in D.PUBLISHED}
    stem, dot, ext = name.rpartition(".")
    n = 2
    while f"{DIR}/{name}" in taken and taken[f"{DIR}/{name}"] != want:
        name = f"{stem}_r{n}{dot}{ext}"
        n += 1
    if taken.get(f"{DIR}/{name}") == want:
        print("already published, skipping", name, want)
        return
    if name != original:
        print("revised name (published paths are never rewritten):", original, "->", name)
    D.push(local, name)
    got = D.api(f"/repos/{D.GH}/contents/{DIR}/{name}?ref={D.BRC}")
    if got.get("sha") != D.blob_of(local):
        raise SystemExit(f"{name} did not read back as its own blob")
    D.PUBMAP[pathlib.Path(str(local)).name] = name
    (D.WORK / "ord0323_publish_map.json").write_text(
        json.dumps(D.PUBMAP, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    D.PUBLISHED.append({"path": f"{DIR}/{name}", "blob": got["sha"],
                        "bytes": int(got.get("size") or len(local.read_bytes()))})
    # commit the row list after every file: a pass that dies halfway would otherwise re-push 100+ files
    # under _r2 names, because the reload door only knows about the last written list.
    (D.WORK / "ord0323_publish_rows.json").write_text(
        json.dumps(D.PUBLISHED, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("published", name, got["sha"], len(local.read_bytes()), "B")


def stage_publish():
    subprocess_fetch()
    # instruments whose bytes have not moved keep their published r1 names; the guard refuses a same-name
    # different-bytes publish, so anything re-measured against the new candidate goes out as _r2.
    keep = [(D.SPIKE / "ord0323_run_arms.py", "ord0323_run_arms.py"),
            (D.SPIKE / "ord0323_r3_readings.py", "ord0323_r3_readings.py"),
            (D.WORK / "ord0323_arms_matrix.json", "ord0323_arms_matrix_r1.json"),
            (D.WORK / "r3" / "r3_before.json", "r3_before_9a669c8b_r4.json"),
            (D.WORK / "r3" / "r4_before_base.json", "r4_before_9a669c8b_r4.json"),
            (D.WORK / "r3" / "r4_selftest.json", "r4_selftest.json")]
    fresh = [(D.SPIKE / "ord0323_run_arms_r2.py", "ord0323_run_arms_r2.py"),
             (D.SPIKE / "ord0323_r4_readings.py", "ord0323_r4_readings_r2.py"),
             (D.SPIKE / "ord0323_deliver.py", "ord0323_deliver_r2.py"),
             (D.SPIKE / "ord0323_stages.py", "ord0323_stages_r2.py"),
             (D.SPIKE / "ord0323_block.py", "ord0323_block_r2.py"),
             (D.WORK / D.MATRIX_NAME, D.MATRIX_NAME),
             (D.SPIKE / "ord0323_matrix_from_disk.py", "ord0323_matrix_from_disk.py"),
             (D.SPIKE / "ui_exposure_taint_ast_r5.cjs", "ui_exposure_taint_ast_r5.cjs"),
             (D.SPIKE / "ord0323_r5_readings.py", "ord0323_r5_readings.py"),
             (D.WORK / "ord0323_r5_readings.json", "ord0323_r5_readings_r3.json"),
             (D.WORK / "r5_before_tree.json", "r5_before_tree_r3.json"),
             (D.WORK / "r5_after_tree.json", "r5_after_tree_r3.json"),
             (D.SPIKE / "ui_exposure_taint_ast_r6.cjs", "ui_exposure_taint_ast_r6.cjs"),
             (D.SPIKE / "ord0323_r6_readings.py", "ord0323_r6_readings.py"),
             (D.WORK / "ord0323_r6_readings.json", "ord0323_r6_readings_r3.json"),
             (D.WORK / "r6_before_tree.json", "r6_before_tree_r3.json"),
             (D.WORK / "r6_after_tree.json", "r6_after_tree_r3.json"),
             (D.SPIKE / "ord0323_widen_q71.py", "ord0323_widen_q71.py"),
             (D.SPIKE / "ord0323_widen_q71_r2.py", "ord0323_widen_q71_r2.py"),
             (D.SPIKE / "ord0323_q68_amend.py", "ord0323_q68_amend.py"),
             (D.SPIKE / "ord0323_q68_amend_r2.py", "ord0323_q68_amend_r2.py"),
             (D.SPIKE / "ord0323_four_forms.py", "ord0323_four_forms.py"),
             (D.SPIKE / "ord0323_four_forms_arms.py", "ord0323_four_forms_arms.py"),
             (D.SPIKE / "ord0323_four_forms_shapes.py", "ord0323_four_forms_shapes.py"),
             (D.SPIKE / "ord0323_four_forms_facts.py", "ord0323_four_forms_facts.py"),
             (D.SPIKE / "ord0323_f4_instrument.py", "ord0323_f4_instrument.py"),
             (D.SPIKE / "ord0323_signoff_criterion.py", "ord0323_signoff_criterion.py"),
             (D.SPIKE / "ord0323_split_legs.py", "ord0323_split_legs.py"),
             (D.SPIKE / "ord0323_split_runner.py", "ord0323_split_runner.py"),
             (D.SPIKE / "ord0323_add_q68.py", "ord0323_add_q68.py"),
             (D.SPIKE / "ord0323_perleg.py", "ord0323_perleg.py"),
             (D.SPIKE / "ord0323_clean_rebuild.py", "ord0323_clean_rebuild.py"),
             (D.SPIKE / "ord0323_retarget.py", "ord0323_retarget.py"),
             (D.WORK / "ord0323_r3_readings.json", "ord0323_r3_readings_r4.json"),
             (D.WORK / "ord0323_r4_readings.json", "ord0323_r4_readings_r4.json"),
             (D.WORK / "r3" / "r3_after.json", "r3_after_candidate_r4.json"),
             (D.WORK / "r3" / "r4_after_candidate.json", "r4_after_candidate_r4.json")]
    for local, name in keep + fresh:
        publish(local, name)
    for shape, r in SH.items():
        rid = r["run_id"]
        publish(D.WORK / f"ord0323_{rid}.json", D.report_name(shape))
        for arm in ARMS:
            f = D.WORK / f"e2e_{rid}" / "ord0323" / f"{rid}__{arm}.json"
            if not f.exists():
                raise SystemExit(f"no per-arm evidence for {shape}/{arm}: {f}")
            publish(f, D.arm_name(shape, arm))
    (D.WORK / "ord0323_publish_rows.json").write_text(
        json.dumps(D.PUBLISHED, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("published files:", len(D.PUBLISHED))


def subprocess_fetch():
    import subprocess
    subprocess.run(["git", "-C", str(D.FROZEN), "fetch", "-q", D.URL, "+refs/heads/*:refs/qoder-scan/*"],
                   capture_output=True, timeout=900)


def _pf(body, name):
    """Look a file's r4 lines up by name: with three files scanned, a positional index silently moves."""
    return next(x for x in body["per_file_lines"] if x["file"] == name)


def stage_receipt():
    cells = []

    def add(cell, verdict, readings, why):
        readings = dict(readings)
        print("  cell:", cell)
        D.C.cite(why, readings, D.PATS)
        cells.append({"cell": cell, "claimed_result": verdict, "derived_result": None,
                      "why": why, "readings": readings})

    f1 = REA["fixed"]["N1"]
    b1 = REA["cell1_baseline_sink"]["N1"]
    l1 = REA["cell1_leak_beside_fields"]["N1"]
    d1 = REA["cell1_fields_gone"]["N1"]
    add("格一 ProductErrorBoundary.tsx 的两向断言", "MET",
        {"file": D.CELL1, "order_named_lines": "104-105",
         "baseline_blob": D.CELL1_BLOB, "candidate_blob": D.CELL1_CAND_BLOB,
         "fixed_N1_status": SH["fixed"]["per_arm"]["N1"],
         "fixed_fold_text": f1["error_detail_text"], "fixed_leaks": f1["leaked_needles_still_on_screen"],
         "fixed_console_error_count": f1["console_error_count"], "fixed_overlay_hosts": f1["overlay_hosts"],
         "baseline_shape_leaks": b1["leaked_needles_still_on_screen"],
         "baseline_shape_fold_text": b1["error_detail_text"],
         "baseline_status": SH["cell1_leak_beside_fields"]["per_arm"]["N1"],
         "baseline_leaks": l1["leaked_needles_still_on_screen"], "baseline_error_head": l1["error_head"],
         "fields_gone_status": SH["cell1_fields_gone"]["per_arm"]["N1"],
         "fields_gone_leaks": d1["leaked_needles_still_on_screen"], "fields_gone_error_head": d1["error_head"],
         "arms_matrix": DIR + "/" + D.MATRIX_NAME,
         "evidence": [DIR + "/" + D.arm_name(s, "N1") for s in
                      ("fixed", "cell1_baseline_sink", "cell1_leak_beside_fields", "cell1_fields_gone")]},
        "格一原样把接来的两样东西印在屏幕上：异常正文与组件帧。把尖上那份文件放回工作树、跑同一枚 N1，屏幕上量到 "
        + repr(b1["error_detail_text"][:46]) + "，命中指针 "
        + json.dumps(b1["leaked_needles_still_on_screen"], ensure_ascii=False)
        + "（帧里带 http:// 开头的源文件路径与行列号，来自这台设备的构建目录）。本候选 N1 得 "
        + SH["fixed"]["per_arm"]["N1"] + "，折子里只剩这台设备自己量的五项 "
        + repr(f1["error_detail_text"][:64]) + "，命中 "
        + json.dumps(f1["leaked_needles_still_on_screen"], ensure_ascii=False) + "；同一趟 console 仍收到 "
        + str(f1["console_error_count"]) + " 条错误，屏幕外挂元素 "
        + json.dumps(f1["overlay_hosts"], ensure_ascii=False) + " —— 没有覆盖层替我把原文再印一遍。"
        "两向各配一枚反件：只把原文放回（字段仍全）N1 得 " + SH["cell1_leak_beside_fields"]["per_arm"]["N1"]
        + "、命中 " + json.dumps(l1["leaked_needles_still_on_screen"], ensure_ascii=False) + "、报错句 "
        + repr(l1["error_head"][:56]) + "；只拆字段（原文仍不在）N1 得 "
        + SH["cell1_fields_gone"]["per_arm"]["N1"] + "、命中 "
        + json.dumps(d1["leaked_needles_still_on_screen"], ensure_ascii=False) + "、报错句 "
        + repr(d1["error_head"][:56]) + "。两枚反件都不许把 N2/N3 变红，矩阵逐条记着。")

    f2, f3 = REA["fixed"]["N2"], REA["fixed"]["N3"]
    b2, b3 = REA["cell2_baseline_throw"]["N2"], REA["cell2_baseline_throw"]["N3"]
    l2 = REA["cell2_status_frozen"]["N2"]
    d2, d3 = REA["cell2_fields_blind"]["N2"], REA["cell2_fields_blind"]["N3"]
    add("格二 JourneyInboxWorkbench.tsx 的两向断言（三个出屏口）", "MET",
        {"file": D.CELL2, "order_named": ":88 与出屏口 687/691/731",
         "baseline_blob": D.CELL2_BLOB, "candidate_blob": D.CELL2_CAND_BLOB,
         "fixed_N2_status": SH["fixed"]["per_arm"]["N2"], "fixed_N3_status": SH["fixed"]["per_arm"]["N3"],
         "fixed_message_text": f2["message_text"], "fixed_pending_text": f2["pending_text"],
         "fixed_fold_text": f3["fold_text"], "fixed_leaks": f2["leaked_needles_still_on_screen"],
         "baseline_shape_N2_status": SH["cell2_baseline_throw"]["per_arm"]["N2"],
         "baseline_shape_N2_leaks": b2["leaked_needles_still_on_screen"],
         "baseline_shape_N3_leaks": b3["leaked_needles_still_on_screen"],
         "baseline_N2_status": SH["cell2_status_frozen"]["per_arm"]["N2"],
         "baseline_N3_status": SH["cell2_status_frozen"]["per_arm"]["N3"],
         "baseline_N2_leaks": l2["leaked_needles_still_on_screen"],
         "fields_blind_N2_status": SH["cell2_fields_blind"]["per_arm"]["N2"],
         "fields_blind_N3_status": SH["cell2_fields_blind"]["per_arm"]["N3"],
         "fields_blind_N2_leaks": d2["leaked_needles_still_on_screen"],
         "fields_blind_N2_error_head": d2["error_head"], "fields_blind_N3_error_head": d3["error_head"],
         "arms_matrix": DIR + "/" + D.MATRIX_NAME,
         "evidence": [DIR + "/" + D.arm_name(s, a) for s in
                      ("fixed", "cell2_baseline_throw", "cell2_status_frozen", "cell2_fields_blind")
                      for a in ("N2", "N3")]},
        "格二的原话出口在 :88：它把回复里的句子重铸成这条腿自己的话，再由 687 的状态行、691 的确认折、731 的待审"
        "警告三处印出来。把尖上那份文件放回工作树：N2 得 " + SH["cell2_baseline_throw"]["per_arm"]["N2"]
        + "、屏幕量到 " + json.dumps(b2["leaked_needles_still_on_screen"], ensure_ascii=False) + "，N3 屏幕量到 "
        + json.dumps(b3["leaked_needles_still_on_screen"], ensure_ascii=False)
        + " —— 三处出屏口都被这枚反件证实确实在用。本候选 N2/N3 都 " + SH["fixed"]["per_arm"]["N2"]
        + "，状态行读 " + repr(f2["message_text"][:36]) + "、待审读 " + repr(f2["pending_text"][:30])
        + "、确认折读 " + repr(f3["fold_text"][:36]) + "，三处命中 "
        + json.dumps(f2["leaked_needles_still_on_screen"], ensure_ascii=False)
        + "；允许字段两侧各自带着 500/503 与 application/json，且两条腿不许互换。只把原话加在设备句旁边（字段仍全）："
        "N2/N3 得 " + SH["cell2_status_frozen"]["per_arm"]["N2"] + "/"
        + SH["cell2_status_frozen"]["per_arm"]["N3"] + "、命中 "
        + json.dumps(l2["leaked_needles_still_on_screen"], ensure_ascii=False)
        + "；只拆字段（原话仍不在）：N2/N3 得 " + SH["cell2_fields_blind"]["per_arm"]["N2"] + "/"
        + SH["cell2_fields_blind"]["per_arm"]["N3"] + "、命中 "
        + json.dumps(d2["leaked_needles_still_on_screen"], ensure_ascii=False) + "、报错句 "
        + repr(d2["error_head"][:52]) + " —— 两观测量各自可红，不互替。")

    R3 = D.R3
    add("要件③：r3 尺量我自己那一枚，改前/改后命中行", "MET",
        {"ruler_blob_commander": D.R3_BLOB, "ruler_blob_measured": R3["ruler"]["local_git_blob_hash"],
         "ruler_selftest": R3["ruler"]["selftest"], "before": R3["before"], "after": R3["after"],
         "shapes_gone": R3["shape_identity"]["shapes_gone"], "shapes_new": R3["shape_identity"]["shapes_new"],
         "renumbered": R3["shape_identity"]["same_shape_renumbered"], "reading": R3["reading"],
         "cell1_after": R3["named_cells"]["cell1_ProductErrorBoundary:104-105"]["after"],
         "candidate": D.CAND, "base": D.BASE,
         "artifact": DIR + "/" + D.pub("ord0323_r3_readings.json"),
         "before_artifact": DIR + "/" + D.pub("r3_before.json"),
         "after_artifact": DIR + "/" + D.pub("r3_after.json")},
        "尺是他那把，逐位回验：本地 " + R3["ruler"]["local_git_blob_hash"] + " 与他贴的 " + D.R3_BLOB
        + " 相同，自检 " + R3["ruler"]["selftest"] + "。同一枚文件在尖 " + D.BASE + " 与候选 " + D.CAND
        + " 上各跑一次：改前 " + str(R3["before"]["hit_count"]) + " 命中、改后 " + str(R3["after"]["hit_count"])
        + "。按 (rule, file, snippet) 认形而不是认行号，消掉的形状是 "
        + json.dumps([f"{x['rule']}@{x['file']}:{x['lines_before']}" for x in R3["shape_identity"]["shapes_gone"]],
                     ensure_ascii=False) + " —— 正是他点名的两行；新增形状 "
        + json.dumps(R3["shape_identity"]["shapes_new"], ensure_ascii=False) + "；改后仍报 "
        + str(len(R3["shape_identity"]["same_shape_renumbered"])) + " 类。尺只认图案，句子内容归 e2e 两向断言。")

    add("要件①⑤：代次、分支与权威线", "MET",
        {"order_named_base": D.BASE, "candidate": D.CAND, "branch": D.BRANCH,
         "remote_readback": D.REMOTE_SHA, "commits_on_branch": D.COMMITS,
         "authority_ref_watched": D.AUTH_REF, "live_tip_now": D.NEW_TIP, "live_tip_meta": D.TIP_META,
         "gap_commits": D.TIP_GAP, "tip_files_touched": len(D.TIP_FILES),
         "tip_frontend_files": len(D.TIP_FRONTEND),
         "cell1_blob_at_both": D.BLOB_PAIR[D.CELL1], "cell2_blob_at_both": D.BLOB_PAIR[D.CELL2],
         "merge_tree": D.PREDICT,
         "refs_read_before_and_after": {"before": D.AUTHORITY_BEFORE, "after": D.AUTHORITY_AFTER},
         "moved_during_my_run": D.MOVED, "push_targets_only": D.PUSH_TARGETS,
         "moves_are_mine": D.MOVES_NOT_MINE,
         "authority_ref_moves_by_me": 0, "force_pushes_by_me": 0},
        "基线按他点名的那一枚现读 " + D.BASE + "，候选 " + D.CAND + " 在其上 " + str(D.COMMITS)
        + " 笔；分支只开新名 " + D.BRANCH + "，ls-remote 回读 " + D.REMOTE_SHA
        + "，我这趟 push 命令里只出现这一枚 ref（" + json.dumps(D.PUSH_TARGETS, ensure_ascii=False)
        + "），无 force。权威线 " + D.AUTH_REF + " 在我两次读取之间从 " + str(D.AUTHORITY_BEFORE.get(D.AUTH_REF))[:12]
        + " 走到 " + D.NEW_TIP + "（" + D.TIP_META + "，不是我：那个 commit 的作者与标题记在 readings 里，"
        "里面没有我的候选），" + json.dumps(list(D.MOVED.keys()), ensure_ascii=False) + " 一并列出。"
        "线与线的关系：我的基线是新尖的祖先，差 " + str(D.TIP_GAP) + " 笔，那 " + str(len(D.TIP_FILES))
        + " 个文件里前端 " + str(len(D.TIP_FRONTEND)) + " 个，我那两格在两尖上的 blob 逐位相同（"
        + D.BLOB_PAIR[D.CELL1]["at_ordered_base"] + "、" + D.BLOB_PAIR[D.CELL2]["at_ordered_base"]
        + "），merge-tree 对新尖预测退出 " + str(D.PREDICT["rc"]) + "、冲突行 " + str(D.PREDICT["conflict_lines"])
        + "。我没有自作主张换基座；要落到 " + D.NEW_TIP + " 只把这 " + str(D.COMMITS) + " 笔平移，三枚 blob 不变，"
        "平移后我重跑整套反件再报数。")

    add("要件④：没有靠改断言换绿、没有跳过", "MET",
        {"spec": D.SPEC, "spec_blob": D.SPEC_CAND_BLOB, "expect_calls": D.EXPECT_CALLS,
         "skip_or_fixme_lines": D.SKIP_HITS,
         "own_commits": [c[:12] for c in D.OWN_COMMITS],
         "own_commit_count": len(D.OWN_COMMITS), "own_file_count": len(D.OWN_FILES),
         "files_changed_by_this_order": D.OWN_FILES,
         "commits_between_base_and_candidate": D.COMMITS,
         "files_differing_base_to_candidate": len(D.CHANGED),
         "commits_carried_by_the_base_not_mine": D.FOREIGN_COMMITS,
         "pre_existing_e2e_touched": [c for c in D.OWN_FILES
                                      if c.startswith("frontend/e2e/") and c != D.SPEC],
         "second_commit_reason": "第一趟 cell1_baseline_sink 里 N1 超时：那枚反件把整份文件换回尖上的版本，"
                                 "而我的臂用只有本候选才有的 data-testid 开折子。改成按结构开折，并把那个 "
                                 "testid 从产品改动里撤掉。",
         "reporter_of_the_measured_run": DIR + "/" + D.report_name("fixed")},
        "本单自己署名的提交 " + str(len(D.OWN_COMMITS)) + " 笔、动到 " + str(len(D.OWN_FILES)) + " 枚文件："
        + json.dumps(D.OWN_FILES, ensure_ascii=False) + "；候选落在现尖上，所以「具名基线..候选」这段是 "
        + str(D.COMMITS) + " 笔、" + str(len(D.CHANGED)) + " 枚文件与基线不同，其中不是我这单的 "
        + str(len(D.FOREIGN_COMMITS)) + " 笔（" + json.dumps(D.FOREIGN_COMMITS, ensure_ascii=False)
        + "）我不算进自己名下。我这 " + str(len(D.OWN_FILES)) + " 枚里既有 e2e 文件 "
        + str(len([c for c in D.OWN_FILES if c.startswith('frontend/e2e/')])) + " 枚（本单新 spec "
        + json.dumps([c for c in D.OWN_FILES if c.startswith('frontend/e2e/')], ensure_ascii=False)
        + "），动到的既有 e2e 文件 "
        + str(len([c for c in D.OWN_FILES if c.startswith('frontend/e2e/') and c != D.SPEC]))
        + " 枚；spec 里 skip/fixme 命中行 " + json.dumps(D.SKIP_HITS, ensure_ascii=False) + "（空集）；expect( 出现 "
        + str(D.EXPECT_CALLS) + " 次，spec blob " + D.SPEC_CAND_BLOB
        + "。第二笔提交只把开折子的定位器换成结构性定位并撤掉我加的 testid，目的是让尖上那份文件也能被同一枚臂量到"
          "（第一趟那格超时、一条读数都没有），不是把红改成绿；断言一条没减。")

    R4 = D.R4
    add("要件③补测：取代 r3 的 r4（AST 汇绑定）在同一格上的前后读数", "MET",
        {"ruler_blob_published_by_S4": D.R4_BLOB, "ruler_blob_measured_here": R4["ruler"]["local_git_hash_object"],
         "ruler_typescript": R4["ruler"]["typescript"], "ruler_selftest": R4["ruler"]["selftest_verdict"],
         "selftest_assertions": R4["ruler"]["selftest_assertions_met"],
         "supersedes_r3": R4["ruler"]["supersedes"],
         "before": R4["before"], "after": R4["after"],
         "per_file_lines": R4["per_file_lines"], "traces_remaining": R4["traces_remaining"],
         "reading": R4["reading"], "gone": R4["gone"], "remaining": R4["remaining"],
         "artifact": DIR + "/" + D.pub("ord0323_r4_readings.json"),
         "before_artifact": DIR + "/r4_before_9a669c8b_r3.json",
         "after_artifact": DIR + "/r4_after_candidate_r3.json",
         "generator": DIR + "/ord0323_r4_readings_r2.py"},
        "r4 的尺身我按 blob 认：" + R4["ruler"]["local_git_hash_object"] + " 与 S4 上架的 " + D.R4_BLOB
        + " 逐位相同，typescript " + R4["ruler"]["typescript"] + "，自检 " + R4["ruler"]["selftest_verdict"] + " "
        + R4["ruler"]["selftest_assertions_met"] + "。两代同一对文件各量一次：尖 " + D.BASE + " 上报 "
        + str(R4["before"]["hit_count"]) + " 形，全是我这两格里被点名的行（" + json.dumps(R4["before"]["cells"])
        + "）；本候选 " + D.CAND + " 上报 " + str(R4["after"]["hit_count"]) + " 形，按文件分是 "
        + json.dumps(R4["per_file_lines"], ensure_ascii=False) + " —— 格一从 "
        + str(len(_pf(R4, "ProductErrorBoundary.tsx")["lines_before"])) + " 形到 "
        + str(len(_pf(R4, "ProductErrorBoundary.tsx")["lines_after"])) + " 形，格二那三形还在，行号被我自己新增的 "
        + str(_pf(R4, "JourneyInboxWorkbench.tsx")["shift_if_same_count"]) + " 行推下去（"
        + json.dumps({"before": _pf(R4, "JourneyInboxWorkbench.tsx")["lines_before"],
                      "after": _pf(R4, "JourneyInboxWorkbench.tsx")["lines_after"]}, ensure_ascii=False) + "）。"
        "r4 判的是流不是内容：一个汇只要可能被交给 `error.message`，它就报形，不论这句话里此刻装的是谁的词。"
        "所以这一格要么按 r4 关掉那八个 catch 站点（见下一格的方向请示），要么由 e2e 那两向断言判内容 —— "
        "内容侧我的读数是 " + json.dumps(R4["interpretation_limit"], ensure_ascii=False)[:150] + "。")

    leg_rows = {c: REA["fixed"][c] for c in D.LEG_KEYS}
    asked = {c: leg_rows[c]["status_asked"] for c in D.LEG_KEYS}
    bad_needle = [c for c in D.LEG_KEYS if leg_rows[c]["needles_found"]]
    bad_status = [c for c in D.LEG_KEYS if not leg_rows[c]["status_in_slot"]]
    bad_foreign = [c for c in D.LEG_KEYS if leg_rows[c]["foreign_status_found"]]
    frozen_bad = [c for c in D.LEG_KEYS if REA["cell2_status_frozen"][c]["foreign_status_found"]]
    frozen_ok = [c for c in D.LEG_KEYS if not REA["cell2_status_frozen"][c]["foreign_status_found"]]
    q68a, q68b = REA["fixed"]["Q68a"], REA["fixed"]["Q68b"]
    slot_texts = {c: leg_rows[c]["slot_text"] for c in D.LEG_KEYS}
    add("要件②扩到 D 数出的九格（T05-T13）与 Q68 那一格：逐臂双向", "MET",
        {"triage_artifact": "evidence/ord0320-triage-d/ord0320_triage_r2.json",
         "triage_blob": D.TRIAGE_BLOB, "cells_named_by_D": D.TRIAGE_CELLS,
         "file": D.CELL2, "blob_at_candidate_parent": D.CELL2_BASE_BLOB,
         "blob_at_candidate": D.CELL2_CAND_BLOB,
         "leg_keys": list(D.LEG_KEYS), "asked_status_per_leg": asked,
         # (sha, nodeid, shape) per leg, and the shapes where that leg actually went red
         "signed_as": {a: {"sha": D.CAND, "nodeid": REA["fixed"][a]["nodeid"], "shape": "fixed",
                           "red_in": sorted(s for s in SH if SH[s]["per_arm"][a] == "failed")}
                       for a in D.LEG_KEYS + ("Q68a", "Q68b", "Q68c", "Q68d")},
         "legs_with_a_needle_on_screen": bad_needle, "legs_missing_their_own_status": bad_status,
         "legs_showing_another_leg_status": bad_foreign, "slot_texts": slot_texts,
         "frozen_shape": {"legs_still_green": frozen_ok, "legs_reddened": frozen_bad,
                          "arm_status": {c: SH["cell2_status_frozen"]["per_arm"][c] for c in D.LEG_KEYS}},
         "q68": {"file": D.Q68_SHEET_FILE,
                 "code_arm_card": q68a["card_text"], "code_in_card": q68a["code_in_card"],
                 "prose_arm_code_slot": q68b["uppercased_prose_in_code_slot"],
                 "prose_arm_fold": q68b["reason_fold_text"],
                 "prose_arm_attributed": q68b["attributed_sentence_in_fold"],
                 "prose_arm_label": q68b["server_label_present"],
                 "slot_back": {"Q68a": SH["cell3_code_slot_back"]["per_arm"]["Q68a"],
                               "Q68b": SH["cell3_code_slot_back"]["per_arm"]["Q68b"]},
                 "ruling": "Q68=「编号槽只准放编号」；句子按 Q67=① 留在带归因标签的技术详情里"},
         "named_source_lines": {
             "cell2_origin_throw": {"file": D.CELL2, "at_ordered_base": D.CELL2_ORIGIN_BASE,
                                    "at_candidate": D.CELL2_ORIGIN_CAND},
             "q68_prose_into_code_slot": {"file": D.Q68_SHEET_FILE, "at_ordered_base": D.Q68_FALLBACK_BASE,
                                          "at_candidate": D.Q68_FALLBACK_CAND}},
         "arms_matrix": DIR + "/" + D.MATRIX_NAME},
        "D 的分桶把钱包那枚文件数成九格：" + json.dumps(D.TRIAGE_CELLS, ensure_ascii=False)
        + "（T05 是折子，T06-T13 是八个 catch 站点，锚点行与逐行依据在她件 " + D.TRIAGE_BLOB + " 的 rows）。"
        "第一趟我只闭了源头 :" + json.dumps(D.CELL2_ORIGIN_BASE, ensure_ascii=False) + " 那一行（同一句在候选上"
        "现读 " + json.dumps(D.CELL2_ORIGIN_CAND, ensure_ascii=False) + "），r4 仍报 3 形：汇接的还是 "
        "`error.message` 这条流，而被拒的回复也可能以 fetch 的"
        " TypeError 或正文解析异常走进同一个汇。这一趟八个站点全部改走产品**已有**的通道（classifyReadFailure + "
        "copyFor 查表），没有一个站点把异常正文写进渲染态；机器位只放这台设备量到的 http_status / content_type / "
        "evidence kind。八条腿各一枚臂、各自一次全新状态码 " + json.dumps(asked, ensure_ascii=False)
        + "，逐臂读数：屏上有原话的腿 " + json.dumps(bad_needle, ensure_ascii=False) + "、缺自己状态的腿 "
        + json.dumps(bad_status, ensure_ascii=False) + "、把别腿状态顶上的腿 " + json.dumps(bad_foreign, ensure_ascii=False)
        + "。归因单独钉一枚反件（所有机器位印成 503）：问 503 的腿 " + json.dumps(frozen_ok, ensure_ascii=False)
        + " 照过，其余 " + json.dumps(frozen_bad, ensure_ascii=False) + " 立刻红 —— 说不清自己是哪条请求的汇不算量到。"
        "Q68 那一格是另一枚尺（r4）看得见、r3 看不见的形：" + json.dumps(D.Q68_SHEET_FILE, ensure_ascii=False)
        + " 改前 :" + json.dumps(D.Q68_FALLBACK_BASE, ensure_ascii=False)
        + " 那行在服务器没给编号时退回 `detail.slice(0, 60).toUpperCase()`，把句子截断大写后塞进「服务器回的原因编号是 …」"
          "（同一行式在候选上现读 " + json.dumps(D.Q68_FALLBACK_CAND, ensure_ascii=False) + "）。"
        "两臂各判一半：给了真编号的卡片仍显示编号（" + str(bool(q68a["code_in_card"])) + "，读数 "
        + json.dumps(str(q68a["card_text"])[:90], ensure_ascii=False) + "）；只给句子的卡片，编号位上没有句子（"
        + str(not q68b["uppercased_prose_in_code_slot"]) + "），而句子仍在带标签的技术详情里（"
        + str(bool(q68b["attributed_sentence_in_fold"])) + " / 标签在不在 "
        + str(bool(q68b["server_label_present"])) + "）。反件只把删掉的退回行放回去：Q68a "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68a"]) + " 保持绿、Q68b "
        + str(SH["cell3_code_slot_back"]["per_arm"]["Q68b"]) + " 变红 —— 修的是「句子不许冒充编号」，不是「把那格清空」。")

    add("代次：两格候选、上一枚十格候选与本候选的字节关系", "MET",
        {"ordered_base": D.BASE, "prev_candidate": D.PREV_CAND, "prev_branch": D.PREV_BRANCH,
         "prev_remote_readback": D.PREV_REMOTE, "candidate": D.CAND, "branch": D.BRANCH,
         "candidate_parent": D.PARENT_LIVE, "parent_meta": D.TIP_META,
         "blob_rows_prev_two_cell_candidate_to_here": D.RECUT_ROWS, "recut_same": D.RECUT_SAME,
         "force_pushes_by_me": 0, "refs_created_by_me": [D.PREV_BRANCH, D.BRANCH]},
        "扩单要求基线现读。两格候选 " + D.PREV_CAND + " 挂在 " + D.PREV_BRANCH + "，架上回读 " + D.PREV_REMOTE
        + "，那枚 ref 我不移动也不 force（已发布坐标不重写）；十格候选重切到他当下的尖 " + D.PARENT_LIVE
        + "（" + str(D.TIP_META) + "）之上 = " + D.CAND + "，分支新名 " + D.BRANCH
        + "。逐枚说字节，不说空话：从两格候选到本候选，"
        + json.dumps([{"file": r["file"], "identical": r["byte_identical"]} for r in D.RECUT_ROWS],
                     ensure_ascii=False)
        + " —— 只有 `frontend/src/components/ProductErrorBoundary.tsx` 那枚逐位相同；"
          "格二那枚文件不同，是这趟按扩单把八个 catch 站点收进既有通道（就是要改的），spec 不同是这趟按 Q71 扩仪器；"
          "两格候选上的那些臂与读数不折算进本候选，本候选的矩阵、四把尺、e2e 全在 " + D.CAND + " 上重跑。")

    r5 = D.R5
    add("要件③：r5 在整棵模块图上量两代（现行尺是下一格的 r6）", "MET",
        {"ruler": r5["ruler"], "generations": r5["generations"], "tree_wide": r5["tree_wide"],
         "in_my_three_files": r5["in_my_three_files"], "reading": r5["reading"],
         "remaining_meaning": r5["remaining_meaning"],
         "artifact": DIR + "/" + D.pub("ord0323_r5_readings.json"),
         "before_tree": DIR + "/" + D.pub("r5_before_tree.json"),
         "after_tree": DIR + "/" + D.pub("r5_after_tree.json"),
         "cross_check": {"r3_before": D.R3["before"]["hit_count"], "r3_after": D.R3["after"]["hit_count"],
                         "r4_before": D.R4["before"]["hit_count"], "r4_after": D.R4["after"]["hit_count"]}},
        "号令者点的尺是 r3（" + D.R3["ruler"]["local_git_blob_hash"] + "），但它已被 S4 的 r4/r5 血缘取代；"
        "r5 的用法按号令者自己那条实测：只有 --tree 建模块图，逐文件跑等于复现 r4。所以两代都用 "
        "git archive 导出 frontend 再 --tree 量：全树 " + str(r5["tree_wide"]["before_hits"]) + " → "
        + str(r5["tree_wide"]["after_hits"]) + "（差 " + str(r5["tree_wide"]["delta"]) + "），我这三枚文件上 "
        + str(len(r5["in_my_three_files"]["before"])) + " → "
        + str(len(r5["in_my_three_files"]["after"])) + " 个格子。按格子 id 数，" \
        + str(r5["in_my_three_files"]["counts"]["gone"]) + " 个消失、" \
        + str(r5["in_my_three_files"]["counts"]["only_at_candidate"]) + " 个只在新代出现；按形状身份"
        "（文件+规则，不含行号）数才是可主张的那个数：" + json.dumps(r5["in_my_three_files"]["by_shape_identity"]["cleared"], ensure_ascii=False)
        + " 清除 " + str(len(r5["in_my_three_files"]["by_shape_identity"]["cleared"])) + " 形、新增 "
        + json.dumps(r5["in_my_three_files"]["by_shape_identity"]["new"], ensure_ascii=False)
        + "，形数变化 " + str(len(r5["in_my_three_files"]["by_shape_identity"]["before"])) + " → "
        + str(len(r5["in_my_three_files"]["by_shape_identity"]["after"])) + "，差额由 PlanWithAiSheet 的行号位移解释 —— " + str(r5["remaining_meaning"])
        + " 全树里不属于我这三枚文件的变动文件 " + json.dumps(r5["tree_wide"]["changed_files_outside_my_three"], ensure_ascii=False)
        + "（" + str(len(r5["tree_wide"]["changed_files_outside_my_three"])) + " 枚）——"
          "本候选站在现尖上，那些是别的单已经落线的改动（列表就在读数件里），**不计进本单名下**；"
          "本单名下只有我这三枚文件按形状身份清掉的那 "
        + str(len(r5["in_my_three_files"]["by_shape_identity"]["cleared"])) + " 形。 同一代的 r3/r4 交叉核对："
        + str(D.R3["before"]["hit_count"])
        + "→" + str(D.R3["after"]["hit_count"]) + " 与 " + str(D.R4["before"]["hit_count"]) + "→"
        + str(D.R4["after"]["hit_count"]) + "。")

    r6 = D.R6
    add("要件③的现行尺：r6 在同一对代次上复量，并逐位对 r5 的差", "MET",
        {"ruler": r6["ruler"], "mode": r6["mode"], "generations": r6["generations"],
         "tree_wide": r6["tree_wide"], "in_my_three_files": r6["in_my_three_files"],
         "reading": r6["reading"], "cross_check_against_r5": r6["cross_check_against_r5"],
         "artifact": DIR + "/" + D.pub("ord0323_r6_readings.json"),
         "before_tree": DIR + "/" + D.pub("r6_before_tree.json"),
         "after_tree": DIR + "/" + D.pub("r6_after_tree.json")},
        "尺换成号令者现在手上那把 r6：本地 " + r6["ruler"]["local_git_hash_object"] + " 与他发布的 "
        + r6["ruler"]["published_blob"] + " 逐位相同（他那份路径 " + r6["ruler"]["published_path"]
        + " 在 commit " + r6["ruler"]["added_by_commit"] + " 上的 blob 也是这一枚，已 rev-parse 回验），"
          "自检 " + r6["ruler"]["selftest"] + "，模式臂 " + str(r6["ruler"]["n_mode_arms_met"]) + "/"
        + str(r6["ruler"]["n_mode_arms"]) + "。口径不自称，抄尺自己写的 scope："
        + json.dumps(r6["mode"]["scope_as_the_ruler_reports_it"], ensure_ascii=False)[:300] + "。"
        "两代都用 git archive 导出后 --tree 量：全树 " + str(r6["tree_wide"]["before_hits"]) + " → "
        + str(r6["tree_wide"]["after_hits"]) + "（差 " + str(r6["tree_wide"]["delta"]) + "），我这三枚 "
        + str(len(r6["in_my_three_files"]["before"])) + " → " + str(len(r6["in_my_three_files"]["after"]))
        + " 格，按形状身份清除 " + json.dumps(r6["in_my_three_files"]["by_shape_identity"]["cleared"], ensure_ascii=False)
        + " 共 " + str(len(r6["in_my_three_files"]["by_shape_identity"]["cleared"])) + " 形、新增 "
        + str(len(r6["in_my_three_files"]["by_shape_identity"]["new"])) + " 形，树内不属于这三枚的变动文件 "
        + str(len(r6["tree_wide"]["changed_files_outside_my_three"])) + " 枚。与 r5 的逐项对照记在件里："
        + json.dumps(r6["cross_check_against_r5"]["agreement"], ensure_ascii=False)
        + "；两把尺只在树级差 " + str(len(r6["cross_check_against_r5"]["cells_only_r5_reports"]["before"]))
        + " 枚（r5 多报 " + json.dumps(r6["cross_check_against_r5"]["cells_only_r5_reports"]["before"], ensure_ascii=False)
        + "，代次两侧同差 = " + str(r6["cross_check_against_r5"]["the_same_difference_on_both_generations"])
        + "），我这三枚文件的格子集合在两把尺上逐位相同，所以本单主张的那个差不依赖选哪把尺；"
          "那枚差额落在别人的文件上，我不裁它是真红还是假红。")

    def attr_hits(shape, arm):
        row = REA[shape][arm]
        for key in ("leaked_needles_in_attributes", "needles_found_in_attributes"):
            if key in row:
                return row[key]
        raise SystemExit(f"no Q71 attribute reading for {shape}/{arm}: {sorted(row)}")

    q68a, q68b = REA["fixed"]["Q68a"], REA["fixed"]["Q68b"]
    swept = {a: REA["fixed"][a]["attribute_pairs_swept"] for a in D.ARM_KEYS}
    # the two Q68 arms judge their own shape (the uppercased truncation in the slot / in an attribute),
    # so the per-needle attribute leg is read from the eleven arms that carry it.
    needle_leg_arms = [a for a in D.ARM_KEYS if not a.startswith("Q68")]
    hits_cand = {a: attr_hits("fixed", a) for a in needle_leg_arms}
    hits_base = {s: {a: attr_hits(s, a) for a in ("N1", "N2", "N3")}
                 for s in ("cell1_baseline_sink", "cell2_baseline_throw")}
    add("要件②补：Q71 口径下属性也算屏幕，这一腿量到了什么、没量到什么", "MET",
        {"instrument_patch": [DIR + "/ord0323_widen_q71.py", DIR + "/ord0323_widen_q71_r2.py"],
         "pairs_swept_per_arm": swept,
         "candidate_hits_per_arm": hits_cand,
         "arms_with_a_per_needle_attribute_leg": len(needle_leg_arms),
         "arms_in_the_q68_family": len([a for a in D.ARM_KEYS if a.startswith("Q68")]),
         "q68b_uppercased_prose_in_attributes": q68b["uppercased_prose_in_attributes"],
         "q68a_control_sweep_names_the_tested_card": q68a["sweep_sees_the_tested_card"],
         "q68a_control_pairs_read": q68a["attribute_pairs_swept"],
         "baseline_attribute_hits": hits_base,
         "arms_matrix": DIR + "/" + D.MATRIX_NAME},
        "Q71 说 data-* / aria-* 算进 DOM，而 textContent 看不见属性，所以每枚臂现在把整页的属性对单独扫一遍。"
        "本候选 " + str(len(needle_leg_arms)) + " 枚臂的逐针属性读数：" + json.dumps(hits_cand, ensure_ascii=False)
        + "（全空），Q68 那 " + str(len([a for a in D.ARM_KEYS if a.startswith('Q68')])) + " 枚另判自己的形："
        + json.dumps(q68b["uppercased_prose_in_attributes"], ensure_ascii=False) + "。"
        "采集控制（不然这一腿是装饰）：Q68a 那趟扫到 " + str(q68a["attribute_pairs_swept"])
        + " 对属性、并能从里面点名被测卡片自己那枚 data-testid = "
        + json.dumps(q68a["sweep_sees_the_tested_card"], ensure_ascii=False) + "。"
        "同时如实报这一腿的位置：两枚基线反件（" + json.dumps(list(hits_base), ensure_ascii=False)
        + "）在属性上同样 0 命中——改前那三处是把原话写在正文里的，所以属性这一腿**不是**本单的牙齿，"
        "它只把『我量过的面比判据要求的面窄』这件事补平；判这十格仍靠正文那一腿与逐臂状态位。")

    L = D.Q68_LEGS
    S = D.Q68_CODE_SLOT
    add("Q68 裁定（号令者 04:14）：三要件逐条现读，与两条腿各自量到的", "MET",
        {"commander_ruling": "Q68 = 「原因编号」那一格只准放编号", "ruling_post_at": "04:14",
         "requirement_1_serverReasonCode": {
             "fallback_lines_at_ordered_base": S["detail_fallback_at_base"],
             "fallback_line_text_at_ordered_base": S["detail_fallback_text_at_base"],
             "serverReasonCode_body_at_candidate": S["serverReasonCode_body_at_candidate"],
             "fallback_lines_at_candidate": S["detail_fallback_at_candidate"],
             "machine_key_table_line_at_candidate": S["machine_keys_accepted_at_candidate"],
             "file": S["file"]},
         "requirement_2_no_code_copy": {
             "line_at_candidate": S["no_code_copy_line_at_candidate"],
             "reachable_after_requirement_1": L["no_code_copy_reachable"],
             "blocked_producers_enumerated": L["blocked_producers"]},
         "requirement_3_sentence_chain_identical_to_ordered_base":
             S["sentence_chain_identical_to_base"],
         "leg_A_codes_that_reach_the_slot": L["code_reaches_the_slot"],
         "leg_B_sentence_only": L["sentence_only_leg"],
         "counter_arm_restoring_the_fallback": L["counter_arm_cell3_code_slot_back"],
         "arms_matrix": DIR + "/" + D.MATRIX_NAME,
         "evidence": [DIR + "/" + D.arm_name("cell3_code_slot_back", a) for a in
                      ("Q68a", "Q68b", "Q68c", "Q68d")]
         + [DIR + "/" + D.arm_name("fixed", a) for a in ("Q68a", "Q68b", "Q68c", "Q68d")],
         "instrument_patch": DIR + "/ord0323_q68_amend.py",
         "second_instrument_patch": DIR + "/ord0323_q68_amend_r2.py"},
        "要件① 现读而不是回忆：那行退回码在你具名的基线上是 "
        + json.dumps(S["detail_fallback_text_at_base"], ensure_ascii=False)
        + "（行号 " + json.dumps(S["detail_fallback_at_base"], ensure_ascii=False)
        + "），本候选同一函数里这样的行是 " + json.dumps(S["detail_fallback_at_candidate"], ensure_ascii=False)
        + " —— 已经没有了；那枚函数现在的整个函数体随件附上："
        + json.dumps(S["serverReasonCode_body_at_candidate"], ensure_ascii=False)[:400]
        + " 只认三枚机器键（接受表在 :" + json.dumps(S["machine_keys_accepted_at_candidate"], ensure_ascii=False) + "）。"
        "要件② 那一支还在 :" + json.dumps(S["no_code_copy_line_at_candidate"], ensure_ascii=False)
        + "，我没删；但要如实报一条：**① 之后它不可达**。枚举 `BLOCKED:` 的生产者 "
        + json.dumps([x["line"] for x in L["blocked_producers"]], ensure_ascii=False)
        + " 三处，逐处理由记在 readings 里，没有一处能把空码送进那一格（可达 = "
        + json.dumps(L["no_code_copy_reachable"], ensure_ascii=False) + "）。"
        "所以「服务器只给人话」那一次落在另一句同样诚实的文案上：屏幕上量到的分支是 "
        + json.dumps(L["sentence_only_leg"]["which_no_code_branch"], ensure_ascii=False)
        + "（那句「…但没有给出具体原因编号…」），不是编号槽里的「（没给编号）」那一支。"
        "**这一条请你裁**：甲 = 承认现在这一支（它同样说没有编号、同样把原话留在技术详情）；"
        "乙 = 把空码路由进编号槽，让它照你原文印「服务器回的原因编号是 （没给编号）」。"
        "要件③：`serverReasonSentence` 整枚函数在基线与本候选之间逐字节相同 = "
        + json.dumps(S["sentence_chain_identical_to_base"], ensure_ascii=False) + "。"
        "两条腿都齐。A（给了真编号就得看得见）现在按你的例子逐键各一枚臂："
        + json.dumps(L["code_reaches_the_slot"], ensure_ascii=False) + "。"
        "B（只有句子时不许冒充编号）：大写截断形在编号位 "
        + json.dumps(L["sentence_only_leg"]["uppercased_prose_in_code_slot"], ensure_ascii=False)
        + "、在属性里 " + json.dumps(L["sentence_only_leg"]["uppercased_prose_in_attributes"], ensure_ascii=False)
        + "、在全页除去被归因那一折之后 "
        + json.dumps(L["sentence_only_leg"]["uppercased_prose_anywhere_but_the_fold"], ensure_ascii=False)
        + " —— 三处都不在；原话只在技术详情里（"
        + json.dumps(L["sentence_only_leg"]["attributed_sentence_in_fold"], ensure_ascii=False)
        + "，归因标签在不在 " + json.dumps(L["sentence_only_leg"]["server_label_present"], ensure_ascii=False)
        + "，这一臂扫到的属性对数 " + str(L["sentence_only_leg"]["attribute_pairs_swept"]) + "）。"
        "反件把那行退回码放回去：Q68b " + str(L["counter_arm_cell3_code_slot_back"]["Q68b"])
        + "，而三枚正臂 Q68a/Q68c/Q68d 仍 "
        + json.dumps([L["counter_arm_cell3_code_slot_back"][a] for a in ("Q68a", "Q68c", "Q68d")],
                     ensure_ascii=False)
        + " —— 红只红在该红的那一枚，正方向没被一起带红。")


    FORM_SHAPES = {"F1": ("f1_engine_prose_back", "f1_fields_gone"),
                   "F2": ("f2_reason_back_as_status", "f2_machine_status_gone"),
                   "F3": ("f3_summary_back_on_screen", "f3_row_fields_gone"),
                   "F4": ("f4_summary_back_on_screen", "f4_draft_fields_gone")}
    FF = D.FOUR_FORMS
    forms = {}
    for _f, (_prose_shape, _fields_shape) in FORM_SHAPES.items():
        _ck, _rk = FF["construct_key"][_f], FF["replacement_key"][_f]
        _red = sorted(s for s in SH if SH[s]["per_arm"][_f] == "failed")
        _declared = sorted(s for s in SH if s != "fixed" and SH[s]["expected"].get(_f) == "failed")
        forms[_f] = {
            "construct_lines_at_pre_fix": FF["construct_lines_at_pre_fix"][_ck],
            "construct_lines_at_candidate": FF["construct_lines_at_candidate"][_ck],
            "replacement_in_place": FF["replacement_present_at_candidate"][_rk],
            "arm_at_candidate": SH["fixed"]["per_arm"][_f],
            "restore_the_prose": {"shape": _prose_shape, "arm": SH[_prose_shape]["per_arm"][_f],
                                  "evidence": DIR + "/" + D.arm_name(_prose_shape, _f)},
            "strip_the_fields": {"shape": _fields_shape, "arm": SH[_fields_shape]["per_arm"][_f],
                                 "evidence": DIR + "/" + D.arm_name(_fields_shape, _f)},
            "shapes_where_this_arm_is_red": _red,
            "shapes_declared_to_redden_it": _declared,
            "observed_equals_declared": _red == _declared,
            "arm_reads": {k: REA["fixed"][_f].get(k) for k in (
                "sentinel_on_screen", "sentinel_in_attributes", "attribute_pairs_swept",
                "fields_in_line", "machine_half", "answered_evidence", "filed_as_transport",
                "machine_status_in_line", "last_token_equals", "own_fields_present",
                "held_token_present", "held_text")},
            # E's signoff shape: this cell's claim is bound to one commit, one test, one shape.
            "signed_as": {"sha": D.CAND, "nodeid": REA["fixed"][_f]["nodeid"], "shape": "fixed"},
        }
    RUNNER_NAME = "ord0323_run_arms_r2.py"
    add("号令者 04:53 的甲：这个文件里另外四形，逐形两向都咬得住", "MET",
        {"ruling_assigned": "CMDR 04:53 甲", "ruling_reconsidered": "CMDR 05:43 收回 04:57 那句『你的通道赢』",
         "runner": RUNNER_NAME, "measured_before_declaring_on": "1371cffc",
         "channel_path": D.CHANNEL["path"], "dead_module_path": "frontend/src/lib/serverReason.ts",
         "declared_reddenings": {s: sorted(a for a, w in SH[s]["expected"].items() if w == "failed")
                                 for s in ("cell2_baseline_throw", "cell2_fields_blind",
                                           "cell2_status_frozen")},
         "non_pass_words_per_shape": {s: SH[s].get("non_pass_words", {}) for s in SH},
         "file": FF["file"], "pre_fix_generation": FF["pre_fix_generation"],
         "forms": forms,
         "no_second_helper": FF["no_second_helper"],
         "one_channel_on_the_tip": D.CHANNEL_USE,
         "channel_blob_at_ordered_base": FF["channel_blob_at_ordered_base"],
         "channel_blob_at_candidate": FF["channel_blob_at_candidate"],
         "arms_matrix": DIR + "/" + D.MATRIX_PUB,
         "instrument_patches": [DIR + "/" + D.pub("ord0323_four_forms.py"),
                                DIR + "/" + D.pub("ord0323_four_forms_arms.py"),
                                DIR + "/" + D.pub("ord0323_four_forms_shapes.py"),
                                DIR + "/" + D.pub("ord0323_f4_instrument.py"),
                                DIR + "/" + D.pub("ord0323_signoff_criterion.py")]},
        "; ".join(
            _f + "：那形在改前那代在 :"
            + json.dumps(forms[_f]["construct_lines_at_pre_fix"], ensure_ascii=False)
            + "、在候选上 :" + json.dumps(forms[_f]["construct_lines_at_candidate"], ensure_ascii=False)
            + "（替代它的写法在位 = " + json.dumps(forms[_f]["replacement_in_place"], ensure_ascii=False)
            + "），本候选这一臂 " + forms[_f]["arm_at_candidate"]
            + "；把原文放回去那枚形状 " + forms[_f]["restore_the_prose"]["shape"] + " → "
            + forms[_f]["restore_the_prose"]["arm"]
            + "；把这台设备的读数拆掉那枚 " + forms[_f]["strip_the_fields"]["shape"] + " → "
            + forms[_f]["strip_the_fields"]["arm"]
            for _f in ("F1", "F2", "F3", "F4"))
        + "。每一形两向都红在该红的那一枚，别臂不受牵连：实际让它红的形状集合与跑之前就声明要让它红的集合"
          "逐位相同 = " + json.dumps({_f: forms[_f]["observed_equals_declared"] for _f in forms},
                                    ensure_ascii=False)
        + "（声明就在驱动器 " + RUNNER_NAME + " 的 RUNS 里。三枚不是为本形而设的形状本来就会把这四形带回旧行为，"
          "也都写在声明里而不是事后追认：" + "; ".join(
              s + " → " + json.dumps(sorted(a for a in SH[s]["expected"]
                                            if SH[s]["expected"].get(a) == "failed"), ensure_ascii=False)
              for s in ("cell2_baseline_throw", "cell2_fields_blind", "cell2_status_frozen"))
        + "。其中 `cell2_status_frozen` 比十格那一版多咬中 N2、T07 —— 因为 F1 的修法把这台设备自己的读数写进了 "
          "memory 那一行，钉住机器位就等于换掉那条腿自己的状态；这条先在 1371cffc 上量到才写进声明。"
          "聚合器对『声明要红』的判定接受任何非通过字样（failed / timedOut / interrupted），实际字样记在每格的 "
          "non_pass_words 里，不把一个超时抹成通过、也不让一个到期的钟冒充断言。）"
        + "通道那枚文件在具名基线与本候选上逐位相同 = "
        + json.dumps(FF["no_second_helper"], ensure_ascii=False) + "（"
        + FF["channel_blob_at_ordered_base"] + " 对 " + FF["channel_blob_at_candidate"] + "）："
          "同一种判断只有一套词汇，我没有为这四形再造第三套。"
        + "再按你 05:43 收回那条指令核一遍现尖：" + D.CHANNEL["path"] + " 里 `classifyReadFailure(` 在 "
        + json.dumps(D.CHANNEL_USE["classifyReadFailure_calls"], ensure_ascii=False) + " 行、`copyFor(` 在 "
        + json.dumps(D.CHANNEL_USE["copyFor_calls"], ensure_ascii=False)
        + " 行；那枚不会上线的模块 `frontend/src/lib/serverReason.ts` 在现尖上存在 = "
        + json.dumps(D.CHANNEL_USE["module_exists_on_tip"], ensure_ascii=False)
        + "、被 import 的文件 " + json.dumps(D.CHANNEL_USE["importers_of_the_dead_module_on_tip"], ensure_ascii=False)
        + "；另有 " + str(len(D.CHANNEL_USE["files_naming_a_variable_serverReason_on_tip"]))
        + " 枚文件里出现 `serverReason` 这串字（多数是已有的 `serverReasonSentence` / `serverReasonCode` 这类符号名，"
          "逐枚列在 readings 的 one_channel_on_the_tip 里，不是那枚模块）。所以本单没有任何代码接向它。")

    A = D.ADJ
    add("如实报的残留（本单没点名，我也没动）", "REPORTED_NOT_FIXED",
        {"adjacent": A, "cell2_r3_hits_after": D.R3["after"]["hit_count"],
         "order_named_source_line": ":88", "order_named_sinks": "687/691/731",
         "boundary_copy_language_reading": D.REA["fixed"]["N1"]["panel_copy"],
         "q67_still_open": "格二所在文件与 ORD-0302 的 :1046 那条链无关，但 Q67 仍没裁",
         "raw_read_panel_pairing": D.RAW_PAIRING,
         "raw_read_panel_file": D.Q68_SHEET_FILE, "refused_route_registered_in": D.SPEC,
         "q53_ruling_this_bears_on": "Q53=①「那一块只陈列原始回读四字段」",
         "field_wording": "NOT-EMITTED",
         "receipt_field_now_exists": D.RECEIPT_FIELD,
         "request_id_still_absent_at_tip": D.RECEIPT_FIELD["request_id_hits_at_tip"] == 0,
         "receipt": DIR + "/ord0323_receipt_r6.json"},
        "两件如实报上去、我没有顺手改。其一，" + D.CELL2 + " 的 "
        + json.dumps({"json_parse": A["requestJson_unguarded_json_parse"]["lines"],
                      "reason_field": A["showResult_server_reason_to_message"]["lines"],
                      "reasoning_summary": A["reasoning_summary_to_dom"]["lines"]}, ensure_ascii=False)
        + " 这几行也能把非本单的原文带上屏（未设防的 json 解析异常、服务器的 `reason` 字段、`reasoning_summary`）"
          "—— 不在本单点名的十格里，D 的分桶另有归类，我只读数不动手。其二，" + D.CELL1 + " 的文案语言取自浏览器偏好（量到 "
        + repr(D.REA["fixed"]["N1"]["panel_copy"][:26]) + "）而不是这台设备已存的 zh-CN，同一屏两处来源不同，量到了没改。"
        "另：格一那枚折子里我留了一枚改前从未出现的指针 unresolved_fields（V8 报的是被访问的属性名 length），"
        "它没有牙齿，我没把它算进反件证据，也没删那条断言。"
        "其三，量 Q68 时撞见一件本单没点名、也不在你三要件里的缺陷，我只报数不动手："
        "`frontend/src/features/planning/PlanWithAiSheet.tsx:" + json.dumps(D.RAW_PAIRING["rawReading_built_at"], ensure_ascii=False).strip("[]") + "` "
        "在第一条请求（agent/commands）的响应上算出 rawReading，再由两处 setResult "
        + json.dumps(D.RAW_PAIRING["every_setResult_that_carries_it"], ensure_ascii=False)
        + " 一起带到屏幕上；被拒那一次由本臂在 spec 的 "
        + json.dumps(D.RAW_PAIRING["the_refusal_was_answered_at"], ensure_ascii=False)
        + " 那行答成 " + str(D.RAW_PAIRING["answered_status_on_the_refused_leg"])
        + "，可屏幕上「这台设备自己量到的回读字段」显示的是 "
        + json.dumps(D.RAW_PAIRING["fields_the_panel_shows"], ensure_ascii=False)
        + " —— 字段是这台设备真量到的，但挂在了另一条请求上。按 Q53 的口径那块只该陈列原始回读四字段，"
          "这条要不要我修，等你派。"
        + "其四，`request_id` 那条我上稿写的 NOT-EMITTED 到现尖上要补一句：具名字段在 "
        + json.dumps(D.RECEIPT_FIELD["request_id_hits_at_tip"], ensure_ascii=False)
        + " 次命中（基线与现尖都是这个数），但 ORD-0332 已经落了另一枚名字 "
        + json.dumps(D.RECEIPT_FIELD["field_name"], ensure_ascii=False) + "，"
        "定义在现尖 " + json.dumps(D.RECEIPT_FIELD["defines_at_tip"], ensure_ascii=False)
        + "、接线在 " + json.dumps(D.RECEIPT_FIELD["wired_at_tip"], ensure_ascii=False)
        + "。本单那些臂答的都是桩，所以那一枚号在不在屏上我没量过，留给你要不要另开一格。")

    receipt = {
        "schema": "CNX_ORD0323_RECEIPT_R1", "order": "ORD-0323", "lane": "B c01d72a3",
        "commander": "494abfd7", "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measurement_scope_first": {
            "scope": "lane B c01d72a3 本机 vite dev 面；手机代次未动；权威线未动",
            "generation": {"ordered_base": D.BASE, "candidate": D.CAND, "live_tip": D.NEW_TIP,
                           "commits_on_branch": D.COMMITS, "gap_to_live_tip": D.TIP_GAP},
            "artifacts": {"arms_matrix": DIR + "/" + D.MATRIX_NAME,
                          "r3_readings": DIR + "/" + D.pub("ord0323_r3_readings.json"),
                          "instrument": DIR + "/ord0323_run_arms_r2.py",
                          "per_arm_evidence_count": len(D.PUBLISHED)},
            "measurement_method": "Playwright 真机面（每个形状一次全新 run id 与独立 sqlite 库）+ 号令者自己的 "
                                  "r3 图案尺 + git ls-remote/merge-tree 只读预测",
        },
        "revision": "r2",
        "erratum_from_r1": {
            "what": "r1 quoted five blob ids that I computed by re-hashing captured `git show` stdout; that "
                    "capture strips the file's final newline, so those ids were sha1s of a truncated byte "
                    "string and resolved in no repository. This revision quotes git's own blob ids "
                    "(rev-parse). No cell's verdict, reading or wording changed for any other reason.",
            "was_now": D.ERRATUM_BLOBS,
            "superseded_file_left_untouched": DIR + "/ord0323_receipt_r1.json",
        },
        "cells": cells,
        "ruler_reuse_proof": {"blob_equal": R3["ruler"]["local_git_blob_hash"] == D.R3_BLOB,
                              "selftest": R3["ruler"]["selftest"]},
        "arms_verdict_from_matrix": SH["fixed"]["per_arm"],
        "matrix_verdict": D.MATRIX["verdict"],
        "verdict_vocabulary_used": ["MET", "REPORTED_NOT_FIXED"],
        "claimed_result": "两格各自双向断言成立；r3 点名的两行命中清零；候选只在新分支，权威线未动",
        "derived_result": None,
        "note": "claimed_result 是我自己的主张，等级归红队（B-1）。derived_result 留空。",
    }
    txt = json.dumps(receipt, ensure_ascii=False, indent=1)
    (D.WORK / "ord0323_receipt_r6.json").write_text(txt, "utf-8", newline="\n")
    grade = D.q38(D.WORK / "ord0323_receipt_r6.json")
    print("Q38 rc=", grade["rc"], "green=", grade["green"], grade["headline"])
    if not grade["green"]:
        print(grade["output"])
        raise SystemExit("a cell's sentence is not derivable from its own readings")
    publish(D.WORK / "ord0323_receipt_r6.json", "ord0323_receipt_r6.json")
    idx = {"schema": "CNX_ORD0323_INDEX_R1", "dir": DIR,
           "listed_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "files": sorted(D.PUBLISHED, key=lambda r: r["path"]), "file_count": len(D.PUBLISHED),
           "total_bytes": sum(int(r["bytes"]) for r in D.PUBLISHED),
           "note": "自增长清单；下一次重写用新文件名，并在下一帖给新的 40 位"}
    (D.WORK / "ord0323_index_r6.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1),
                                                  "utf-8", newline="\n")
    publish(D.WORK / "ord0323_index_r6.json", "ord0323_index_r6.json")
    (D.WORK / "ord0323_publish_rows.json").write_text(
        json.dumps(D.PUBLISHED, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    return receipt, idx


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("all", "publish"):
        stage_publish()
    receipt = idx = None
    if stage in ("all", "receipt"):
        receipt, idx = stage_receipt()
    else:
        # a later stage in its own process reads the two tail artifacts back from disk
        receipt = json.loads((D.WORK / "ord0323_receipt_r6.json").read_text(encoding="utf-8"))
        idx = json.loads((D.WORK / "ord0323_index_r6.json").read_text(encoding="utf-8"))
    if stage in ("all", "block", "post"):
        from ord0323_block import build_block, write_block, post_bus
        text = build_block(D, receipt, idx)
        # `post` must not drop a second copy of the same block into the inbox: the applier reads the
        # directory, and two files one minute apart made it supersede its own pending input.
        if stage in ("all", "block"):
            write_block(D, text)
        if stage in ("all", "post"):
            post_bus(D, text)


if __name__ == "__main__":
    main()
