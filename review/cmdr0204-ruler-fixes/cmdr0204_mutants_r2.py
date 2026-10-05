"""Second generation of CMDR 02:04's four counter-checks, with the r1 reporting defect closed.

Why this exists (the r1 defect, measured not assumed):
`cmdr0204_mutants_r1.py:109-112` passes R4's node selection as a bare string, and `run()` does
`args += list(selection)` -- `list(str)` splits a string into single characters, so pytest received
`tests/test_qoder_city_failure_reasons.py` followed by hundreds of one-character arguments.  That is a
usage error: non-zero exit, no summary line, no FAILED line.  r1 still printed `verdict=OK` because its
verdict came from `exit != 0` alone.  So r1's R4 row proved nothing.

Two changes, both about what counts as evidence:
  1. selection is normalised to a list of arguments;
  2. a row is only scored when the run actually produced a parseable summary plus, for a red expectation,
     a FAILED line naming the node under test.  Anything else is `INVALID`, which fails the verdict
     instead of quietly passing it.

r1's file stays on disk exactly as published (instrument code paths are not rewritten; this is a new
generation, per CMDR-0925-2128).  Mutations are restored from a snapshot and the restore is checked by
sha256 and by `git status --porcelain`.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
BACKEND = TREE / "backend"
HYD = BACKEND / "app/catalog_hydration_operations.py"
CITY = BACKEND / "app/integrations/discovery/real_city.py"
T197 = BACKEND / "tests/test_qoder_ord197_four_class_receipt.py"
TCITY = BACKEND / "tests/test_qoder_city_failure_reasons.py"
FILES = [HYD, CITY, T197, TCITY]

HOLD_ANCHOR = '        set_phase(session, operation_id, "DISCOVERING_POIS")'
HOLD_INJECT = "        import time as _hold; _hold.sleep(0.4)\n"
OUTCOME_ANCHOR = "                outcome=OUTCOME_RESOLVER_RUNTIME_FAILURE,"
OUTCOME_MUTANT = "                outcome=OUTCOME_PREPARED,"
MAP_ANCHOR = "            return PROVIDER_SERVER_ERROR"
MAP_MUTANT = "            return PROVIDER_BAD_RESPONSE"
WAIT_LINE = '    job = _wait_closed(a["operation_id"])\n'

R197 = "tests/test_qoder_ord197_four_class_receipt.py"
RCITY = "tests/test_qoder_city_failure_reasons.py"
R3_NODE = "test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage"
R4_NODE = "test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match"
CITY_NODE = "test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def patch(path: pathlib.Path, old: str, new: str, *, insert: bool = False,
          expect: int = 1) -> None:
    text = read(path)
    n = text.count(old)
    assert n == expect, f"anchor count {n} != {expect} in {path.name}"
    out = text.replace(old, new + old) if insert else text.replace(old, new)
    path.write_text(out, encoding="utf-8", newline="")


def run(module: str, selection: list[str], must_name: str) -> dict:
    args = [PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--tb=line", "-rf", module]
    args += [s for s in selection if s]
    proc = subprocess.run(args, cwd=str(BACKEND), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout + proc.stderr
    lines = out.splitlines()
    tb = [l.strip() for l in lines if re.match(r"^[A-Za-z]:\\.*\.py:\d+:", l)]
    failed = [l for l in lines if l.startswith("FAILED")]
    summary = [l for l in lines if re.search(r"\d+ (passed|failed)", l)]
    nodes = sorted({f.split("::")[-1].split(" - ")[0] for f in failed})
    header = [l for l in lines if "test database" in l]
    if not summary:
        shape = "INVALID_no_summary"          # r1's R4 row landed here: a usage error, not a red
    elif proc.returncode == 0:
        shape = "GREEN"
    elif must_name in nodes:
        shape = f"RED_named:{must_name[:28]}"
    else:
        shape = f"RED_unexpected_nodes:{nodes}"
    return {"argv_tail": [a.split("/")[-1][:46] for a in args[args.index(module):]],
            "exit": proc.returncode, "shape": shape,
            "summary": summary[-1].strip("= ") if summary else "(none)",
            "db_header": (header[0][:120] if header else "(none)"),
            "nodes": nodes, "reason": (tb[0][:170] if tb else "(none)")}


def main() -> int:
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    dirty0 = len(subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                                capture_output=True, text=True).stdout.strip().splitlines())
    print(f"tree HEAD={head} | dirty lines before={dirty0}")

    snap = {p: read(p) for p in FILES}
    digests = {p: hashlib.sha256(read(p).encode("utf-8")).hexdigest()[:16] for p in FILES}
    for p, d in digests.items():
        print(f"snapshot {p.name:<44} sha256={d}")
    if snap[T197].count(WAIT_LINE) != 2:
        print("REFUSE: the landed _wait_closed lines are not both present")
        return 8

    def attempt(label: str, want: str, edits: dict, module: str, selection: list[str],
                must_name: str, tries: int = 3) -> bool:
        for p, text in snap.items():
            p.write_text(text, encoding="utf-8", newline="")
        for path, spec in edits.items():
            old, new, insert, n_anchors = spec
            patch(path, old, new, insert=insert, expect=n_anchors)
        rows = [run(module, selection, must_name) for _ in range(tries)]
        shapes = [r["shape"] for r in rows]
        ok = all((s == "GREEN") if want == "green" else s.startswith("RED_named") for s in shapes)
        print(f"\n{label:<32} want={want:<5} runs={shapes} verdict={'OK' if ok else 'NOT_OK'}")
        print(f"   argv={rows[0]['argv_tail']}")
        print(f"   tail={rows[0]['summary']}")
        print(f"   db={rows[0]['db_header']}")
        print(f"   reason={rows[0]['reason']}")
        return ok

    hold = {HYD: (HOLD_ANCHOR, HOLD_INJECT, True, 1)}
    verdicts = []
    verdicts.append(attempt(
        "R1 fixed + 0.4s hold", "green", dict(hold), R197,
        ["-k", f"{R3_NODE} or {R4_NODE}"], R3_NODE))
    verdicts.append(attempt(
        "R2 unfixed + 0.4s hold", "red", {**hold, T197: (WAIT_LINE, "", False, 2)}, R197,
        ["-k", f"{R3_NODE} or {R4_NODE}"], R3_NODE))
    verdicts.append(attempt(
        "R3 outcome written wrong", "red", {HYD: (OUTCOME_ANCHOR, OUTCOME_MUTANT, False, 1)},
        R197, [f"{R197}::{R4_NODE}"], R4_NODE))
    verdicts.append(attempt(
        "R4 5xx mapped back", "red", {CITY: (MAP_ANCHOR, MAP_MUTANT, False, 1)},
        RCITY, [f"{RCITY}::{CITY_NODE}"], CITY_NODE))

    for p, text in snap.items():
        p.write_text(text, encoding="utf-8", newline="")
    bad = [p.name for p in FILES
           if hashlib.sha256(read(p).encode("utf-8")).hexdigest()[:16] != digests[p]]
    dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip().splitlines()
    print(f"\nrestored byte-identical: {'all 4' if not bad else 'FAILED -> ' + str(bad)}"
          f" | tree dirty lines after={len(dirty)}")
    print("VERDICT", "ALL_FOUR_REAL" if all(verdicts) and not bad else "SOMETHING_NOT_REAL")
    return 0 if all(verdicts) and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
