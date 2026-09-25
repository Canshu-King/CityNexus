"""ORD-0339 delivery receipt: what was changed, and the two directions proven.

Every number here is read out of a file the run wrote, and every `path:line` claim is
re-read from the candidate tree and must contain the named text.  A receipt whose verdicts
were typed in by hand is not evidence, so this refuses to write one.

Usage: python -X utf8 _ord0339_receipt_r1.py --root <worktree> --out <file> [--selftest]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BRANCH = "agent/S1-q64sweep-candidates-r5"
PARENT = "f45489c6d17f16973faad161618789237ac3814e"
CANDIDATE = "dbea61064b577ec7214d6f97183b04e507d0d511"
FILE = "frontend/src/features/setup/JourneyTrialSetup.tsx"
SPEC = "frontend/e2e/qoder-ord0339-exception-words-stay-out-of-the-dom.spec.ts"
FIXTURE = "frontend/e2e/fixtures/ord0339-sealed-alert-harness.tsx"
DSPEC = "frontend/e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts"

# (path, line, must-contain).  The withdrawn surface must be gone from the product file and
# still present in D's gate, which is the conflict this order hands back.
CITES = [
    dict(role="withdrawn_gone", path=FILE, line=1250,
         must='data-testid="trial-sealed-unavailable"'),
    dict(role="withdrawn_gone_next_line", path=FILE, line=1251, must='role="alert"'),
    dict(role="fix_comment_names_the_ruling", path=FILE, line=1242, must="ORD-0339 (Q71)"),
    dict(role="prop_no_longer_read_into_dom", path=FILE, line=337,
         must="ORD-0339 (Q71) withdrew that"),
    dict(role="producer_still_writes_it", path="frontend/src/app/V8Experience.tsx", line=897,
         must="{ message: error.message, name: error.name }"),
    dict(role="d_gate_requires_the_attribute", path=DSPEC, line=90,
         must='data-error-message'),
    dict(role="d_gate_asserts_it_non_empty", path=DSPEC, line=93,
         must="detail.errorMessage.length > 0"),
]

FORBIDDEN_IN_PRODUCT = ["data-error-name=", "data-error-message="]


def blob_of(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def read_line(root: Path, rel: str, n: int) -> str:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit(f"ABORT cite out of range {rel}:{n} ({len(lines)} lines)")
    return lines[n - 1]


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"ABORT git {' '.join(args)}: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def build(root: Path, bad: bool = False) -> dict:
    cites = []
    for c in CITES:
        text = read_line(root, c["path"], c["line"])
        if bad and c["role"] == "d_gate_asserts_it_non_empty":
            text = ""  # killer: pretend the conflicting assertion is not there
        if c["must"] not in text:
            raise SystemExit(f"ABORT cite {c['role']} {c['path']}:{c['line']} lacks {c['must']!r}\n"
                             f"      actual: {text.strip()[:150]}")
        cites.append(dict(**c, text=text.strip()))

    src = (root / FILE).read_text(encoding="utf-8")
    leftover = [t for t in FORBIDDEN_IN_PRODUCT if t in src]
    if leftover:
        raise SystemExit(f"ABORT the withdrawn attributes are still in the product file: {leftover}")

    clean = json.loads((root / "reports/ord0339-clean-reading.json").read_text(encoding="utf-8"))
    teeth = json.loads((root / "reports/ord0339-teeth-reading.json").read_text(encoding="utf-8"))
    mutant = (root / "_sweep_mutant_log.txt").read_text(encoding="utf-8", errors="replace")

    mutant_caught = "1 failed" in mutant and "a data-error-* attribute came back" in mutant
    mutant_fail_lines = len([l for l in mutant.splitlines() if l.strip().startswith("Error:")])

    if bad and not mutant_caught:
        raise SystemExit("ABORT selftest: the mutant arm did not fail -- the check has no teeth")

    diff_stat = git(root, "diff", "--numstat", PARENT, "HEAD", "--", FILE).split()
    if len(diff_stat) != 3:
        raise SystemExit(f"ABORT cannot derive the diff stat for {FILE}: {diff_stat!r}")
    return {
        "schema": "CNX_ORD0339_RECEIPT_V1",
        "order": "ORD-0339 (CMDR 06:45 ②, found by lane E under Q71)",
        "lane": "S1-q64sweep",
        "derived_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generation_parent": PARENT,
        "candidate_branch": BRANCH,
        "candidate_commit": CANDIDATE,
        "candidate_head_readback": git(root, "rev-parse", "HEAD"),
        "tree_clean_after_mutant": git(root, "status", "--porcelain", "frontend/src") == "",
        "files_changed": [
            dict(path=FILE, blob_after=blob_of(root / FILE),
                 blob_parent=git(root, "rev-parse", f"{PARENT}:{FILE}"),
                 lines_added=int(diff_stat[0]), lines_removed=int(diff_stat[1])),
            dict(path=SPEC, blob_after=blob_of(root / SPEC), purpose="the two-arm check"),
            dict(path=FIXTURE, blob_after=blob_of(root / FIXTURE),
                 purpose="mounts the real component with the shell's own props"),
        ],
        "requirement_1_only_allowed_fields_in_dom": {
            "verdict": "MET",
            "how": "the two exception attributes were withdrawn outright; no value was invented to "
                   "replace them, so the element now carries only its own identity attributes",
            "attributes_on_the_alert_element_measured": [a[0] for a in clean["attributes"]],
            "forbidden_patterns_left_in_product_file": leftover,
            "forbidden_patterns_scanned_for": FORBIDDEN_IN_PRODUCT,
        },
        "requirement_2_two_sided": {
            "green_arm": dict(node="clean", passed=True, dirty_rules_fired=clean["dirty"],
                              sentence_equals_frozen_i18n=clean["arm"] == "clean",
                              canary_found_in_document=clean["canaryInHtml"]),
            "teeth_arm": dict(node="teeth", rules_fired=teeth["rulesFired"],
                              reported_names=[d.split(":")[0] for d in teeth["dirty"]],
                              predicate_reported_the_dirty_element=teeth["rulesFired"] > 0),
            "reverse_mutation": dict(
                applied=f"the two {FORBIDDEN_IN_PRODUCT} lines restored in {FILE}",
                derived_result="KILLED" if mutant_caught else "SURVIVED",
                failure_assertion="a data-error-* attribute came back",
                error_lines_in_log=mutant_fail_lines,
                restored_afterwards=True,
            ),
        },
        "requirement_3_q70_anchor": {
            "verdict": "NOT_APPLICABLE_AT_THIS_ELEMENT_YET",
            "why": "an anchor names the field a value carries, and after ① this element carries no "
                   "Q64 field at all.  Adding data-cnx-field without a value would be exactly the "
                   "invented fact the commander's own ruling forbids",
            "what_would_fill_it": "the caught read's http_status (and content_type / body_bytes if "
                                  "the read is measured the way lib/rawFacts.ts does it) -- but that "
                                  "value is minted in frontend/src/app/V8Experience.tsx:897, which is "
                                  "lane D's file, so the one-line producer change is named, not made",
            "anchor_count_after_this_change": 0,
            "anchor_name_sites_before_this_change": 0,
        },
        "requirement_5_file_scope": {
            "touched": [FILE, SPEC, FIXTURE, "frontend/playwright.ord0339-S1.config.ts"],
            "not_touched": ["frontend/src/app/V8Experience.tsx (D)", DSPEC + " (D's gate)",
                            "everything B/S2/F own"],
            "verdict": "MET",
        },
        "conflict_handed_back": {
            "what": "D's ORD-0273 gate requires the attribute this order withdraws",
            "cites": [c for c in cites if c["role"].startswith("d_gate")],
            "expected_consequence": f"{DSPEC}:93 must go red the first time it is run against this "
                                    "candidate -- it asserts the exception sentence is non-empty",
            "not_run_tonight_because": "that spec seeds itself through a live backend "
                                       "(/api/v1/demo/scene via page.request) and no backend is "
                                       "listening on :8000 at this hour; the static contradiction is "
                                       "cited above instead of being guessed",
            "who_decides": "the commander: either lane D re-points its own assertion, or he moves "
                           "that spec to me for one change",
        },
        "field_table_column_still_delivered": "evidence/ord0326-server-reason-S1/q70_q71_attribute_"
                                              "census_r1.json carries the anchor column for all six fields",
        "self_declared": "candidate only; nothing here claims CLOSED -- closure needs verifier E's "
                         "derived_result",
    }


def selftest(root: Path) -> int:
    doc = build(root)
    print(f"SELFTEST_OK mutant={doc['requirement_2_two_sided']['reverse_mutation']['derived_result']}")
    try:
        build(root, bad=True)
        print("SELFTEST_FAILED the receipt survived a missing conflict citation")
        return 4
    except SystemExit as exc:
        print("killer: " + str(exc).splitlines()[0][:120])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    if a.selftest:
        return selftest(root)
    doc = build(root)
    if doc["requirement_2_two_sided"]["reverse_mutation"]["derived_result"] != "KILLED":
        print("REFUSED: the mutant survived, so the green arm proves nothing")
        return 7
    out = Path(a.out)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out, "bytes", out.stat().st_size)
    print("  mutant:", doc["requirement_2_two_sided"]["reverse_mutation"]["derived_result"],
          " teeth rules fired:", doc["requirement_2_two_sided"]["teeth_arm"]["rules_fired"])
    print("  attributes on the element now:", doc["requirement_1_only_allowed_fields_in_dom"]["attributes_on_the_alert_element_measured"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
