"""ORD-0500 r18: prove the arm's ref discovery cannot publish a truncated denominator.

Why this exists: `branch_emit_arm` asks the server which refs this order has.  At 21:44 one unpatterned
`ls-remote --refs origin` answered with 5 of an 18-ref family (r5..r9) while other runs returned all 18,
and the loop stopped at the first non-empty read -- so the receipt's denominator became whatever the
transport happened to hand back, and the page would have said "N published refs, M of them ran" about a
half-read.  A truncation cannot be ordered from the network on demand, so the arms below DRIVE it with a
stubbed read (deterministic), and the real remote is only OBSERVED, never claimed as a proof.

  M1  reads alternate short/full            -> refs_in_family must refuse (ABORT_REF_READ_UNSTABLE)
  M2  every read comes back short          -> it must refuse rather than publish 5
  C1  two identical full reads             -> it returns all 18, no refusal
  O1  the real origin, patterned x3        -> recorded sizes; no verdict claimed

Writes evidence/ref_discovery_arm_<REFDISC_OUT or r17>.json.
"""
import json
import os
import re
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EV = os.path.join(LANE, "evidence")
sys.path.insert(0, os.path.join(LANE, "tools"))
import branch_emit_arm_r16 as A          # the instrument under test

FULL = ["refs/heads/review/newlane-ord0500-phone-checkin-entry-r%d" % i for i in range(1, 19)]
SHORT = FULL[4:9]                          # exactly what the 21:44 read handed back


def run_arm(name, responses, expect):
    """Run refs_in_family() with a stubbed transport and classify what it did.

    `expect["own"]` is the ref this hand would have just pushed: the arm sets the same environment the
    chain sets, so the own-ref guard is exercised the way production exercises it.
    """
    original = A.sh
    holder = {}
    previous_own = os.environ.get("BRANCH_EMIT_EXCLUDE")
    if "own" in expect:
        os.environ["BRANCH_EMIT_EXCLUDE"] = expect["own"]

    def fake(args, cwd=None):
        body = responses.pop(0) if responses else holder.get("last", [])
        holder["last"] = body
        return 0, "".join("%040x\t%s\n" % (1, r) for r in body)
    A.sh = fake
    try:
        got = A.refs_in_family()
        verdict = "RETURNED"
        detail = {"count": len(got), "sample": [g.rsplit("-", 1)[-1] for g in got][:4]}
    except SystemExit as exc:
        verdict = "REFUSED"
        detail = {"message": str(exc)[:180]}
    finally:
        A.sh = original
        if "own" in expect:
            if previous_own is None:
                os.environ.pop("BRANCH_EMIT_EXCLUDE", None)
            else:
                os.environ["BRANCH_EMIT_EXCLUDE"] = previous_own
    bite = (verdict == expect["want"]) and (expect.get("needle") is None
                                            or expect["needle"] in detail.get("message", ""))
    return {"id": name, "expect": expect["said"], "verdict": verdict, "detail": detail,
            "bite": bite}


def observe_real():
    sizes = []
    for _ in range(3):
        rc, out = A.sh(["ls-remote", "--refs", "origin", A.FAMILY + "*"])
        if rc == 0:
            sizes.append(len({l.split()[1] for l in out.splitlines()
                              if len(l.split()) == 2 and l.split()[1].startswith(A.FAMILY)}))
    return {"patterned_read_sizes": sizes, "agree": len(set(sizes)) == 1,
            "claim": "OBSERVATION ONLY: what the transport answered three times just now"}


def main():
    rows = [
        run_arm("M1_alternating_short_full", [FULL, SHORT, FULL, SHORT, FULL, FULL],
                {"want": "REFUSED", "needle": "ABORT_REF_READ_UNSTABLE", "own": "r18",
                 "said": "两趟读数不一致 → 必须拒发分母"}),
        run_arm("M2_every_read_short", [SHORT, SHORT, SHORT, SHORT],
                {"want": "REFUSED", "needle": "ABORT_REF_READ_MISSING_OWN_REF", "own": "r18",
                 "said": "三趟都一样地短（少了 r18）→ 一致不等于完整，必须拒"}),
        run_arm("C1_two_full_reads", [FULL, FULL],
                {"want": "RETURNED", "own": "r18", "said": "两趟相同、完整、含我自己刚推的枝 → 18 枚照收"}),
    ]
    obs = observe_real()
    out = {"tool": os.environ.get("REFDISC_TOOL") or "ref_discovery_arm_r17",
           "took_local": datetime.now().astimezone().isoformat(timespec="seconds"),
           "family_size_from_a_full_read": len(FULL), "runs": rows,
           "observation": obs, "every_arm_bit": all(r["bite"] for r in rows),
           "note": "the truncation is driven by a stub because the network cannot be ordered to truncate "
                   "on request; the real remote is observed and reported, not used as a proof"}
    dest = os.path.join(EV, os.environ.get("REFDISC_OUT") or "ref_discovery_arm_r17.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"every_arm_bit": out["every_arm_bit"],
                      "arms": [(r["id"], r["verdict"], r["bite"]) for r in rows],
                      "observation": obs, "receipt": os.path.basename(dest)},
                     indent=2, ensure_ascii=False))
    return 0 if out["every_arm_bit"] else 1


if __name__ == "__main__":
    sys.exit(main())
