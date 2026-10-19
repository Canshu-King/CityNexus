"""The copy campaign's floor, wired as an arm that fails on growth.

Three measurements are what "the UI is simpler now" was decided from all morning:

  * copy that points at the screen's own layout ("the roster below", "pick a trip above");
  * copy that defends or describes the product instead of answering ("we would never invent ...");
  * copy keys no product file reads, so a sentence can be edited forever and change nothing.

Each has a ruler that computes it (`defensive_copy_scan_r1.py`, `copy_orphan_keys_r1.py`) and every one
of them came down today -- but a number that goes down can go up again the moment the next sentence is
written, and nothing in the tree noticed. This file is the noticing: the three sets are compared with a
committed baseline, any NEW member is a refusal, and a set that has shrunk is reported and blessed by a
separate call, so lowering the floor is a visible act rather than an accident.

It is a no-growth arm, not a ban: today's survivors are in the baseline on purpose (each has a stated
reason, listed in `copy_restraint_baseline_r1.json`), and a lane adding a sentence that trips a marker is
asked to reword it, not punished for existing. Read the two rulers' own selftests for why their
vocabularies are what they are; this file adds no vocabulary of its own, which is the point.

Why the verdict is a function and not three `print` calls in `main()`: this file's whole value is its
exit codes, and an exit code you cannot reach from a selftest is an exit code that can rot. The first
mutation run over this file "caught" four mutants for the wrong reason -- the copies sat outside the
tools folder, could not `load` their two rulers, and died with a traceback that read like a refusal.
Underneath that noise, a gate that never refused anything passed its own selftest. `decide()` is what
that selftest can now bite.

Usage:
    python tools/copy_restraint_gate_r1.py              # compare with the baseline, 0 or 1
    python tools/copy_restraint_gate_r1.py --bless      # rewrite the baseline from the tree
    python tools/copy_restraint_gate_r1.py --json       # machine-readable counts
    python tools/copy_restraint_gate_r1.py --selftest   # controls over the comparison and the verdict
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRONTEND = HERE.parent
BASELINE = HERE / "copy_restraint_baseline_r1.json"
SETS = ("pointers", "defensive", "orphans")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current() -> dict[str, list[str]]:
    """The three sets, as sorted `origin|side|key` tokens -- a sentence's text is not stored anywhere."""

    scan = load("defensive_copy_scan_r1.py")
    orphans = load("copy_orphan_keys_r1.py")
    pointers = sorted({f"{origin}|{side}|{key}" for origin, side, key, _ in scan.layout_pointers()})
    defensive = sorted({f"{origin}|{side}|{key}" for origin, side, key, _, _ in scan.candidates()})
    dead = sorted(f"orphans|-|{key}" for key in orphans.inventory()["dead"])
    return {"pointers": pointers, "defensive": defensive, "orphans": dead}


def compare(now: dict[str, list[str]], base: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    """Growth and shrink per set, as membership differences -- never as counts of counts."""

    out: dict[str, dict[str, list[str]]] = {}
    for name in base:
        now_set, base_set = set(now.get(name, [])), set(base.get(name, []))
        out[name] = {"grew": sorted(now_set - base_set), "gone": sorted(base_set - now_set)}
    return out


def summarize(now: dict[str, list[str]], base: dict[str, list[str]], verdict: dict) -> list[str]:
    lines: list[str] = []
    for name in sorted(base):
        grew, gone = verdict[name]["grew"], verdict[name]["gone"]
        lines.append("%-10s baseline %d -> now %d | grew %d | gone %d" % (
            name, len(base[name]), len(now[name]), len(grew), len(gone)))
        for item in grew[:10]:
            lines.append("    NEW: " + item)
        if len(grew) > 10:
            lines.append("    ... {} more".format(len(grew) - 10))
        for item in gone[:10]:
            lines.append("    gone: " + item)
        if len(gone) > 10:
            lines.append("    ... {} more gone".format(len(gone) - 10))
    return lines


def decide(now: dict[str, list[str]], base: dict[str, list[str]], *, has_baseline: bool, bless: bool,
           baseline_name: str = "") -> tuple[int, list[str]]:
    """The whole verdict as one pure function: (exit code, lines to print).

    rc 4 -- no floor recorded yet, so there is nothing to grow above (recording one is deliberate work).
    rc 5 -- a set came back empty: a broken read, which would otherwise look like the cleanest UI ever.
    rc 1 -- membership grew: a new pointer, a new defensive sentence, or a key nobody reads.
    rc 0 -- at the floor, or below it (a shrink is reported and needs `--bless` to become the new floor).
    """

    name = baseline_name or BASELINE.name
    if not has_baseline and not bless:
        return 4, ["REFUSE (rc 4): no baseline at %s -- run --bless once, on purpose." % name]
    empty = sorted(set_name for set_name, items in now.items() if not items)
    if empty:
        return 5, ["REFUSE (rc 5): these sets came back empty, which is a broken read, not a clean UI: "
                   + ", ".join(empty)]
    verdict = compare(now, base)
    lines = summarize(now, base, verdict)
    total_grew = sum(len(v["grew"]) for v in verdict.values())
    if total_grew and not bless:
        return 1, lines + [
            "REFUSE (rc 1): {} new sentences or keys above the floor. Reword them, or name the reason in"
            " the baseline with --bless and a reviewer.".format(total_grew)]
    if any(v["gone"] for v in verdict.values()):
        lines.append("SIMPLER than the baseline; run --bless to move the floor down so the next reader"
                     " starts here.")
    lines.append("AT FLOOR: no growth in pointers, defensive copy, or unread keys.")
    return 0, lines


def selftest() -> int:
    base = {
        "pointers": ["a|zh|x.below", "a|zh|x.upper"],
        "defensive": ["b|en|y.screen", "b|zh|y.invent", "dictionary|zh|z.blame"],
        "orphans": ["orphans|-|close"],
    }

    results: list[tuple[str, bool, str]] = []
    same = compare({k: list(v) for k, v in base.items()}, base)
    results.append(("an unchanged tree passes", all(not d["grew"] for d in same.values()), str(same)[:60]))

    grown = {k: list(v) + ["c|en|new.pointer"] for k, v in base.items()}
    verdict = compare(grown, base)
    results.append(("one new member in every set is named and refused",
                    all(verdict[k]["grew"] == ["c|en|new.pointer"] for k in verdict), str(verdict)[:80]))

    shrunk = {"pointers": ["a|zh|x.below"], "defensive": base["defensive"], "orphans": []}
    verdict = compare(shrunk, base)
    results.append(("a set that got smaller is a shrink, not a failure",
                    not verdict["pointers"]["grew"] and verdict["pointers"]["gone"] == ["a|zh|x.upper"]
                    and verdict["orphans"]["gone"] == ["orphans|-|close"], str(verdict["pointers"])[:70]))

    renamed = compare({"pointers": ["a|zh|x.under"], "defensive": base["defensive"], "orphans": base["orphans"]}, base)
    results.append(("renaming a key is growth, not a wash -- the sentence still points",
                    renamed["pointers"]["grew"] == ["a|zh|x.under"]
                    and renamed["pointers"]["gone"] == ["a|zh|x.below", "a|zh|x.upper"],
                    str(renamed["pointers"])[:80]))

    empty = compare({"pointers": [], "defensive": [], "orphans": []}, base)
    results.append(("an empty read is reported as gone-everything, so the caller can refuse it",
                    all(len(empty[k]["gone"]) == len(base[k]) for k in base), str({k: len(empty[k]["gone"]) for k in empty})))

    # The verdict itself, reachable without a tree: every exit code this file promises has to have a
    # control that turns red when the promise is broken. That is what the four mutants are aimed at.
    floor = {"pointers": ["a|zh|x.below"], "defensive": ["b|en|y.screen"], "orphans": ["orphans|-|close"]}
    rc, lines = decide(floor, floor, has_baseline=True, bless=False)
    results.append(("decide: an unchanged tree exits 0 and says AT FLOOR",
                    rc == 0 and any("AT FLOOR" in line for line in lines), "rc %d" % rc))
    over = {"pointers": ["a|zh|x.below", "c|en|new"], "defensive": floor["defensive"], "orphans": floor["orphans"]}
    rc, lines = decide(over, floor, has_baseline=True, bless=False)
    results.append(("decide: one new member exits 1 and names it",
                    rc == 1 and any("NEW: c|en|new" in line for line in lines), "rc %d" % rc))
    rc, _ = decide(over, floor, has_baseline=True, bless=True)
    results.append(("decide: --bless is the only way a grown set exits 0 (it writes the floor, not this call)",
                    rc == 0, "rc %d" % rc))
    rc, lines = decide({k: [] for k in floor}, floor, has_baseline=True, bless=False)
    results.append(("decide: an empty read exits 5, never 0",
                    rc == 5 and any("empty" in line for line in lines), "rc %d" % rc))
    rc, lines = decide(floor, floor, has_baseline=False, bless=False)
    results.append(("decide: a missing baseline exits 4 and says so",
                    rc == 4 and any("no baseline" in line for line in lines), "rc %d" % rc))

    now = current()
    floors = {"pointers": 1, "defensive": 5, "orphans": 5}
    results.append(("the tree reads non-zero in all three sets (a silent zero is not a pass)",
                    all(len(now[k]) >= floors[k] for k in floors),
                    " ".join("%s=%d" % (k, len(now[k])) for k in sorted(now))))
    blessed = {k: sorted(v) for k, v in now.items()}
    results.append(("the baseline on disk matches the tree today (no drift since it was blessed)",
                    BASELINE.exists() and json.loads(BASELINE.read_text(encoding="utf-8"))["sets"] == blessed,
                    "baseline " + ("present" if BASELINE.exists() else "MISSING")))

    failed = [name for name, ok, _ in results if not ok]
    for name, ok, detail in results:
        print("%s | %s | %s" % ("PASS" if ok else "FAIL", name, detail))
    print("controls: {} | failed: {}".format(len(results), len(failed)))
    if failed:
        print("SELFTEST RED (rc 3): " + "; ".join(failed))
        return 3
    print("SELFTEST GREEN: growth is refused, shrink is reported, and a zero is not a pass.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    baseline = BASELINE
    if "--baseline" in sys.argv:
        # A caller (or a test of this file) may compare against another floor; the default never moves.
        baseline = Path(sys.argv[sys.argv.index("--baseline") + 1])
    bless = "--bless" in sys.argv
    stored = (json.loads(baseline.read_text(encoding="utf-8")) if baseline.exists()
              else {"sets": {name: [] for name in SETS}})
    now = current()
    code, lines = decide(now, stored["sets"], has_baseline=baseline.exists(), bless=bless,
                         baseline_name=baseline.name)
    for line in lines:
        print(line)
    if "--json" in sys.argv:
        print(json.dumps({"counts": {k: len(v) for k, v in now.items()},
                          "verdict": compare(now, stored["sets"])}, ensure_ascii=False))
    if code:
        return code
    if bless:
        payload = {"sets": {k: sorted(v) for k, v in now.items()},
                   "counts": {k: len(v) for k, v in now.items()},
                   "blessed_by": "copy_restraint_gate_r1.py --bless"}
        baseline.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
        again = json.loads(baseline.read_text(encoding="utf-8"))
        if again["sets"] != {k: sorted(v) for k, v in now.items()}:
            print("REFUSE: the baseline just written does not read back the same -- not blessing.")
            return 6
        print("blessed:", json.dumps(again["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
