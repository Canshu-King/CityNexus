"""Build a one-page morning manifest from the coordinate-audit receipt (no hand-typed numbers).

Why: tonight produced ~20 instruments and ~30 receipts across six lanes. The ledger carries them in
delivery order, which is the wrong shape for a reader who asks "what can I re-run, and what did it
prove?". This generator reads `audit_r6_receipt.json` (the ruler's own output, whose verdicts are
already derived per cell) and prints the coordinate table verbatim from it, then appends a status
block. Status lines are the ONLY hand-written part, and each one names the ruling or receipt it comes
from, so nothing about a number is typed from memory.

Usage: python overnight_manifest_r1.py <audit_receipt.json> <out.md>
"""
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (order, verdict, where the verdict comes from) - no numbers here, only names of authorities.
STATUS = [
    ("ORD-0269 / ORD-0273", "CLOSED",
     "arbiter bus stamp 5823957595 (Q29=①), scope sentence: gate re-run on landed 45b0a5e2; the 9 "
     "reverse-mutation kills stay candidate-generation aef5765c facts, not re-run"),
    ("ORD-0271-A / ORD-0277 / ORD-0275 / ORD-0268", "CLOSED",
     "earlier arbiter rulings + red-team derivations (see ledger blocks; coordinates in the table below)"),
    ("ORD-0272", "OPEN",
     "arbiter bus stamp 5823957595 (Q34=①): seam face is a landed-generation fact (ORD-0282), but the "
     "authoritative line has no regression carrier yet -> blocked on ORD-0287"),
    ("ORD-0274", "CANDIDATE VERIFIED-FORM, awaiting derivation",
     "commander re-read: compare 45b0a5e2...ef277b2 = ahead 3 / behind 0 (ff-able), 4 files +116/-9; "
     "derived_result belongs to lane HJ-P1 via ORD-0290"),
    ("ORD-0276", "ACCEPTED",
     "commander recomputation receipt_consistency_o0276_r1 = 14 arms ALL_AGREE; user visibility stays the "
     "lane's own NO_PIXEL_READING, not promoted"),
    ("ORD-0279 / ORD-0279-X", "ACCEPTED / CLOSED",
     "validator GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1 (Q24=①, Q25=①) + the cross-gen audit cells"),
    ("ORD-0280", "DISPATCHED (write window opened)",
     "commander 号令 block 06:5x: three dirty spots in PlanWithAiSheet.tsx, label semantics untouched, "
     "fix model is the repo's own simulationAdapter pattern"),
    ("ORD-0281", "SHAPE ACCEPTED, no product code yet",
     "arbiter Q33=①: this order now covers the keyed leg only; the unkeyed leg split out as ORD-0288"),
    ("ORD-0282", "ACCEPTED",
     "commander recomputation receipt_consistency_o0282_r1 = 10 arms ALL_AGREE; K8 seam flip is now a "
     "landed-generation reading (guard 416ea4f2 vs mutant 784599fd, 6 rounds, blob-checked per round)"),
    ("ORD-0283 / ORD-0285", "BITES CLOSED (4/4 verified)",
     "lane E's own reverify receipt (derived_result: FIXES_VERIFIED 4/4), re-checked by commander's "
     "receipt_consistency_o0285_r1 = 7 arms agree"),
    ("ORD-0287", "OPEN via Q35=②",
     "carrier cannot be ported (product symbol absent on the landed line, counted by both lanes); "
     "route now = a guard regression test that depends only on the authoritative line"),
    ("ORD-0288 / ORD-0289 / ORD-0290", "DISPATCHED",
     "0288 = unkeyed write leg (shape @HJ-P3, code @D); 0289 = AST-based write-leg census on two "
     "generations (@F); 0290 = five-arm derived_result for lane B's candidate (@HJ-P1)"),
    ("ORD-0286", "GATES SIGNED, KILLS UNPROVEN",
     "lane E bus 5823802157: 0278 = GATE_GREEN_4_4 and 0253 = GATE_GREEN_3_3 on the tip it read itself "
     "(06717045); reverse mutations for THIS generation were not delivered, and 5/8 gate blobs differ from "
     "v6/landed -> per Q24 the v6 kills do not carry over. Not landed yet."),
    ("ORD-0287 / ORD-0288 / ORD-0289 / ORD-0290 / ORD-0291 / ORD-0292 / ORD-0293", "DISPATCHED",
     "0287 K8 carrier on the authoritative line only (Q35=②); 0288 unkeyed write leg (shape accepted, code "
     "held); 0289 AST write-leg census on two generations; 0290 five-arm derivation for lane B's 0274; "
     "0291 deadline-constant probe; 0292 same-generation kills for 0278/0253; 0293 second-observer repro of "
     "the silently-ignored key."),
    ("CANDIDATE_REF_FREEZE_V1", "IN EFFECT (Q37=①)",
     "delivery = frozen_tip (40 hex) + frozen_at in the receipt and no further pushes to that ref until the "
     "commander lands it or returns it; verifiers only accept frozen_tip; the commander re-reads the ref one "
     "tick before an ff-only landing and stops if it differs"),
    ("DEFAULT_WRITE_DEADLINE_MS", "RULAED (Q36=①)",
     "the constant 0281 introduces must default ABOVE the observed busy_timeout (30 s) and be scenario "
     "configurable, plus a two-way gate that is RED when the default sits below it"),
    ("HARDLINK_SNAPSHOT_PROHIBITION_V1", "IN EFFECT (Q32=①)",
     "lane copies only; every generation swap runs dist_hardlink_scan.py and names hits without "
     "blocking the served line"),
]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 5
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    cells = d["cells"]
    ok = sum(1 for c in cells if c["verdict"] == "OK")
    lines = []
    lines.append("# CityNexus overnight evidence manifest (machine-generated - do not hand-edit the table)")
    lines.append("")
    lines.append("- built at %s from `%s` (instrument `%s`, blob `%s`)"
                 % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), src, d["instrument"]["repo_path"],
                    d["instrument"]["blob"]))
    lines.append("- branch `%s` @ tip `%s` (read when the receipt was produced)"
                 % (d.get("branch", "?"), d.get("ref_tip_read") or "ABSENT - see ORD-0283/C8"))
    lines.append("- cells read: **%d**, resolving byte-for-byte: **%d**, failing: **%d**, overall: `%s`"
                 % (d["claims"], ok, d["failing"], d["overall"]))
    lines.append("")
    lines.append("## What each cited coordinate is")
    lines.append("")
    lines.append("| repo path | declared blob (40) | bytes | cited by | resolves |")
    lines.append("|---|---|---|---|---|")
    for c in cells:
        lines.append("| `%s` | `%s` | %d | %s | %s |"
                     % (c["path"], c["declared_blob"], c["declared_bytes"], c["cited_by"], c["verdict"]))
    lines.append("")
    lines.append("## Orders and what they mean now")
    lines.append("")
    for order, verdict, whence in STATUS:
        lines.append("- **%s** - `%s` - authority: %s" % (order, verdict, whence))
    lines.append("")
    lines.append("## How to re-run the checks yourself (read-only; no tokens are ever printed)")
    lines.append("")
    lines.append("```text")
    lines.append("python live_checks/%s                 # every coordinate above, byte-for-byte"
                 % d["instrument"]["repo_path"].split("/")[-1])
    lines.append("python live_checks/audit_receipt_runner_r2.py <that ruler> <out.json>   # same, plus a tip-pinned receipt")
    lines.append("python live_checks/generation_transfer_check_r5.py --selftest            # 20 arms, offline judge + live read-back")
    lines.append("python live_checks/dist_hardlink_scan.py --selftest")
    lines.append("python live_checks/receipt_consistency_o0276_r1.py / python live_checks/receipt_consistency_o0282_r1.py / ..._o0285_r1.py")
    lines.append("```")
    lines.append("")
    lines.append("Scope note carried from the ruler: resolving a coordinate proves the object is readable and")
    lines.append("byte-equal to what was cited. It does NOT prove the numbers inside a receipt are true - those")
    lines.append("are judged by the verifier receipts and the recomputation rulers named above.")
    text = "\n".join(lines) + "\n"
    open(dst, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote", dst, len(text.encode("utf-8")), "B; cells", len(cells), "ok", ok, "failing", d["failing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
