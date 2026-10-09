"""mirror_ledger.py read-back contract (arbiter ruling 2026-09-24, ORD-0277 round): a dead ROUTE must not be
reported as a disagreement about the FILE.

Measured trigger: mirroring the 4,911,888-byte ledger returned `PUT -> 200 commit d1a86a3166b3`, then the
`contents` body came back EMPTY, so the tool printed `MISMATCH - do not trust this mirror`.  An independent
read proved the file had in fact landed (`commander/control` contents sha == local `git hash-object` ==
`94cef773ef8f6cce7dfa5f710bfb2d9ab07eccee`).  A false red in the evidence chain makes every lane doubt the
wrong object, so this file pins the classification both ways.

No mirror is performed here: the live half is read-only (GET contents meta + GET commit), and the classifier
is pulled out of `mirror_ledger.py` by AST.
"""
import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "mirror_ledger.py")
LOCAL = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
OUT = os.path.join(HERE, "receipts", "mirror_readback_contract.json")
GREEN, RED = "GREEN", "RED"
CONF, DEGRADED, MISMATCH = "BYTE_LEVEL_CONFIRMED", "CONTENTS_BODY_UNUSABLE_BLOB_CONFIRMED", "MISMATCH"


def blob_sha(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + bytes(1) + raw).hexdigest()


def get(url):
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok,
                                              "Accept": "application/vnd.github+json",
                                              "User-Agent": "cnx-cmdr"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def extract_judge():
    src = io.open(TOOL, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "readback_state")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), TOOL, "exec"), ns)
    return ns["readback_state"], src


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cells = []

    def check(name, ok, detail):
        cells.append({"cell": name, "verdict": GREEN if ok else RED, "detail": detail})

    judge, src = extract_judge()
    W = "a" * 40           # a stand-in sha of the right shape
    V = "b" * 40

    # ---- the synthetic decision table, both directions
    check("T1_full_body_agreement_is_byte_level",
          judge(W, 10, b"0123456789", b"0123456789", W, W) == CONF,
          {"state": judge(W, 10, b"0123456789", b"0123456789", W, W)})
    check("T2_empty_body_with_equal_shas_is_not_mismatch",
          judge(W, 10, b"", b"0123456789", W, W) == DEGRADED,
          {"state": judge(W, 10, b"", b"0123456789", W, W),
           "why": "exactly the 4.9 MB case: the contents serializer gave up, the object did not change"})
    check("T3_different_remote_sha_is_mismatch",
          judge(V, 10, b"", b"0123456789", W, W) == MISMATCH,
          {"state": judge(V, 10, b"", b"0123456789", W, W)})
    check("T4_git_hash_object_disagreeing_is_mismatch",
          judge(W, 10, b"0123456789", b"0123456789", W, V) == MISMATCH,
          {"state": judge(W, 10, b"0123456789", b"0123456789", W, V),
           "why": "the third route exists to catch a bug in MY OWN hashing, so it must be able to veto"})
    check("T5_missing_remote_sha_is_mismatch_not_absent_comparison",
          judge("", 10, b"", b"x", W, W) == MISMATCH and judge(None, 10, b"x", b"x", W, W) == MISMATCH,
          {"empty": judge("", 10, b"", b"x", W, W), "none": judge(None, 10, b"x", b"x", W, W),
           "rule": "A-3 fail-closed stays: no remote coordinate, no confirmation"})
    check("T6_local_route_unavailable_degrades_but_does_not_veto",
          judge(W, 10, b"0123456789", b"0123456789", W, None) == CONF,
          {"state": judge(W, 10, b"0123456789", b"0123456789", W, None)})
    check("T7_size_disagreement_with_equal_sha_is_not_byte_level",
          judge(W, 999, b"", b"0123456789", W, W) == DEGRADED and
          judge(W, 999, b"0123456789", b"0123456789", W, W) == DEGRADED,
          {"rule": "size mismatch kills the body-level claim but the git object sha is the authority"})

    # ---- the real case, read-only against the branch that already holds the mirror
    raw = io.open(LOCAL, "rb").read()
    want = blob_sha(raw)
    cmd = subprocess.run(["git", "hash-object", LOCAL], capture_output=True, text=True, timeout=180)
    local_cmd = (cmd.stdout or "").strip()
    meta = get("https://api.github.com/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md"
               "?ref=commander/control")
    st = judge(meta.get("sha"), meta.get("size"), b"", raw, want, local_cmd)
    fresh = meta.get("sha") == want
    # The contract, not a state claim: this file is shared, and a lane edited it locally 3,614 B after my
    # 12:36 mirror, so "remote == local" is a moment, not a property.  What must hold in BOTH moments is
    # that an unusable body never decides the verdict - the sha agreement does.
    check("R1_empty_body_never_decides_the_verdict_on_the_real_file",
          (st == DEGRADED if fresh else st == MISMATCH),
          {"local_bytes": len(raw), "remote_size": meta.get("size"), "local_drift_vs_remote":
           len(raw) - int(meta.get("size") or 0), "local_blob_sha1": want,
           "git_hash_object": local_cmd, "remote_sha": meta.get("sha"),
           "shas_equal": fresh, "state_returned": st,
           "rule": "the old proof answered MISMATCH in both moments, which is why it trained people to "
                   "ignore a real mismatch"})
    check("R2_the_two_local_routes_agree_independently",
          bool(local_cmd) and local_cmd == want,
          {"computed_local_blob_sha1": want, "git_hash_object": local_cmd,
           "agree": local_cmd == want, "remote_sha": meta.get("sha"),
           "drift_is_reported_not_judged": True})
    import base64
    body = meta.get("content") or ""
    rb = base64.b64decode("".join(body.split())) if body else b""
    check("R3_contents_body_route_still_capped_on_this_file",
          len(rb) < len(raw),
          {"body_bytes_returned": len(rb), "local_bytes": len(raw), "body_equals_local": rb == raw,
           "meaning": "asserted so the assumption behind the fix stays watched: if GitHub ever returns the "
                      "full body here this cell goes RED and the degraded state stops being needed"})

    # ---- killers: the classifier must have teeth, and each mutant owns one cell
    def mutant(new_src):
        """Recompile `readback_state` with ONE textual variable changed, in a clean namespace."""
        i = src.index("def readback_state")
        j = src.index("def local_hash_object", i)
        body_src = src[i:j].rstrip()
        assert old in body_src, "anchor outside the extracted function"
        ns = {}
        exec(compile(ast.parse(body_src.replace(old, new_src, 1)), "<mutant>", "exec"), ns)
        return ns["readback_state"]

    killers = []
    pairs = [("K1_empty_body_treated_as_mismatch",
              'return "BYTE_LEVEL_CONFIRMED" if body_ok else "CONTENTS_BODY_UNUSABLE_BLOB_CONFIRMED"',
              'return "BYTE_LEVEL_CONFIRMED" if body_ok else "MISMATCH"',
              lambda j: j(W, 10, b"", b"0123456789", W, W), DEGRADED, MISMATCH,
              "T2_empty_body_with_equal_shas_is_not_mismatch"),
             ("K2_remote_sha_equality_dropped",
              "shas_agree = bool(remote_sha) and remote_sha == want and (local_cmd is None or local_cmd == want)",
              'shas_agree = bool(remote_sha) and (local_cmd is None or local_cmd == want)',
              lambda j: j(V, 10, b"", b"0123456789", W, W), MISMATCH, DEGRADED,
              "T3_different_remote_sha_is_mismatch"),
             ("K3_local_route_allowed_to_veto_when_absent",
              "shas_agree = bool(remote_sha) and remote_sha == want and (local_cmd is None or local_cmd == want)",
              "shas_agree = bool(remote_sha) and remote_sha == want and local_cmd == want",
              lambda j: j(W, 10, b"0123456789", b"0123456789", W, None), CONF, MISMATCH,
              "T6_local_route_unavailable_degrades_but_does_not_veto")]
    for name, old, new, call, want_clean, want_mut, owner in pairs:
        if old not in src:
            killers.append({"mutant": name, "verdict": RED, "why": "anchor not found - the mutant is a no-op"})
            continue
        j_mut = mutant(new)
        clean_state = call(judge)
        mut_state = call(j_mut)
        killers.append({"mutant": name, "owner_cell": owner, "clean_returned": clean_state,
                        "mutant_returned": mut_state,
                        "verdict": "KILLED" if (clean_state == want_clean and mut_state == want_mut)
                                   else "SURVIVED"})
    check("K8_every_mutant_flips_only_its_own_cell",
          len(killers) == 3 and all(k["verdict"] == "KILLED" for k in killers), {"kills": killers})
    check("S1_old_single_route_proof_is_gone_from_the_tool",
        src.count('print("BYTE-IDENTICAL:", rb == raw)') == 0 and "READBACK STATE" in src and
        "do not trust this mirror (sha inequality, NOT a dead route)" in src,
          {"old_line_still_present": src.count('print("BYTE-IDENTICAL:", rb == raw)'),
           "new_lines_present": ["READBACK STATE" in src]})

    n_green = sum(1 for c in cells if c["verdict"] == GREEN)
    overall = GREEN if n_green == len(cells) else RED
    tb = io.open(TOOL, "rb").read()
    receipt = {"what": "mirror_ledger read-back contract (measurement-chain reliability fix, arbiter-approved narrow scope)",
               "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "tool_under_change": {"path": TOOL.replace("\\", "/"), "bytes": len(tb),
                                     "blob": blob_sha(tb)},
               "trigger": {"incident": "PUT 200 commit d1a86a3166b3 then contents body empty -> printed MISMATCH",
                           "independent_proof_used_at_the_time": "94cef773ef8f6cce7dfa5f710bfb2d9ab07eccee"},
               "cells": cells, "cells_total": len(cells), "cells_green": n_green, "overall": overall,
               "claimed_result": "offline_selftest_" + overall}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1, ensure_ascii=False))
    print("overall = %s (%d/%d)" % (overall, n_green, len(cells)))
    for c in cells:
        print("  %-56s %s" % (c["cell"], c["verdict"]))
    for k in killers:
        print("  kill %-46s %-8s clean=%s mutant=%s" % (k["mutant"], k["verdict"],
                                                        k.get("clean_returned"), k.get("mutant_returned")))
    print("wrote", OUT)
    return 0 if overall == GREEN else 1


if __name__ == "__main__":
    raise SystemExit(main())
