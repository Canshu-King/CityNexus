"""Prove the two re-anchor guards bite, on scratch copies only -- wt22 is not touched.

S1 drops a backtick from one replacement string: the exact bug the shipped r8 comment would have
gotten away with (it turned "shared `require()`" into "shared require()`"), so `apply` must refuse it.
S2 rewords the shipped prose so no phrase anchor matches: `apply` must report ABORT_ANCHOR_PHRASE
rather than silently replacing nothing and calling the comment re-anchored.
S3 is the positive control: applying for real moves the digits and leaves the prose alone.

S1/S2 splice a new REPL entry by splitlines index rather than by re-typing the whole `apply`, so the
prose of this driver never becomes a competing copy of the tool.  The exec of a tool source region
reads the tool's own file and is why this driver needs no duplicated anchor logic.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reanchor_r8 as R

SRC = open(os.path.join(R.WT, R.TEST), encoding="utf-8", newline="").read()
MAIN_LINES = open(os.path.join(R.WT, R.MAIN), encoding="utf-8").read().splitlines()


def scratch(**repl_over):
    """Re-exec the tool's support region with REPL entries replaced by the given source text."""
    lines = list(R.REPL_SRC_LINES)
    for label, source_line in repl_over.items():
        needle = '"%s": ' % label
        for i, l in enumerate(lines):
            if needle in l and "PATTERNS" not in l:
                lines[i] = source_line
                break
        else:
            raise SystemExit("ABORT_SELFTEST_LAYOUT cannot find the %r entry in %s to splice it -- "
                             "the guard would not have been tested" % (label, R.__file__))
    code = "\n".join(lines)
    try:
        compile(code, "<scratch>", "exec")
    except SyntaxError as exc:
        raise SystemExit("ABORT_SELFTEST_TRUNCATED the spliced support region does not compile (%s) "
                         "-- the guard was never reached" % exc)
    ns = {"__name__": "reanchor_r8_scratch", "__file__": R.__file__}
    exec(code, ns)
    return ns


def main():
    anchors, span = R.read_anchors(MAIN_LINES)
    out = {"tool": "reanchor_r8_selftest", "anchors_from_tip": anchors, "route_span": list(span),
           "main_lines": len(MAIN_LINES)}

    # S1 -- a replacement that changes the prose, not just the digits.  The spliced line is SOURCE
    # text, so it names the tool's own `Q` variable instead of holding a backtick character.
    bad = scratch(**{"require": '    "require": Q + " helper (" + Q + "backend/app/main.py:%d" + Q + ")",'})
    try:
        bad["apply"](SRC, anchors)
        out["s1_prose_mutation"] = {"verdict": "FAIL_GUARD_BLIND",
                                    "note": "apply() accepted a replacement that dropped a backtick"}
    except SystemExit as exc:
        t = str(exc.args[0]) if exc.args else ""
        out["s1_prose_mutation"] = {"verdict": "PASS" if t.startswith("ABORT_TEXT_CHANGED") else "FAIL",
                                    "abort_head": t[:64]}

    # S2 -- the phrase the tool anchors on is gone: refusing must be said out loud.
    ns = scratch()
    m0 = re.search(ns["PATTERNS"][0][1], SRC)
    if not m0:
        raise SystemExit("ABORT_SELFTEST_STARTING_SHAPE the shipped require() citation is not the "
                         "shape this driver expects")
    shipped_citation = ns["REPL"]["require"] % int(m0.group(1))
    reworded = SRC.replace(shipped_citation, "shared require helper (see main.py)", 1)
    if reworded == SRC:
        out["s2_reworded_control"] = {"verdict": "FAIL_NO_STARTING_SHAPE",
                                      "note": "the shipped text does not contain %r" % shipped_citation}
    elif re.search(ns["PATTERNS"][0][1], reworded):
        out["s2_reworded_control"] = {"verdict": "FAIL_INSTRUMENT",
                                      "note": "the rewording left the anchor phrase intact, so S2 "
                                              "tested nothing"}
    else:
        try:
            ns["apply"](reworded, anchors)
            out["s2_reworded_control"] = {"verdict": "FAIL_GUARD_BLIND",
                                          "note": "apply() found nothing to replace and stayed silent"}
        except SystemExit as exc:
            t = str(exc.args[0]) if exc.args else ""
            out["s2_reworded_control"] = {"verdict": "PASS" if t.startswith("ABORT_ANCHOR_PHRASE") else "FAIL",
                                          "abort_head": t[:64],
                                          "citation_removed": shipped_citation}

    # S3 -- positive control: the digits move, the prose does not.
    def mask(s):
        return re.sub(r"\d", "#", s)

    new, replaced, n = ns["apply"](SRC, anchors)
    changed = sum(1 for a, b in zip(SRC.splitlines(), new.splitlines()) if a != b)
    out["s3_real_application"] = {
        "verdict": ("PASS" if n == 4 and len(replaced) == 4 and mask(new) == mask(SRC) else "FAIL"),
        "replacements": n, "numbers_from": replaced,
        "numbers_to": {k: anchors[k] for k in replaced},
        "stale_count": sum(1 for k, v in replaced.items() if v != anchors[k]),
        "prose_identical_when_every_digit_masked": mask(new) == mask(SRC),
        "bytes_before": len(SRC.encode("utf-8")), "bytes_after": len(new.encode("utf-8")),
        "lines_changed": changed,
    }

    ARMS = ("s1_prose_mutation", "s2_reworded_control", "s3_real_application")
    out["arms"] = list(ARMS)
    out["every_arm"] = [out[k]["verdict"] for k in ARMS]
    out["green"] = all(v == "PASS" for v in out["every_arm"])

    path = os.path.join(R.LANE, "evidence", "reanchor_r8_selftest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if out["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
