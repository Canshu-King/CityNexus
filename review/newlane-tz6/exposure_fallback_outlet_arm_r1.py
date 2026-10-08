"""Counter-arm for the exception-to-DOM fallback outlet.

The order (号令者派单 · 曝光面收窄三件, item three, backend lane): "把异常到 DOM 这条通道的兜底形状
定成一处可复用出口，别逐屏手抄."  What this pins is therefore not one screen's copy but the *shape*:
the sentence a screen may say when a step failed and no usable answer arrived must have ONE home, and
a screen must ask it rather than write its own.

Two halves, both read off the real tree:

  * structural -- the unreachable-server literal appears in exactly one file, and every screen that
    used to hand-copy it now asks the outlet;
  * behavioural -- the outlet is transpiled from its real source together with its real dependencies
    and actually called, so the assertions describe what it returns rather than what it is written.
    This is the part a pure text check cannot do: it proves the outlet tells "the server answered
    with something unusable" apart from "the server never answered", which is the distinction the
    hand-copies erased.

On the tip's bytes the structural half bites (four files write the literal, none ask an outlet) and
the behavioural half cannot even load the module.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "frontend", "src")
OUTLET_REL = "lib/refusalFallback.ts"
OUTLET = os.path.join(SRC, "lib", "refusalFallback.ts")
NODE_MODULES = os.path.join(REPO, "frontend", "node_modules")
TSC = os.path.join(NODE_MODULES, "typescript", "bin", "tsc")

# The literal every screen used to copy by hand.
LITERAL = "Could not reach the server. Try again."
# The screens that hand-copied it on the tip (the order's "逐屏手抄").
FORMER_COPIERS = [
    os.path.join("app", "V8Experience.tsx"),
    os.path.join("features", "execution", "LiveRecovery.tsx"),
    os.path.join("features", "planning", "PlanComparison.tsx"),
    os.path.join("features", "stay", "HotelsPanel.tsx"),
]


def walk():
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in {"node_modules", "__tests__"}]
        for name in files:
            if name.endswith((".ts", ".tsx")):
                yield os.path.join(root, name)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def structural() -> tuple[list[str], int]:
    bad: list[str] = []
    checks = 0

    writers = [p for p in walk() if LITERAL in read(p)]
    rel_writers = sorted(os.path.relpath(p, SRC).replace("\\", "/") for p in writers)
    checks += 1
    if rel_writers != [OUTLET_REL]:
        bad.append(
            "the fallback sentence is written in %d file(s) (%s); it must have one home, %s"
            % (len(rel_writers), ", ".join(rel_writers) or "none", OUTLET_REL)
        )

    for rel in FORMER_COPIERS:
        path = os.path.join(SRC, *rel.split(os.sep))
        checks += 1
        if not os.path.isfile(path):
            bad.append("%s is missing" % rel)
            continue
        text = read(path)
        if LITERAL in text:
            bad.append("%s still hand-copies the fallback sentence" % rel)
        if "refusalFallback" not in text:
            bad.append("%s does not ask the outlet" % rel)

    checks += 1
    if not os.path.isfile(OUTLET):
        bad.append("there is no outlet at %s" % OUTLET_REL)
    return bad, checks


def transpile_outlet(work: str) -> tuple[bool, str]:
    # Wipe the output dir first.  Leaving a previous run's JS in place makes the behavioural half
    # read a stale outlet and report green on bytes that have none -- a false green measured on
    # this arm's own tip-byte run (structural bit, behavioural silently passed from the cache).
    if os.path.isdir(work):
        for name in os.listdir(work):
            target = os.path.join(work, name)
            (os.remove if os.path.isfile(target) else os.rmdir)(target)
    os.makedirs(work, exist_ok=True)
    source = os.path.join(SRC, "lib", "refusalFallback.ts")
    if not os.path.isfile(source):
        return False, "no outlet source at %s" % source
    cmd = [
        "node", TSC,
        source,
        "--outDir", work, "--module", "commonjs", "--target", "es2020",
        "--esModuleInterop", "--skipLibCheck",
    ]
    proc = subprocess.run(cmd, cwd=os.path.join(REPO, "frontend"), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=600)
    ok = os.path.isfile(os.path.join(work, "refusalFallback.js"))
    return ok, (proc.stdout or "") + (proc.stderr or "")


RUNNER = r"""
const path = require("path");
const m = require(path.join(process.argv[2], "refusalFallback.js"));
const { isOriginResponseUnusable } = require(path.join(process.argv[2], "failureAttribution.js"));
const { OriginResponseUnusableError } = require(path.join(process.argv[2], "failureAttribution.js"));
const { ReadDeadlineMissed } = require(path.join(process.argv[2], "readDeadline.js"));

const out = [];
function record(label, value) { out.push({ label: label, value: value }); }

// No answer at all: a TypeError from fetch, and this device's own read deadline.
record("typeerror_en", m.deviceKnownRefusalSentence(new TypeError("fetch failed"), false));
record("typeerror_zh", m.deviceKnownRefusalSentence(new TypeError("fetch failed"), true));
record("deadline_en", m.deviceKnownRefusalSentence(new ReadDeadlineMissed(1500), false));

// An answer that came back but is not usable data: a DIFFERENT fact, and it must not read as
// "could not reach the server".
const unusable = new OriginResponseUnusableError(503, "text/html", "html");
record("unusable_en", m.deviceKnownRefusalSentence(unusable, false));
record("unusable_zh", m.deviceKnownRefusalSentence(unusable, true));

// A failure this outlet knows nothing about: null, so the caller keeps its own fallback.
record("unknown", m.deviceKnownRefusalSentence(new Error("something else"), false));

// The outlet must not be a constant: an unknown answer and no answer cannot say the same thing.
record("distinct", m.deviceKnownRefusalSentence(unusable, false) !== m.unreachableServerSentence(false));
record("unusable_names_status", /503/.test(m.deviceKnownRefusalSentence(unusable, false) || ""));
record("unusable_names_content_type", /text\/html/.test(m.deviceKnownRefusalSentence(unusable, false) || ""));
record("noanswer_says_no_status", !/HTTP \d/.test(m.unreachableServerSentence(false)));

process.stdout.write(JSON.stringify(out));
"""


def behavioural(work: str) -> tuple[list[str], dict, int]:
    ok, log = transpile_outlet(work)
    if not ok:
        return ["the outlet could not be transpiled from its real source: %s" % log.strip()[:300]], {}, 0
    runner = os.path.join(work, "_runner.cjs")
    with open(runner, "w", encoding="utf-8") as handle:
        handle.write(RUNNER)
    proc = subprocess.run(["node", runner, work], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)
    if proc.returncode != 0:
        return ["calling the outlet failed: %s" % (proc.stderr or proc.stdout).strip()[:300]], {}, 0
    rows = {r["label"]: r["value"] for r in json.loads(proc.stdout)}

    # One entry per assertion the outlet is held to; the count is this table's length, not a literal.
    ASSERTIONS = (
        ("typeerror_en", lambda v: v == LITERAL,
         "a fetch TypeError does not get the unreachable sentence"),
        ("typeerror_zh", lambda v: bool(v),
         "the zh arm of the unreachable verdict is empty"),
        ("deadline_en", lambda v: v == LITERAL,
         "a missed read deadline is not the unreachable verdict"),
        ("unusable_en", lambda v: bool(v) and v != LITERAL,
         "an unusable answer is reported as 'could not reach the server' -- the two facts the "
         "hand-copies erased are still erased"),
        ("unknown", lambda v: v is None,
         "the outlet guesses at a failure it cannot know"),
        ("distinct", lambda v: bool(v),
         "the outlet returns the same sentence whether or not the server answered"),
        ("unusable_names_status", lambda v: bool(v),
         "the unusable verdict does not name the HTTP status this device read"),
        ("unusable_names_content_type", lambda v: bool(v),
         "the unusable verdict does not name the content type this device read"),
        ("noanswer_says_no_status", lambda v: bool(v),
         "the no-answer verdict names an HTTP status, which it cannot have observed"),
    )
    bad: list[str] = []
    for label, holds, why in ASSERTIONS:
        if not holds(rows.get(label)):
            bad.append("%s: %s (read %r)" % (label, why, rows.get(label)))
    return bad, rows, len(ASSERTIONS)


def main() -> int:
    work = os.path.join(os.environ.get("TEMP", "/tmp"), "tz6_outlet_arm")
    bad, struct_checks = structural()
    beh_bad, rows, beh_checks = behavioural(work)
    bad += beh_bad

    print("exposure fallback outlet: %d structural + %d behavioural checks, %d bad"
          % (struct_checks, beh_checks, len(bad)))
    for label in ("typeerror_en", "deadline_en", "unusable_en", "unknown"):
        print("   %-18s -> %s" % (label, json.dumps(rows.get(label), ensure_ascii=False)))
    for flag in ("distinct", "unusable_names_status", "unusable_names_content_type",
                 "noanswer_says_no_status"):
        print("   %-26s -> %s" % (flag, rows.get(flag)))
    if bad:
        print("\nARM BITES -- the exception-to-DOM fallback is not one outlet:")
        for item in bad:
            print("   " + item)
        return 1
    print("\nARM_QUIET: one home for the fallback shape, and it answers the two facts apart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
