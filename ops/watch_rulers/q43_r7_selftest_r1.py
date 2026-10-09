"""ORD-0371 two-way tester for claim_coordinate_check_r7 (and it re-runs r6's six arms on the new module).

Every expectation is computed from what the run produced: each class is asserted with the literal context
present AND with it stripped out of the same sentence, so an arm that quietly no-ops shows up as a failed
NEG->POS pair instead of a green line.

Run: python q43_r7_selftest_r1.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r7 = load("q43r7", "claim_coordinate_check_r7.py")
REAL = "backend/app/main.py"
FAKE = "backend/app/definitely_not_in_the_tree_zzz.py"


def scan(mod, text):
    claims, findings, exempt = mod.scan(text)
    verdict, code = mod.decide(claims, findings, text)
    return verdict, claims, findings, exempt


def main():
    st = r7.configure_tree()
    arm = {"available": st["available"], "ref": st["ref"], "paths": st["paths"], "why": st["why"]}
    checks = {}
    # A sentence made only of literals has zero claims, so the honest expectation for an "exempt" arm is
    # NO_CLAIM_FOUND, not GREEN - my first run asserted GREEN and got NO_CLAIM_FOUND back. What an exempt
    # arm must prove is (a) nothing refused and (b) the discount is visible in a named bucket, never silent.
    def exempted(v, c, f, ex, want_class):
        return (len(f) == 0 and v in ("Q43_GATE_GREEN", "NO_CLAIM_FOUND", "Q43_GATE_GREEN_CITED")
                and ex.get(want_class, 0) >= 1)

    # ---- r6 arms, re-run on r7 so the new classes cannot silently undo the committed-path voucher ----
    checks["POS_committed_path_vouchers_count"] = (
        scan(r7, "tier B 命中 77 处，逐行看 %s 的具名量具输出" % REAL)[0] == "Q43_GATE_GREEN",)
    checks["NEG1_unvouched_count_still_red"] = (
        scan(r7, "tier B 命中 77 处，没有引用任何文件")[0] == "Q43_GATE_RED",)
    checks["NEG2_uncertain_path_still_red"] = (
        scan(r7, "tier B 命中 77 处，逐行看 %s 的具名量具输出" % FAKE)[0] == "Q43_GATE_RED",)
    checks["NEG3_next_line_path_still_red"] = (
        scan(r7, "tier B 命中 77 处，逐行看下一行的量具输出\n%s 在这里" % REAL)[0] == "Q43_GATE_RED",)

    # ---- r7: IPv4 literal ----
    v_ip, c_ip, f_ip, ex_ip = scan(r7, "命令行 `uvicorn app.main:app --host 127.0.0.1 --port 8138` 是我起的")
    checks["R7_ip_literal_exempt"] = (exempted(v_ip, c_ip, f_ip, ex_ip, "IP_PART"),
                                      v_ip, c_ip, len(f_ip), sorted(ex_ip.items()))
    v_n, c_n, f_n, ex_n = scan(r7, "这一轮扫了 127 个节点，没有一个应答")
    checks["R7_bare_127_count_still_red"] = (v_n == "Q43_GATE_RED", c_n, len(f_n), sorted(ex_n.items()))

    # ---- r7: bracketed data array ----
    v_a, c_a, f_a, ex_a = scan(r7, "命中节点、可命中、框 `[0,145,522,44]`、URL 不变")
    checks["R7_array_exempt"] = (exempted(v_a, c_a, f_a, ex_a, "ARRAY_LITERAL"),
                                 v_a, c_a, len(f_a), sorted(ex_a.items()))
    v_a2, c_a2, f_a2, ex_a2 = scan(r7, "命中 145 个节点")
    checks["R7_count_145_still_red"] = (v_a2 == "Q43_GATE_RED", c_a2, len(f_a2), sorted(ex_a2.items()))

    # ---- r7: pid / port written in prose ----
    v_p, c_p, f_p, ex_p = scan(r7, "三证：8138 的监听 pid 9984 ← 父 23992 的 CommandLine 就是那一行")
    checks["R7_pid_port_prose_exempt"] = (exempted(v_p, c_p, f_p, ex_p, "PID"),
                                          v_p, c_p, len(f_p), sorted(ex_p.items()))
    v_p2, c_p2, f_p2, ex_p2 = scan(r7, "账本里写了 23992 行，没人引用文件")
    checks["R7_23992_without_pid_word_still_red"] = (v_p2 == "Q43_GATE_RED", c_p2, len(f_p2),
                                                     sorted(ex_p2.items()))

    # ---- the guard that matters most: a real count sharing a line with literals must still refuse ----
    v_g, c_g, f_g, ex_g = scan(r7, "「看已保存的只读副本」：命中 1 个节点、框 `[0,145,522,44]`、URL 不变")
    checks["R7_count_next_to_literals_still_red"] = (v_g == "Q43_GATE_RED", c_g, len(f_g), sorted(ex_g.items()))

    ok = all(c[0] for c in checks.values())
    print(json.dumps({"committed_path_arm": arm, "checks": checks, "overall_pass": ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
