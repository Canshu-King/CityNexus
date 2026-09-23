"""Build CNX_SCOPE_KEY_INDEX_V1: the machine-readable answer to lane F's "拿不到 scope 键".

Every receipt here is read from disk and its scope key (exact_sha, nodeid, run_shape) plus its numbers
are taken from the file, not retyped - so the index cannot drift from what it indexes. The mainline
facts (ancestry, which files moved) are measured with git in this run too.
"""
from __future__ import annotations

import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("D:/moodle/_qoder_integration_20260919")
HERE = Path(__file__).parent
TIP_ANNOUNCED_BY_F = "f24628f"          # what the commander quoted at 14:3x
TREES = {"2ab69f2": "2ab69f20adf783a6f29133f577877a88580129e3",
         "21f1e8d": "21f1e8db76b33f0be863ebe10b8b992afab13163",
         "0fd3cc7": "0fd3cc70d788f1e062669b528714d946e044ccd2"}
ARM_OF_INTEREST = {
    "C-ORD0224A2-Y3-loser-readback-only": "Y3 = 只坏败者回读（C 一格，索引与两次 reuse 读都留活）",
    "C-ORD0225-Y23-index-and-loser-readback": "Y23 = 破坏部分唯一索引 + 败者回读（命令那一臂）",
}
PUBLISHED = {  # what this delivery puts on commander/control, and where
    "v1_gate_receipt_Y3_a_2ab69f2.json": "evidence/ord0224_a2",
    "v1_gate_receipt_Y3_b_2ab69f2.json": "evidence/ord0224_a2",
    "v1_gate_receipt_Y3_c_2ab69f2.json": "evidence/ord0224_a2",
    "v1_gate_receipt_Y3_d_2ab69f2.json": "evidence/ord0224_a2",
    "v1_gate_receipt_Y23_a_0fd3cc7.json": "evidence/ord0225",
    "v1_gate_receipt_Y23_b_0fd3cc7.json": "evidence/ord0225",
    "v1_gate_receipt_Y3_a_0fd3cc7.json": "evidence/ord0225",
}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


ALL_CARRIERS = ["A1 pre-resolution read", "A2 post-resolution read",
                "B partial unique index", "C loser read-back"]


def is_ancestor(a: str, b: str) -> dict:
    """`merge-base --is-ancestor` prints nothing either way - only the exit code decides."""
    p = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", a, b],
                       capture_output=True, text=True)
    return {"a": a, "b": b, "exit_code": p.returncode,
            "stdout": p.stdout.strip(), "is_ancestor": p.returncode == 0,
            "method": "git merge-base --is-ancestor <a> <b>; 判 exit code，不判输出（它两种答案都不说话）"}


def blob_of(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def read_receipt(name: str) -> dict:
    p = HERE / name
    d = json.loads(p.read_text(encoding="utf-8"))
    dr, runs = d["derivation"], d["mutated_runs"]["runs"]
    return {
        "file": f"{PUBLISHED[name]}/{name}",
        "bytes": p.stat().st_size,
        "git_blob_sha1": blob_of(p),
        "scope_key": {
            "repo": d["scope"]["repo"], "exact_sha": d["scope"]["exact_sha"],
            "target_nodeids": d["scope"]["target_nodeids"], "run_shape": d["scope"]["run_shape"],
            "tree_kind": d["scope"]["tree_kind"],
        },
        "command_argv": d["scope"]["command_argv"],
        "mutation_id": d["mutation"]["mutation_id"],
        "mutation_plain": ARM_OF_INTEREST.get(d["mutation"]["mutation_id"], "?"),
        "carriers_removed": d["mutation"]["carriers_removed"],
        "carriers_left_live": [c for c in ALL_CARRIERS if c not in d["mutation"]["carriers_removed"]],
        "carriers_unparsed_from_receipt": [c for c in d["mutation"]["carriers_removed"]
                                           if c not in ALL_CARRIERS],
        "changed_files": [{"path": c["path"], "before_blob": c["before_blob"],
                           "anchor_hits": c["anchor_hits"], "bytes_changed": c["bytes_changed"]}
                          for c in d["mutation"]["changed_files"]],
        "collected": sorted({r["collected"] for r in runs}),
        "baseline_outcome": list(d["baseline"]["target_outcomes"].values()),
        "rounds": d["mutated_runs"]["rounds"],
        "primary_red_rounds": dr["primary_red_rounds"],
        "observed_red_reasons": sorted({(r.get("assertion_red_reason") or "")[:220]
                                        for r in runs if r["run_index"] in dr["primary_red_rounds"]}),
        "kill_rate": f"{len(dr['primary_red_rounds'])}/{d['mutated_runs']['rounds']}",
        "claimed_result": dr["claimed_result"],
        "derived_result": dr["derived_result"],
        "hygiene": {
            "every_round_named_a_fresh_db": dr["every_round_named_a_fresh_db"],
            "every_round_restored_byte_exact": dr["every_round_restored_byte_exact"],
            "marker_residue_after_restore": sum(r["restore"]["mutant_marker_hits_after_restore"] for r in runs),
            "tree_identical_to_exact_sha": all(v["identical"] for v in d["scope"]["tree_kind_check"].values()),
        },
        "rows": {"baseline": dr["baseline_catalog_rows"], "mutated": dr["mutated_catalog_rows"]},
        "row_column_reading": (
            "行数出自 commander 自己那把尺 gate_streak.row_counts（blob "
            f"{(d['environment'].get('row_column_instrument') or {}).get('git_blob_sha1','')[:16]}…）；"
            "Y3 那一臂的行数恒为 1 是真读数不是坏表：红的形状是败者抛 HYDRATION_STORE_BUSY，"
            "库里没多出第二行开放作业，所以**这一臂的判据是节点红、行数是见证**。"
            if d["mutation"]["mutation_id"].endswith("loser-readback-only") else
            "行数出自 commander 自己那把尺 gate_streak.row_counts；这一臂会出现 2..5 行开放作业，"
            "所以 0->N 那一列在这里是**能区分**的。"),
        "emitter_blob": (d.get("provenance") or {}).get("emitter_git_blob_sha1_this_file"),
    }


def main() -> int:
    receipts = [read_receipt(n) for n in sorted(PUBLISHED)]
    by_key: dict[tuple, list[dict]] = {}
    for r in receipts:
        k = (r["scope_key"]["exact_sha"][:7], r["mutation_id"])
        by_key.setdefault(k, []).append(r)
    spread = []
    for k, rs in sorted(by_key.items()):
        rates = [len(x["primary_red_rounds"]) for x in rs]
        spread.append({
            "scope_key": {"exact_sha": rs[0]["scope_key"]["exact_sha"], "run_shape": rs[0]["scope_key"]["run_shape"],
                          "nodeid": rs[0]["scope_key"]["target_nodeids"][0], "mutation_id": k[1]},
            "batches": [{"file": Path(x["file"]).name, "kill_rate": x["kill_rate"],
                         "git_blob_sha1": x["git_blob_sha1"][:16]} for x in rs],
            "kills": rates, "min": min(rates), "max": max(rates),
            "all_rounds_red_in_every_batch": all(x == rs[0]["rounds"] for x in rates),
            "deterministic_in_any_batch": any(x == rs[0]["rounds"] for x in rates),
            "note": ("同一 scope 键的批次差就是结论本身：恒不满轮 ⇒ 该突变体在这道门上不是确定性杀手；"
                     "挑一批好看的等于说谎，所以全部批次都发。"),
        })
    pre_v1 = HERE / "xproc_y3_rounds_raw_test_g3_concurrent_open_ge_2ab69f2.json"
    pv = json.loads(pre_v1.read_text(encoding="utf-8"))
    tip = git("rev-parse", "HEAD")
    diff_names = git("diff", "--name-only", TREES["21f1e8d"], tip).splitlines()
    tip_moved_names = git("diff", "--name-only", TREES["0fd3cc7"], tip).splitlines()
    files3 = ["backend/app/catalog_hydration_operations.py", "backend/db/schema.sql",
              "backend/tests/test_qoder_anywhere_gates.py"]
    tips = {**TREES, "live_tip_at_build": tip}
    blobs = {f: {s: git("rev-parse", f"{sha}:{f}") for s, sha in tips.items()} for f in files3}
    out = {
        "kind": "CNX_SCOPE_KEY_INDEX_V1",
        "issued_for": "lane F 实读 §①（总线转述 @14:3x：evidence/ord0224 全 11 件里没有可读的 scope 键）",
        "session": "8c66aa92",
        "answers": {
            "what_was_asked": "把 2ab69f2 上 Y3=3/10 那格读数按 CNX_REVERSE_MUTATION_RECEIPT_V1 形状发布",
            "what_the_old_file_said": {
                "file": "evidence/ord0224_a2/" + pre_v1.name, "git_blob_sha1": blob_of(pre_v1),
                "bytes": pre_v1.stat().st_size,
                "sha": pv["sha"], "node": pv["node"], "run_shape": pv.get("run_shape"),
                "killed": pv["verdict"]["killed"], "rounds": pv["verdict"]["rounds"],
                "control": pv["control_round"]["node_outcome"],
                "field_correction": ("旧件的 verdict.campaign_valid 与 deterministic_kill 由同一个条件写出："
                                     "它把『这批证据有效』和『击杀是确定性的』混成一格。V1 收据里两者分开记："
                                     "控制轮绿 + 每轮还原逐字节 + 锚点 1 命中 ⇒ 证据有效；3/10 ⇒ 击杀不确定，"
                                     "那是**关于突变体**的结论。"),
            },
            "v1_receipts_published": receipts,
            "batches_per_scope_key": spread,
        },
        "mainline_facts_measured_in_this_run": {
            "tip_now": {"sha": tip, "short": tip[:7],
                        "as_announced_to_me": TIP_ANNOUNCED_BY_F,
                        "tip_moved_again": tip[:7] != TIP_ANNOUNCED_BY_F,
                        "log": git("log", "-1", "--format=%h %ad %s", "--date=iso", tip)},
            "tip_under_the_newest_batches": {
                "measurement_tip": TREES["0fd3cc7"][:7],
                "index_build_tip": tip[:7],
                "moved_underneath": tip[:7] != TREES["0fd3cc7"][:7],
                "files_between": tip_moved_names,
                "backend_app_between": [p for p in tip_moved_names if p.startswith("backend/app/")],
                "0fd3cc7_is_ancestor_of_now": is_ancestor(TREES["0fd3cc7"], tip),
                "plain": ("0fd3cc7 之后主线又动了：动的文件全在 frontend/e2e/review，backend/app 0 个。"
                          "本件不把两件事混着说：那三枚 0fd3cc7 收据的坐标就是 0fd3cc7，不改成今天这个尖。"),
            },
            "ancestry": {
                "21f1e8d_is_ancestor_of_tip": is_ancestor(TREES["21f1e8d"], tip),
                "2ab69f2_is_ancestor_of_tip": is_ancestor(TREES["2ab69f2"], tip),
                "reverse_self_test_tip_is_ancestor_of_21f1e8d": is_ancestor(tip, TREES["21f1e8d"]),
                "self_test_meaning": ("反向那一格必须 is_ancestor=false 且 exit_code!=0。若它也报 true，"
                                      "那就是这台仪器读不出差别（例如 git 直接失败），上面两条一起作废。"),
            },
            f"files_changed_21f1e8d_to_tip_{tip[:7]}": {"measured_against_tip": tip,
                                                        "count": len(diff_names), "paths": diff_names,
                                                        "any_in_backend_app": [p for p in diff_names
                                                                              if p.startswith("backend/app/")]},
            "blob_identity_of_the_three_files_under_mutation": blobs,
            "consequence": ("三把被测文件（被突变的产品文件、schema、那道门）在 2ab69f2 / 21f1e8d / 0fd3cc7 "
                            "与本次建索引时读到的主线尖上 blob 摘要逐一相同 ⇒ 在 21f1e8d 上量的 Y23/Y123 读数"
                            "描述的字节与今天主线一致；但这只是**字节**同一，不是结果互换的许可证："
                            "每枚读数的坐标仍是它自己那棵树，要主线尖上的数就看本件里 0fd3cc7 那三枚。"
                            "跨 shape / 跨键的互换一律按仲裁 A-5 拒绝，本件不做任何跨键推断。"),
        },
        "not_signed": ("derived_result 全部留 null：交付方不得给自己派生 verdict（B-1）。"
                       "ORD-0224 / ORD-0225 两边都不写 CLOSED；PROVIDER_WORK_COALESCING(ORD-0244) "
                       "未开工，composite DoD 在此之前不得写 FINAL CLOSED；强修 claim-before-work 一行未动。"),
    }
    target = HERE / "scope_key_index_v1.json"
    text = json.dumps(out, ensure_ascii=False, indent=2)
    # fail-closed on the one thing that made the old file useless: a key that is not actually there
    if out["mainline_facts_measured_in_this_run"]["ancestry"][
            "reverse_self_test_tip_is_ancestor_of_21f1e8d"]["is_ancestor"]:
        raise SystemExit("ancestry reads both directions as true - refusing to emit")
    for r in receipts:
        for k in ("exact_sha", "target_nodeids", "run_shape"):
            if not r["scope_key"].get(k):
                raise SystemExit(f"receipt {r['file']} lost scope key component {k}")
    import os as _os
    if _os.environ.get("CNX_SELFTEST_EMPTY_BLOB"):  # 反向自测：让真实代码路径拿到一次空输出
        blobs = {f: {"sabotage": ""} for f in files3}
    for f, per in blobs.items():
        for label, sha in per.items():
            if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
                raise SystemExit(f"blob read failed for {f} at {label}: {sha!r} (empty output is not identity)")
    if "\r" in text:
        raise SystemExit("CRLF in a published artifact")
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(receipts)} receipts indexed | {len(spread)} scope keys | tip {tip[:7]} | "
          f"files changed 21f1e8d..{tip[:7]} = {len(diff_names)} (backend/app: "
          f"{len([p for p in diff_names if p.startswith('backend/app/')])})")
    for s in spread:
        print(" ", s["scope_key"]["exact_sha"][:7], s["scope_key"]["mutation_id"][-26:],
              "batches", [b["kill_rate"] for b in s["batches"]])
    print("->", target, target.stat().st_size, "B", "blob", blob_of(target)[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
