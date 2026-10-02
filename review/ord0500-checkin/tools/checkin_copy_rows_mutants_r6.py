"""ORD-0500 r6: run the row gate against a mutation and prove it reddens, then prove the revert.

Two mutations, each aimed at a different assertion, because a gate that only ever catches one thing
proves only that one thing:
  M1 puts the hard-coded 打卡 back into the English row (the defect this order fixes) -> A1 + B2;
  M2 drops the `button:` argument from the call site while leaving the row interpolated -> B1, i.e.
     the screen would render the literal characters `{button}` at a traveller.
The scratch tree holds copies of only the three files the gate reads, so nothing under wt22 is edited;
each mutation is reverted by writing the original bytes back and re-running the gate, which must go
green again -- and the byte digests before and after must be the same.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
SRC = os.path.join(LANE, "wt22")
SCRATCH = os.path.join(LANE, "mut_r6")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
FILES = ["frontend/src/features/checkin/checkinCopy.ts",
         "frontend/src/features/trip/TripItinerary.tsx",
         "frontend/src/i18n/LocaleContext.tsx"]


def digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def stage():
    if os.path.exists(SCRATCH):
        shutil.rmtree(SCRATCH)
    for rel in FILES:
        dst = os.path.join(SCRATCH, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, rel), dst)
    return {rel: digest(os.path.join(SCRATCH, rel)) for rel in FILES}


def run_gate(tag):
    """The gate writes its own receipt per invocation; the verdict is read from that file, never
    parsed back out of stdout (an earlier version of this tool did, and reported `null` verdicts)."""
    receipt = os.path.join(LANE, "evidence", "checkin_copy_rows_r6_%s.json" % tag)
    if os.path.exists(receipt):
        os.remove(receipt)
    p = subprocess.run([PY, "-X", "utf8", os.path.join(LANE, "tools", "checkin_copy_rows_r6.py"),
                        SCRATCH, receipt], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300)
    data = json.load(open(receipt, encoding="utf-8")) if os.path.exists(receipt) else {"MISSING": True}
    return p.returncode, data


def edit(rel, old, new):
    p = os.path.join(SCRATCH, rel)
    t = open(p, encoding="utf-8").read()
    if t.count(old) != 1:
        raise SystemExit("ABORT_PATCH_SHAPE %s -- %r appears %d times" % (rel, old[:40], t.count(old)))
    open(p, "w", encoding="utf-8", newline="").write(t.replace(old, new))


def main():
    before = stage()
    rc0, green = run_gate("control")
    report = {"tool": "checkin_copy_rows_mutants_r6",
              "took_local": datetime.now().astimezone().isoformat(),
              "control_exit": rc0, "control_verdict": green.get("verdict"),
              "mutants": []}
    copy_rel, screen_rel = FILES[0], FILES[1]

    edit(copy_rel, 'en: "This stamp did not name a stop, so nothing was written. Tap {button} on one of the stops.",',
         'en: "This stamp did not name a stop, so nothing was written. Tap 打卡 on one of the stops.",')
    rc1, m1 = run_gate("M1")
    report["mutants"].append({"id": "M1_hard_coded_label_back", "expected": "RED",
                              "exit": rc1, "verdict": m1.get("verdict"),
                              "cases": sorted({f.get("case") for f in m1.get("findings", [])}),
                              "evidence_lines": [f.get("line") for f in m1.get("findings", [])]})
    edit(copy_rel, 'en: "This stamp did not name a stop, so nothing was written. Tap 打卡 on one of the stops.",',
         'en: "This stamp did not name a stop, so nothing was written. Tap {button} on one of the stops.",')
    rc1b, reverted1 = run_gate("M1_revert")
    report["mutants"][-1]["revert_exit"] = rc1b
    report["mutants"][-1]["revert_verdict"] = reverted1.get("verdict")
    report["mutants"][-1]["bytes_restored"] = digest(os.path.join(SCRATCH, copy_rel)) == before[copy_rel]

    edit(screen_rel, "if (key) return wordsFor(CHECKIN_COPY[key], zh, { button: t(\"checkin.button\") });",
         "if (key) return wordsFor(CHECKIN_COPY[key], zh);")
    rc2, m2 = run_gate("M2")
    report["mutants"].append({"id": "M2_placeholder_left_unsupplied", "expected": "RED",
                              "exit": rc2, "verdict": m2.get("verdict"),
                              "cases": sorted({f.get("case") for f in m2.get("findings", [])}),
                              "evidence_lines": [f.get("line") for f in m2.get("findings", [])]})
    edit(screen_rel, "if (key) return wordsFor(CHECKIN_COPY[key], zh);",
         "if (key) return wordsFor(CHECKIN_COPY[key], zh, { button: t(\"checkin.button\") });")
    rc2b, reverted2 = run_gate("M2_revert")
    report["mutants"][-1]["revert_exit"] = rc2b
    report["mutants"][-1]["revert_verdict"] = reverted2.get("verdict")
    report["mutants"][-1]["bytes_restored"] = digest(os.path.join(SCRATCH, screen_rel)) == before[screen_rel]

    report["scratch_isolated_from_wt22"] = all(
        digest(os.path.join(SCRATCH, rel)) == digest(os.path.join(SRC, rel)) for rel in FILES)
    report["digests"] = before
    report["every_mutant_bit"] = all(m["exit"] != 0 and m["revert_exit"] == 0
                                     and m["bytes_restored"] for m in report["mutants"])
    path = os.path.join(LANE, "evidence", "checkin_copy_rows_mutants_r6.json")
    json.dump(report, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if report["every_mutant_bit"] and rc0 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
