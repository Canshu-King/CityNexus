"""ORD-0371 two-way self-test for claim_coordinate_check_r6 - written OUTSIDE the ruler on purpose.

The r4e selftest lives inside the tool it tests, so an arm that silently no-ops can still report
"pass" (that is exactly how the 18:13 r4e-vs-r5e mis-comparison happened to me: I read an exit code,
not a produced number). This tester imports the module and asserts both directions:

  POS  a committed path on the same line vouches a count          -> green
  NEG1 the same count with no voucher                             -> red
  NEG2 a path that is NOT in the authoritative tree               -> red
  NEG3 the path moved to the NEXT line (inside the +-200 window)  -> red   (r6 is stricter than r4e here)
  NEG4 a bare path does not buy the DIMENSION exemption           -> red   (that one still costs a strong receipt)
  NEG5 the arm fail-closes: an unresolvable ref vouches nothing    -> red

Every expectation is computed from what the run produced; nothing here is a literal I typed from memory.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("q43r6", os.path.join(HERE, "claim_coordinate_check_r6.py"))
r6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r6)

REAL = "backend/app/main.py"
FAKE = "backend/app/definitely_not_in_the_tree_zzz.py"


def verdict_of(text):
    """(verdict_word, exit_code, claims, findings, exempt). decide() returns a PAIR, so unpacking it into one
    name and comparing that name to a string would silently make every arm false - caught here on the first
    run, where NEG2/3/5 were genuinely red yet reported failed."""
    claims, findings, exempt = r6.scan(text)
    verdict, code = r6.decide(claims, findings, text)
    return verdict, code, claims, findings, exempt


def main():
    st = r6.configure_tree()
    arm = {"available": st["available"], "ref": st["ref"], "paths": st["paths"], "why": st["why"]}
    pos_line = "tier B 命中 77 处，逐行看 %s 的具名量具输出" % REAL
    neg1_line = "tier B 命中 77 处，没有引用任何文件"
    neg2_line = "tier B 命中 77 处，逐行看 %s 的具名量具输出" % FAKE
    neg3_pair = "tier B 命中 77 处，逐行看下一行的量具输出\n%s 在这里，它在下一行" % REAL
    neg4_line = "留白 212px 与那条声明的 212px 等量，来源见 %s，但没有收据" % REAL

    checks = {}
    v, code, claims, f, ex = verdict_of(pos_line)
    checks["POS_committed_path_vouchers_count"] = (v == "Q43_GATE_GREEN", v, claims, len(f))
    v, code, claims, f, ex = verdict_of(neg1_line)
    checks["NEG1_unvouched_count_still_red"] = (v == "Q43_GATE_RED", v, claims, len(f))
    v, code, claims, f, ex = verdict_of(neg2_line)
    checks["NEG2_uncertain_path_still_red"] = (v == "Q43_GATE_RED", v, claims, len(f))
    v, code, claims, f, ex = verdict_of(neg3_pair)
    checks["NEG3_next_line_path_still_red"] = (v == "Q43_GATE_RED", v, claims, len(f))
    v, code, claims, f, ex = verdict_of(neg4_line)
    # What NEG4 actually guards: a bare committed path may VOUCH a claim as a coordinate, but it must not
    # pay for the DIMENSION / DISCIPLINE_ZERO *exemptions* (those still cost a strong receipt - blob /
    # issuecomment / refs/heads / run id). Asserting on the exemption buckets, not on the verdict, because
    # the verdict legitimately turns green once the number has a coordinate beside it.
    checks["NEG4_bare_path_does_not_buy_dimension_exemption"] = (
        "DIMENSION" not in ex and "DISCIPLINE_ZERO" not in ex, v, claims, len(f), sorted(ex.keys()))

    # NEG5: point the arm at a ref that does not exist, then re-run the POS case - it must go red.
    r6._tree.update({"available": False, "why": "forced off by the tester"})
    v, code, claims, f, ex = verdict_of(pos_line)
    checks["NEG5_arm_fail_closed"] = (v == "Q43_GATE_RED", v, claims, len(f))

    ok = all(c[0] for c in checks.values())
    print(json.dumps({"committed_path_arm": arm, "checks": checks, "overall_pass": ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
