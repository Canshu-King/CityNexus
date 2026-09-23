"""ORD-0253 反突变台子：把幂等保护的承重点具名拆掉，看哪几格变红；每轮逐字节复原并自证。

仲裁点名的两枚是 M1/M2，M3/M4 是我自己加的第二承载（同一格里索引与回读是两条独立保护）。
每条 arm 都记 `primary_target_nodeids`（该 arm 语义上该打红的格）与整批红集，
`derived_result / direct_red / collateral_red` **一律留 null 给外部 verifier**（B-1：交付方不自宣 KILLED）。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

WT = Path("D:/moodle/_qoder_f_ord253_20260923/backend")
TARGET = WT / "app/main.py"
GATE = "tests/test_qoder_agent_command_idempotency.py"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0253_reverse_mutation_receipt.json")

ARMS = [
    {
        "mutation_id": "M1_regenerate_key_every_call",
        "claim_broken": "同 key 重放回到同一枚持久 mission（验收①）",
        "carriers_removed": ["request-supplied key is actually used as the durable claim"],
        "anchor": '    scoped_key = f"agent.command:{header_key}"\n',
        "mutated": '    scoped_key = f"agent.command:{header_key}-{uuid4()}"  # MUT M1\n',
        "expected_anchor_hits": 1,
        "primary_target_nodeids": [
            "test_same_key_same_request_replays_the_one_persisted_mission",
            "test_two_threads_one_key_produce_one_mission",
        ],
    },
    {
        "mutation_id": "M2_constant_signature_overmerges",
        "claim_broken": "同 key 不同意图必须 fail closed，绝不静默 alias（验收②）",
        "carriers_removed": ["request signature is compared before replaying"],
        "anchor": ('    signature = canonical_request_signature(\n'
                   '        {\n            "journey_id": str(journey_id),\n'
                   '            "command": payload.command,\n'
                   '            "requested_autonomy": payload.requested_autonomy,\n        }\n    )\n'),
        "mutated": '    signature = "MUT-M2-constant"  # 过度合并：任何请求都算同一个意图\n',
        "expected_anchor_hits": 1,
        "primary_target_nodeids": [
            "test_same_key_with_a_different_command_fails_closed_never_aliases",
            "test_same_key_with_a_different_autonomy_fails_closed_too",
            "test_same_key_on_another_journey_fails_closed_not_silently_reused",
        ],
    },
    {
        "mutation_id": "M3_drop_operation_scope",
        "claim_broken": "键按 operation 作用域，不与别的操作互相冒领",
        "carriers_removed": ["operation prefix on the stored key"],
        "anchor": '    scoped_key = f"agent.command:{header_key}"\n',
        "mutated": '    scoped_key = header_key  # MUT M3：去掉 operation 前缀\n',
        "expected_anchor_hits": 1,
        "primary_target_nodeids": ["test_the_receipt_is_a_durable_scoped_row_not_an_in_memory_map"],
    },
    {
        "mutation_id": "M4_ignore_key_validate_anything",
        "claim_broken": "太短的键走既有 422，不新造错误也不硬塞",
        "carriers_removed": ["validate_idempotency_key guard on this route"],
        "anchor": ('    try:\n        header_key = validate_idempotency_key(idempotency_key)\n'
                   '    except CommerceValidationError as exc:\n'
                   '        raise HTTPException(422, str(exc)) from exc\n'
                   '    signature = canonical_request_signature(\n'),
        "mutated": ('    header_key = idempotency_key\n    _exc = None\n'
                    '    signature = canonical_request_signature(\n'),
        "expected_anchor_hits": 1,
        "primary_target_nodeids": [
            "test_a_malformed_key_is_refused_with_the_existing_validation_message"],
    },
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run_gate() -> tuple[int, list[str], str]:
    p = subprocess.run([PY, "-m", "pytest", "--no-header", "-p", "no:cacheprovider", GATE,
                        "-q", "--tb=no", "-rf"], cwd=str(WT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1200)
    out = p.stdout or ""
    red = sorted(set(re.findall(r"FAILED .*::(test_\w+)", out)))
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l or "failed" in l or "error" in l), "")
    return p.returncode, red, tail


def main() -> int:
    original = TARGET.read_bytes()
    base_rc, base_red, base_tail = run_gate()
    print(f"控制轮（未突变）：rc={base_rc} 红集={base_red or '无'} | {base_tail}")
    control_green = base_rc == 0 and not base_red
    if not control_green:
        print("REFUSE：控制轮不绿 ⇒ 整批作废（campaign_valid=False），不做任何突变")
        return 3

    arms = []
    for arm in ARMS:
        text = original.decode("utf-8")
        hits = text.count(arm["anchor"])
        if hits != arm["expected_anchor_hits"]:
            arms.append({"mutation_id": arm["mutation_id"], "invalid": f"anchor_hits={hits}"})
            continue
        mutated = text.replace(arm["anchor"], arm["mutated"], 1)
        mutated_bytes = mutated.encode("utf-8")
        TARGET.write_bytes(mutated_bytes)
        try:
            rc, red, tail = run_gate()
        finally:
            TARGET.write_bytes(original)
            restored = TARGET.read_bytes()
        arms.append({
            "mutation_id": arm["mutation_id"], "claim_broken": arm["claim_broken"],
            "carriers_removed": arm["carriers_removed"],
            "allowed_scope": "product", "actual_scope": "product",
            "anchor_hits": hits, "bytes_changed": restored != mutated_bytes,
            "mutated_sha256": sha(mutated_bytes),
            "primary_target_nodeids": [f"{GATE}::{n}" for n in arm["primary_target_nodeids"]],
            "mutated_runs": {"rounds": 1, "exit_code": rc, "summary_line": tail,
                             "failed_nodeids": [f"{GATE}::{n}" for n in red],
                             "control_round_red": bool(base_red)},
            "restore": {"restored": sha(restored) == sha(original),
                        "byte_exact_match_before": restored == original,
                        "no_mutant_marker_left": arm["mutated"] not in TARGET.read_text(encoding="utf-8")},
            "derivation": {"claimed_result": "KILLED" if red else "SURVIVED",
                           "claimed_result_note": "交付方自称，仅供 verifier 参考",
                           "derived_result": None, "direct_red_nodeids": None,
                           "collateral_red_nodeids": None,
                           "primary_hit_every_named_cell": all(
                               n.split("::")[-1] in red for n in arm["primary_target_nodeids"])
                           if red else False},
        })
        a = arms[-1]
        print(f"{a['mutation_id']}: rc={rc} 红={len(red)} named_hits={a['derivation']['primary_hit_every_named_cell']} "
              f"restore_ok={a['restore']['byte_exact_match_before']} | {tail}")
        if not red:
            print(f"  ⇒ {a['mutation_id']} 没打红任何一格：要么保护有冗余承载，要么我这枚突变是空操作。**不记成 KILLED。**")

    after = TARGET.read_bytes()
    receipt = {
        "schema_version": "CNX_REVERSE_MUTATION_RECEIPT_V1",
        "receipt_kind": "reverse_mutation",
        "order": "ORD-0253 后端半件（agent/commands 幂等）",
        "lane": "F 8ccd71d8", "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": {"repo": "candidate worktree D:/moodle/_qoder_f_ord253_20260923",
                  "branch": "agent/f-ord253-candidates",
                  "base_authoritative_sha": subprocess.run(
                      ["git", "-C", str(WT.parent), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip(),
                  "target_file": str(TARGET), "gate_file": str(WT / GATE),
                  "run_shape": f"whole-file（该门文件一次跑满，本轮控制轮 {base_tail}）",
                  "exact_command": f"{PY} -m pytest --no-header -p no:cacheprovider {GATE} -q --tb=no -rf"},
        "environment": {"python": PY, "cwd": str(WT),
                        "offline_precondition": "ai_api_key 为空（门内每格再 assert 一次）"},
        "control_round": {"exit_code": base_rc, "red": base_red, "green": control_green,
                          "summary": base_tail},
        "arms": arms,
        "file_integrity": {"before_sha256": sha(original), "after_all_arms_sha256": sha(after),
                           "byte_exact_after_campaign": after == original},
        "verifier_note": "derived_result / direct_red / collateral_red 全留 null，归红队/仲裁（B-1）",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n全臂跑完后被测文件逐字节复原={after == original}")
    print(f"WROTE {OUT} ({OUT.stat().st_size} B, sha256[:12]={sha(OUT.read_bytes())[:12]})")
    return 0 if after == original else 4


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
