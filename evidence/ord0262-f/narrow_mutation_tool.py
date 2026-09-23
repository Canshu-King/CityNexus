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
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run(nodeids: list[str]) -> dict:
    proc = subprocess.run(
        [PY, "-m", "pytest", GATE, "-q", "--no-header", "-p", "no:cacheprovider",
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
    "what": "ORD-0262-NARROW 门的反突变 campaign（commander (a)/(b) 口径下：只测我加的那两行的承重）",
    "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "scope": {"branch": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "--abbrev-ref", "HEAD"],
                                        capture_output=True, text=True).stdout.strip(),
              "head": subprocess.run(["git", "-C", str(BACKEND.parent), "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
              "base": "d2665e25855aeb265329266831983de42321697d",
              "target_file": str(TARGET), "target_sha_before_and_after": base_sha,
              "run_shape": f"{PY} -m pytest {GATE} -q（每枚突变只跑点名的 nodeid）"},
    "control": {"note": "控制轮 = 未突变时的整轮读数（4 passed / 1 failed=FINDING_OPEN 常数格），"
                        "见 ord0262_narrow_receipt.json；控制轮里那一格红是**已知开放读数**，不算 campaign 失效",
                "control_green_on_the_four_contract_cells": True},
    "mutations": results,
    "restore_verified": sha(TARGET) == base_sha,
    "not_measured": {"cross_process_same_key_face": "归 verifier（仲裁 §3）；本门是进程内形制，不借此声明跨进程已闭"},
}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(receipt, ensure_ascii=False, indent=1))
print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)  还原后 sha == base：{sha(TARGET) == base_sha}")
