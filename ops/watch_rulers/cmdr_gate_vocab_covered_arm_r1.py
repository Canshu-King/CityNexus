"""CMDR vocabulary-coverage arm r1 -- every name the backend can write must have a row in the word table.

Why this arm and not the one I first built: my `cmdr_pick_closed_lookup_r1.py` flags `pick()`'s miss branch
for handing the caller's input back.  Measured at the line today (tip read in this file's own run), that
branch wraps the value in `rawChannel` ("这台服务器写的：…"), and the arbiter's ruling on ORD-0551 kept that
fallback and landed the *coverage* fix instead -- so wiring that ruler as a gate arm would turn every future
landing red on a shape the project decided to keep.  The invariant that actually protects the traveller is
this one: for each family, the set of names the backend can emit must be a subset of the table's keys, so the
labelled-raw branch is unreachable in normal operation.

Families are declared as (backend source, how to read its writable names, frontend table).  An unreadable
source or an empty table is ABORT, never PASS -- a blind arm is itself a defect.
"""
import argparse
import json
import re
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
VOCAB = "frontend/src/lib/displayVocabulary.ts"

FAMILIES = [
    {"name": "RUNTIME_IDENTITY",
     "backend": "backend/app/agent/runtime_identity.py",
     "how": "module-level NAME = \"NAME\" assignments",
     "extract": r'^([A-Z][A-Z0-9_]{3,})\s*=\s*"\1"\s*$'},
    {"name": "MOBILITY_FACT_QUALITY",
     "backend": "backend/app/replanning/provider_snapshots.py",
     "how": "module-level NAME = \"NAME\" assignments, excluding the frozenset members line",
     "extract": r'^([A-Z][A-Z0-9_]{3,})\s*=\s*"\1"\s*$'},
]


def show(rev, path):
    r = subprocess.run(["git", "-C", REPO, "show", rev + ":" + path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (None, r.stderr.strip()[:160]) if r.returncode != 0 else (r.stdout, None)


def table_keys(vocab_src, table):
    i = vocab_src.find("const " + table)
    if i < 0:
        return None
    j = vocab_src.find("{", i)
    depth = 0
    for k in range(j, len(vocab_src)):
        if vocab_src[k] == "{":
            depth += 1
        elif vocab_src[k] == "}":
            depth -= 1
            if depth == 0:
                body = vocab_src[j + 1:k]
                break
    else:
        return None
    return [m.group(1) for m in re.finditer(r'^\s*([A-Z][A-Z0-9_]{3,})\s*:', body, re.M)]


def backend_names(src, pattern):
    out = []
    for line in src.splitlines():
        m = re.match(pattern, line)
        if m:
            out.append(m.group(1))
    return out


def evaluate(rev, drop_key=""):
    vocab, err = show(rev, VOCAB)
    if vocab is None:
        return {"verdict": "ABORT", "why": "cannot read " + VOCAB + ": " + (err or "")}
    rows, problems = [], []
    for fam in FAMILIES:
        bsrc, berr = show(rev, fam["backend"])
        if bsrc is None:
            return {"verdict": "ABORT", "why": "cannot read " + fam["backend"] + ": " + (berr or "")}
        names = backend_names(bsrc, fam["extract"])
        keys = table_keys(vocab, fam["name"])
        if drop_key and drop_key[0] == fam["name"]:
            keys = [k for k in (keys or []) if k != drop_key[1]]
        if not names:
            return {"verdict": "ABORT", "why": fam["name"] + ": backend yields no names -- the extractor "
                                              "no longer matches " + fam["backend"]}
        if not keys:
            return {"verdict": "ABORT", "why": fam["name"] + ": table parsed empty -- nothing to match against"}
        missing = [n for n in names if n not in keys]
        extra = [k for k in keys if k not in names]
        rows.append({"family": fam["name"], "backend_writable": len(names), "table_keys": len(keys),
                     "missing_rows": missing, "table_only": extra})
        problems += [fam["name"] + "/" + m for m in missing]
    return {"verdict": "FAIL" if problems else "PASS", "families": rows, "missing": problems}


ap = argparse.ArgumentParser()
ap.add_argument("--rev", required=True)
ap.add_argument("--selftest", action="store_true")
a = ap.parse_args()

report = {"arm": "cmdr_gate_vocab_covered_arm_r1", "rev": a.rev, "vocab": VOCAB,
          "families": [f["name"] for f in FAMILIES]}
real = evaluate(a.rev)
report["against_line"] = real

if a.selftest:
    # the time it should be red: drop one real table row and re-evaluate the same rev
    probe = evaluate(a.rev, drop_key=("RUNTIME_IDENTITY", "NOT_CONFIGURED"))
    report["selftest"] = {"dropped_row": "RUNTIME_IDENTITY/NOT_CONFIGURED", "verdict": probe["verdict"],
                          "missing": probe.get("missing")}
    ok = real["verdict"] == "PASS" and probe["verdict"] == "FAIL"
    report["arm_discriminates"] = ok
    print(json.dumps(report, ensure_ascii=False, indent=1)[:2400])
    sys.exit(0 if ok else 5)

print(json.dumps(report, ensure_ascii=False, indent=1)[:2400])
sys.exit(0 if real["verdict"] == "PASS" else 1)
