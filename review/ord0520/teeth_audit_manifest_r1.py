"""Teeth audit: every guard this lane owns, judged by RUNNING it, plus whether its instrument uses it.

Two questions, and they are deliberately answered by different means, because one of them cannot be
answered by reading:

  1. does the guard bite?  -- answered by RUNNING it: an empty/partial input must be refused BY NAME and a
     complete input must be allowed. Reading the source cannot settle this; there is a gate in this very
     tree that a word-scan called mute while it had a `still_red` arm.
  2. does its own instrument actually call it?  -- answered by READING the call sites. A guard nobody calls
     is dead code: it can bite beautifully and still protect nothing.

A guard has teeth only when both are true. Rows where they are not are the work queue, and the reason is
stated per row rather than summarised. The scope is derived: instruments are the files carrying the guard
predicates, and every predicate each instrument defines is in scope whether or not it is called -- a dead
guard has to appear in the table, or the table would be the very thing it is auditing.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
INSTRUMENTS = ["abort_glass_provenance_r3.py", "osmt_flake_attribution_r3.py", "abort_http_probe_r3.py"]
PREDICATES = ("refuse_when_empty", "refuse_unless_all_present", "refuse_unless_states_present")

#: Per predicate, an input that must be REFUSED and one that must be ALLOWED. Kept explicit because the
#: right pair differs by predicate, and guessing it is how a probe measures the wrong thing. Items are
#: NAMES wherever the guard joins the missing ones into its message; the provenance guard takes records
#: instead, so that one's inputs are dicts and the message it builds there does not join anything.
PROBES = {
    "refuse_when_empty": {"empty": [], "filled": ["alpha", "beta"]},
    "refuse_unless_all_present": {"empty": ["a"], "filled": ["a", "b"]},
    "refuse_unless_states_present": {
        "empty": [{"state": "patched"}],
        "filled": [{"state": "patched"}, {"state": "tip_bytes"}],
    },
}
#: For the 3-argument form, (declared, recorded) per case.
TWO_COLLECTION = {"empty": (["a", "b", "c", "d"], []), "filled": (["a", "b", "c", "d"], ["a", "b", "c", "d"])}
#: The provenance guard of the same name takes four RECORD slots, not names, and reports only how many
#: are missing. Feeding it names would exercise a different code path than the one its caller uses, so
#: its two-collection probes are given here too.
PROVENANCE_SLOTS = {"empty": ({}, {}, {}, {}), "filled": ({"P1": 1}, {"P2": 1}, {"P3": 1}, {"P4": 1})}


def defines(path: pathlib.Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def call_sites(path: pathlib.Path) -> set:
    """Predicates this instrument CALLS (indented call, i.e. inside a function body)."""

    text = path.read_text(encoding="utf-8")
    return {p for p in PREDICATES if re.search(r"^\s{4,}%s\(" % re.escape(p), text, re.M)}


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(guard, case: str, value, what: str, instrument: str, predicate: str):
    """Call the guard the way ITS OWN signature and ITS OWN instrument want.

    Two guards share the name `refuse_unless_all_present` and they do not take the same thing: the HTTP
    probe's takes (declared_names, recorded_names) and the provenance one's takes four record slots. The
    input shape is therefore chosen per (instrument, predicate); a probe fed the wrong shape would be
    exercising a path the caller never takes and its verdict would mean nothing.
    """

    import inspect

    params = list(inspect.signature(guard).parameters)
    buffer = io.StringIO()
    code = None
    with contextlib.redirect_stdout(buffer):
        try:
            if instrument == "abort_glass_provenance_r3.py" and predicate == "refuse_unless_all_present":
                guard(list(PROVENANCE_SLOTS[case]), what)
            elif len(params) == 3:
                declared, recorded = TWO_COLLECTION[case]
                guard(declared, recorded, what)
            else:
                guard(value, what)
        except SystemExit as exc:
            code = exc.code
    return code, buffer.getvalue().strip()


def probe(guard, predicate: str, what: str, instrument: str) -> dict:
    spec = PROBES[predicate]
    empty_code, empty_said = _run(guard, "empty", spec["empty"], what, instrument, predicate)
    filled_code, filled_said = _run(guard, "filled", spec["filled"], what, instrument, predicate)
    return {
        "empty_refused": empty_code not in (0, None),
        "empty_exit_code": empty_code,
        "empty_names_what_it_refused": what in empty_said,
        "filled_allowed": filled_code in (0, None),
        "bites": (empty_code not in (0, None)) and what in empty_said and filled_code in (0, None),
    }


def main() -> int:
    rows = []
    for instrument in INSTRUMENTS:
        path = HERE / instrument
        if not path.exists():
            rows.append({"instrument": instrument, "status": "MISSING"})
            continue
        defined = defines(path)
        called = call_sites(path)
        module = load(path.stem)
        for predicate in sorted(defined & set(PREDICATES)):
            guard = getattr(module, predicate)
            what = "the audited collection"
            result = probe(guard, predicate, what, instrument)
            row = {"instrument": instrument, "predicate": predicate,
                   "called_by_its_own_instrument": predicate in called,
                   "bites_when_driven": result["bites"],
                   "empty_refused_by_name": result["empty_names_what_it_refused"],
                   "filled_allowed": result["filled_allowed"]}
            row["has_teeth"] = row["called_by_its_own_instrument"] and row["bites_when_driven"]
            row["why"] = (
                "called by its instrument and bites when driven" if row["has_teeth"]
                else ("dead code: nothing in its instrument calls it" if not row["called_by_its_own_instrument"]
                      else "called, but does not bite on the probe's empty input")
            )
            rows.append(row)

    # This file has to be able to fail, or its green is decoration.  Two temporary probes decide that:
    # a guard nothing calls must land in the work queue, and a guard that refuses everything must fail
    # the "bites" half (a guard that refused both inputs would otherwise look armed).
    dead = HERE / "zz_dead_guard_probe_tmp.py"
    deaf = HERE / "zz_deaf_guard_probe_tmp.py"
    dead_src = "\n".join([
        "def refuse_when_empty(collection, what):",
        "    return None",
        "",
        "",
        "def call_nothing():",
        "    return 0",
        "",
    ])
    deaf_src = "\n".join([
        "def refuse_when_empty(collection, what):",
        "    print('REFUSE: %s is empty' % what)",
        "    raise SystemExit(2)",
        "",
        "",
        "def caller():",
        "    refuse_when_empty([], 'x')",
        "",
    ])
    dead.write_text(dead_src, encoding="utf-8", newline="\n")
    deaf.write_text(deaf_src, encoding="utf-8", newline="\n")
    try:
        # A guard that nothing calls: the "called" half must read False even though it can be driven.
        dead_module = load(dead.stem)
        dead_driven = probe(dead_module.refuse_when_empty, "refuse_when_empty", "x", dead.name)["bites"]
        dead_called = bool(re.search(r"^\s{4,}refuse_when_empty\(", dead_src, re.M))
        dead_row = {"called_by_its_own_instrument": dead_called, "bites_when_driven": dead_driven}
        dead_row["has_teeth"] = dead_called and dead_driven
        # A guard that refuses everything: "bites" must be False, because the filled input is refused too.
        deaf_module = load(deaf.stem)
        deaf_result = probe(deaf_module.refuse_when_empty, "refuse_when_empty", "x", deaf.name)
    finally:
        for probe_file in (dead, deaf):
            probe_file.unlink(missing_ok=True)
    control_dead_caught = dead_row["has_teeth"] is False
    control_deaf_caught = deaf_result["bites"] is False
    print("control_dead_guard_lands_in_queue %s" % control_dead_caught)
    print("control_refuses_everything_is_not_teeth %s" % control_deaf_caught)

    queue = [r for r in rows if not r.get("has_teeth")]
    report = {
        "method": "bites: RUN the guard (empty must be refused BY NAME, filled must be allowed). "
                  "called: READ the instrument's call sites. Scope: every predicate each instrument defines.",
        "rows": rows,
        "total": len(rows),
        "with_teeth": sum(1 for r in rows if r.get("has_teeth")),
        "work_queue": [{"instrument": r["instrument"], "predicate": r["predicate"], "why": r["why"]}
                       for r in queue],
        "controls_passed": bool(control_dead_caught and control_deaf_caught),
        "verdict": ("EVERY_GUARD_HAS_TEETH" if (not queue and control_dead_caught and control_deaf_caught)
                    else ("CONTROL_FAILED" if not (control_dead_caught and control_deaf_caught)
                          else "WORK_QUEUE_NOT_EMPTY")),
    }
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))
    for r in rows:
        print("%-32s %-28s called=%-5s bites=%-5s %s"
              % (r["instrument"], r["predicate"], r["called_by_its_own_instrument"],
                 r["bites_when_driven"], r["why"]))
    print("VERDICT %s" % report["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())