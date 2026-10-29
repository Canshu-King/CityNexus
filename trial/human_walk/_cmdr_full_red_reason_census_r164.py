"""Turn a whole-suite --tb=line run into a cause table instead of a pile of red lines.

Reads the suite output file, groups every stack-tail record by (file, line, reason), normalises the
reason so that parameterised wording does not split a group, and refuses to report a table whose
rows do not add up to the number in pytest's own summary line.  It also names how many groups are
already explained by the two families found this shift, and keeps every other group visible rather
than lumping it into 'unknown'.
"""

import io
import json
import os
import re
import sys

SUITE_OUT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bw163-backend-full-tbline.txt"
RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bw163-red-census.txt"

TAIL = re.compile(r"^(?P<path>.*?):(?P<line>\d+): (?P<reason>.*)$", re.M)
SUMMARY = re.compile(r"^(\d+) failed, (\d+) passed.*?(\d+) errors?", re.M)
BEARER_KEYS = ("KeyError: 'active_plan'", "authenticated traveler credentials are required")
FAKE_SETTINGS = "SimpleNamespace"


def normalise(reason):
    """Collapse whitespace but keep the message body.

    An earlier version cut at the first brace, which is exactly where a JSON error body starts, so
    every 'AssertionError: {\"error\": ...}' group printed an empty reason and fell into 'not yet
    attributed'.  The body is the finding, so it stays.
    """
    return " ".join(reason.split())[:160]


def logical_lines(text):
    """Fold pytest's --tb=line continuation lines back onto the tail they belong to.

    With --tb=line an assertion that prints a multi-line message shows only its first line, so an
    unfixed parser records 'AssertionError:' and calls the red unexplained.  Indented followers are
    part of the same failure, so they are joined before matching.
    """
    joined = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and joined:
            joined[-1] += " " + raw.strip()
        else:
            joined.append(raw)
    return "\n".join(joined)


UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
TRACE = re.compile(r"CNX-[A-Z0-9]{8}")


def signature(reason):
    """Group by the message shape, not by the identifiers inside it.

    Keeping the JSON body was necessary to classify at all, but a body that carries a plan version id
    makes every failure its own group, which hides the size of the cause.  Identifiers are masked so
    twelve copies of one refusal count as twelve.
    """
    text = normalise(reason)
    text = UUID.sub("<id>", text)
    text = TRACE.sub("<receipt>", text)
    return re.sub(r"\b[0-9a-f]{16,}\b", "<id>", text)


def classify(reason, outside_tree):
    """Name the shape the tail actually shows, and keep unproven links out of the label."""
    if "KeyError: 'active_plan'" in reason or "authenticated traveler credentials" in reason:
        return "bearer-less private read (measured this shift)"
    if "traveler credentials are invalid" in reason:
        return "credential refused (measured this shift)"
    if "401 == 200" in reason or "assert 401" in reason:
        return "door answers 401 where the test expects 200"
    if "'str' object has no attribute 'get'" in reason:
        return "body iterated as a list (the measured 401 shape)"
    if FAKE_SETTINGS in reason:
        return "fake settings missing a field"
    if "12-field contract" in reason:
        return "stale field-list contract"
    if "end_at > start_at" in reason or "RENDEZVOUS_TIME_PASSED" in reason or "'PAST'" in reason:
        return "seeded clock expired"
    if "'Depends' object has no attribute" in reason:
        return "route function called with dependencies unbound"
    if "DEMO_START_REFUSED" in reason:
        return "demo journey cannot start without a selected plan"
    if "demo/scene 实际 503" in reason or "scene 里没有 journey_id" in reason:
        return "demo scene setup refused"
    if "is not authoritative" in reason:
        return "plan version refused as not authoritative"
    if "V13_COMMITMENT_ANCHOR" in reason or "V13_C4_ANCHOR" in reason:
        return "commitment anchor rejected by the v13 planner"
    if "REQUIRE_CONFIRMATION" in reason and "ALLOW_AUTO" in reason:
        return "autonomy decided differently than the test expects"
    if "'_IncludedRouter' object has no attribute" in reason:
        return "test reads a router shape that changed"
    if "CAPTURED_REPLAY_CITY_MISMATCH" in reason:
        return "replay city does not match"
    if "demo scene setup refused" in reason:
        return "demo scene setup refused"
    if outside_tree:
        return "crash lands in library code, not repo code"
    return "not yet attributed"


def repo_relative(path):
    """Name the file the way the repo does, and mark the frames that are not repo code at all."""
    forward = path.replace("\\", "/")
    if "_cmdr_rescue_v3_1022/" in forward:
        tail = forward.split("_cmdr_rescue_v3_1022/", 1)[1]
        if tail.startswith("backend/"):
            return tail[len("backend/"):], False
        return tail, False
    return forward, True


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not os.path.exists(SUITE_OUT):
        print("ABORT no suite output yet at %s" % SUITE_OUT)
        return 3
    raw_text = io.open(SUITE_OUT, encoding="utf-8", errors="replace").read()
    text = logical_lines(raw_text)
    summary = SUMMARY.findall(text)
    if not summary:
        print("ABORT the run has no summary line yet; nothing to census")
        return 4
    failed, passed, errors = (int(item) for item in summary[-1])
    groups = {}
    for match in TAIL.finditer(text):
        file_name, outside_tree = repo_relative(match.group("path"))
        reason = match.group("reason")
        key = (file_name, int(match.group("line")), signature(reason), outside_tree)
        groups[key] = groups.get(key, 0) + 1
    total_records = sum(groups.values())
    if total_records != failed:
        print(
            "ABORT stack-tail records %d do not equal pytest's own %d failed -- the ruler would be"
            " inventing a table" % (total_records, failed)
        )
        return 5
    by_class = {}
    for (_file, _line, reason, outside_tree), count in groups.items():
        name = classify(reason, outside_tree)
        by_class[name] = by_class.get(name, 0) + count
    lines = [
        "WHOLE-SUITE RED CENSUS r164",
        "SOURCE %s" % os.path.basename(SUITE_OUT),
        "SUMMARY failed=%d passed=%d errors=%d" % (failed, passed, errors),
        "STACK_TAIL_RECORDS %d (must equal failed, enforced above)" % total_records,
        "OUTSIDE_REPO_FRAMES %d" % sum(c for (_f, _l, _r, o), c in groups.items() if o),
        "DISTINCT_TAIL_GROUPS %d" % len(groups),
        "RED BY CAUSE %s" % json.dumps(by_class, sort_keys=True, ensure_ascii=False),
        "TOP GROUPS",
    ]
    for (file_name, line_no, reason, outside_tree), count in sorted(
        groups.items(), key=lambda item: (-item[1], item[0])
    )[:25]:
        marker = "%s:%d" % (file_name, line_no) if not outside_tree else "(library) %s:%d" % (file_name, line_no)
        lines.append(
            "  %3d x %s [%s] %s" % (count, marker, classify(reason, outside_tree), normalise(reason))
        )
    lines.append("TOP NOT-ATTRIBUTED GROUPS")
    unattributed = [
        (key, count) for key, count in groups.items() if classify(key[2], key[3]) == "not yet attributed"
    ]
    for (file_name, line_no, reason, _outside), count in sorted(unattributed, key=lambda item: (-item[1], item[0]))[:10]:
        lines.append("  %3d x %s:%d %s" % (count, file_name, line_no, normalise(reason)))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
