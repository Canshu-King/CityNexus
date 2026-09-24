"""ORD-0262-NARROW 门的两枚反突变：把承重那一行改掉，目标格**必须**变红。

规矩（B-1 起）：交付方不许自宣 KILLED —— 这里只记 `claimed_result`，`derived_result` 留 null 给 verifier。
突变只碰我自己加的那两行；跑完逐字节还原并回验 sha1。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path("D:/moodle/_qoder_f_ord253_20260923/backend")
TARGET = BACKEND / "app/main.py"
GATE = "tests/test_qoder_ord0262_narrow_contention.py"
GATES = [GATE, "tests/test_qoder_stay_generation_operations.py"]
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp936：会印读数的仪器必须先钉输出编码
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_narrow_mutation_receipt.json")

MUTANTS = {
    "M1_whitelist_emptied": {
        "edits": [
            ('CONTENTION_UNIQUE_ROWS = frozenset({"traveler_agent_policies.traveler_id"})',
             "CONTENTION_UNIQUE_ROWS = frozenset()"),
            ('CONTENTION_LOCK_MARKERS = ("database is locked", "database is busy")',
             "CONTENTION_LOCK_MARKERS = ()"),
        ],
        "targets": ["test_1_named_policy_claim_collision_answers_inside_the_existing_envelope",
                    "test_2_a_held_write_lock_answers_in_the_envelope_not_as_a_bare_500",
                    "test_4_a_non_lock_operational_error_is_not_called_contention"],
        "owner": "①/②：认不出来就没人翻译 ⇒ 这两格该红；③' 那格反向该**继续绿**（名单外本来就不认）",
    },
    "M2_envelope_replaced_by_bare_503": {
        "edits": [
            ('        "Another generation is writing right now; this one was not recorded. Try again.",\n'
             '        status=503,\n'
             '        details={"retry_after_ms": _contention_retry_after_ms(), "contention": reason},\n'
             '        message_key="generation.store_busy",\n'
             '        reason_code=reason,',
             '        "busy",\n        status=503,'),
        ],
        "targets": ["test_1_named_policy_claim_collision_answers_inside_the_existing_envelope",
                    "test_2_a_held_write_lock_answers_in_the_envelope_not_as_a_bare_500"],
        "owner": "①/②：只把状态码改对、信封掏空 ⇒ 必须红（证明门测的是契约不是状态码）",
    },
    "M3_retry_literal_reintroduced_hydration": {
        "edits": [('            details={"retry_after_ms": _hydration_busy_retry_after_ms()},',
                   '            details={"retry_after_ms": 500},')],
        "targets": ["test_5_the_retry_hint_comes_from_the_operation_ladder_not_a_fourth_literal",
                    "test_a_busy_store_answers_a_named_retry_on_both_doors"],
        "owner": "④ 的正控（commander 01:1x §③ 点名要的那一枚）：把 hydration 的等值抄回写死的 500 ⇒ "
                 "那一格**必须红**；generation 两门那枚既存门必须**继续绿**（它管的是另一条操作），"
                 "这才说明这一刀切在 hydration 上，不是把整块产品打死",
    },
    "M5_generation_site_literal_reintroduced": {
        "edits": [('            details={"retry_after_ms": _contention_retry_after_ms()},\n'
                   '            message_key="generation.store_busy",\n'
                   '        )\n'
                   '    finished = wait_for_operation(row.id)',
                   '            details={"retry_after_ms": 500},\n'
                   '            message_key="generation.store_busy",\n'
                   '        )\n'
                   '    finished = wait_for_operation(row.id)')],
        "targets": ["test_5_the_retry_hint_comes_from_the_operation_ladder_not_a_fourth_literal",
                    "test_a_busy_store_answers_a_named_retry_on_both_doors"],
        "owner": "④ 的第三枚正控，也是这次 A/B 真找出来的那一格：把**等待门**那处抄回 500 ⇒ 我的 ④ 与"
                 "既存那枚 resident 门（它从前钉死 ==500）必须同时红 —— resident 断言现在判的是"
                 "'等于阶梯下限 + 两门一致'，不是旧数字",
    },
    "M4_retry_literal_reintroduced_envelope": {
        "edits": [('        details={"retry_after_ms": _contention_retry_after_ms(), "contention": reason},',
                   '        details={"retry_after_ms": 500, "contention": reason},')],
        "targets": ["test_5_the_retry_hint_comes_from_the_operation_ladder_not_a_fourth_literal",
                    "test_1_named_policy_claim_collision_answers_inside_the_existing_envelope",
                    "test_2_a_held_write_lock_answers_in_the_envelope_not_as_a_bare_500"],
        "owner": "④ 的第二枚正控：共享具名信封里抄回 500 ⇒ ④ 必须红；①/② 记在 targets 里是要**看见它们继续绿**"
                 "（它们断的是信封形状，不该被等值来源这一刀带走）",
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run(nodeids: list[str]) -> dict:
    assert nodeids, "SETUP：targets 为空 ⇒ 这一枚什么都没问，不许跑"
    proc = subprocess.run(
        [PY, "-m", "pytest", *GATES, "-q", "--no-header", "-p", "no:cacheprovider",
         "-k", " or ".join(nodeids)],
        cwd=str(BACKEND), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900)
    out = proc.stdout
    return {"rc": proc.returncode, "failed_nodeids": sorted(_re_fail(out)),
            "tail": out.strip().splitlines()[-1] if out.strip() else "",
            "collection_lines": [ln for ln in out.splitlines()
                                 if "collected" in ln or " error" in ln][:2]}


def _re_fail(out: str):
    import re
    for m in re.finditer(r"FAILED \S+::(\w+)", out):
        yield m.group(1)


original = TARGET.read_bytes()
base_sha = sha(TARGET)
results: dict[str, object] = {}
ALL_TARGETS = sorted({n for spec in MUTANTS.values() for n in spec["targets"]})
control = run(ALL_TARGETS)          # 未突变的同形制读数：控制轮不绿 ⇒ 整批作废，不出任何判级
campaign_valid = control["rc"] == 0 and not control["failed_nodeids"]
try:
    for name, spec in MUTANTS.items():
        text = TARGET.read_text(encoding="utf-8")
        for a, b in spec["edits"]:
            assert text.count(a) == 1, f"{name}：锚点出现 {text.count(a)} 次，不是唯一 ⇒ 中止"
            text = text.replace(a, b)
        TARGET.write_text(text, encoding="utf-8", newline="\n")
        mutated_sha = sha(TARGET)
        started = time.time()
        reading = run(spec["targets"])
        results[name] = {
            "mutation": {"before_sha256_16": base_sha, "after_sha256_16": mutated_sha,
                         "anchors": [a[:60] for a, _ in spec["edits"]]},
            "target_nodeids": spec["targets"], "owner_assertion": spec["owner"],
            "mutated_runs": reading, "seconds": round(time.time() - started, 1),
            "claimed_result": "KILLED" if reading["failed_nodeids"] else "SURVIVED",
            "killed_by": [n for n in spec["targets"] if n in reading["failed_nodeids"]],
            "still_green": [n for n in spec["targets"] if n not in reading["failed_nodeids"]],
            "derived_result": None,      # 由 verifier 派生，我不自签
        }
        TARGET.write_bytes(original)
        assert sha(TARGET) == base_sha, f"{name}：还原后 sha 不一致 ⇒ 立刻停，别继续跑"
finally:
    TARGET.write_bytes(original)

receipt = {
    "what": "ORD-0262-NARROW 门的反突变 campaign（5 枚：①/② 的具名信封 + ④ 的三枚正控：把等值抄回写死数字）",
    "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "scope": {"branch": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "--abbrev-ref", "HEAD"],
                                        capture_output=True, text=True).stdout.strip(),
              "head": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
              "base": subprocess.run(["git", "-C", str(BACKEND.parent), "merge-base", "HEAD",
                                      "d2665e25855aeb265329266831983de42321697d"],
                                     capture_output=True, text=True).stdout.strip(),
              "target_file": str(TARGET), "target_sha_before_and_after": base_sha,
              "run_shape": f"{PY} -m pytest {' + '.join(GATES)} -q（每枚只跑点名的 nodeid）"},
    "control": {"reading": control, "all_targets": ALL_TARGETS,
                "campaign_valid": campaign_valid,
                "rule": "控制轮 = 未突变、同两把门、同一组点名 nodeid 的真实读数；"
                        "它不绿就整批作废（不出 KILLED/SURVIVED 判级）"},
    "mutations": results,
    "campaign_valid": campaign_valid,
    "restore_verified": sha(TARGET) == base_sha,
    "not_measured": {"cross_process_same_key_face": "归 verifier（仲裁 §3）；本门是进程内形制，不借此声明跨进程已闭"},
}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(receipt, ensure_ascii=False, indent=1))
print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)  还原后 sha == base：{sha(TARGET) == base_sha}")
