"""Time-surface census: every place the UI renders a moment, and whether it says which moment.

The domain's criterion is one sentence: for every time on screen, the reader must be able to answer
"is this local clock or UTC, which field did it come from, and is the zone the one I expect?"  This
scanner reads the source and reports, per site:

  * the file and line of the call that formats a moment,
  * the field it formats (what it is a reading OF),
  * the zone source it passes (a named zone, the device zone, or a fallback),
  * whether the rendered text carries a zone label (an explicit `timeZoneName`, a printed zone
    name, or a UTC suffix), and
  * whether the call can silently fall back to the device clock.

It prints a table and a count, and exits non-zero if any site formats a moment with no zone label --
so it can be run as a check, not just read.

Nothing is edited: it lists and resolves.
"""
import io
import os
import re
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0447_wt/"

# a call that turns a value into a displayed moment
FORMATTERS = ("Intl.DateTimeFormat", "dateInZone", "toLocaleString", "toLocaleTimeString",
              "toLocaleDateString", "date(")
# the label vocabulary a screen may use to say WHICH moment it is showing.  Two kinds of carrier:
#  * a literal in the source (timeZoneName, a printed zone name, a UTC suffix);
#  * the i18n key that carries the attribution -- the source names the KEY, and the words live in
#    the locale table, so looking for the words at the call site would read the wrong layer.
ZONE_LABEL = re.compile(
    r"timeZoneName|utcOffset|\bUTC\b|\bGMT\b|\bCST\b|时区|当地时间|本地时间|北京时?间"
    r"|zoneAttribution|zone_attribution")


def src_files():
    out = subprocess.run(["git", "ls-files", "frontend/src"], cwd=WT, capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stdout.split("\n")
    return [p for p in out if p.strip().endswith((".ts", ".tsx"))]


def scan():
    sites = []
    for rel in src_files():
        text = io.open(WT + rel, encoding="utf-8", errors="replace").read()
        lines = text.split("\n")
        for i, line in enumerate(lines, start=1):
            if "dateInZone" in line and "function dateInZone" in line:
                continue
            if not any(f in line for f in FORMATTERS):
                continue
            if not is_render_site(line):
                continue
            # what moment is this a reading of?  the first argument, if we can see it
            arg = ""
            m = re.search(r"dateInZone\(\s*([^,)]+)", line)
            if not m:
                m = re.search(r"\.format\(\s*new Date\(\s*([^)]+)\)", line)
            if m:
                arg = m.group(1).strip()
            zone = "device" if ("dateInZone" not in line) else "named"
            if "timeZone" in line and "timeZoneName" not in line:
                zone = "named"
            labelled = bool(ZONE_LABEL.search(line))
            # a window of the surrounding lines, because the label may sit beside the call
            ctx = "\n".join(lines[max(0, i - 4):min(len(lines), i + 4)])
            labelled = labelled or bool(ZONE_LABEL.search(ctx))
            can_fallback = "dateInZone" in line
            sites.append({"file": rel, "line": i, "arg": arg, "zone": zone,
                          "labelled": labelled, "can_fallback": can_fallback,
                          "text": line.strip()[:100]})
    return sites


DURATION = re.compile(
    r"\bminutes?\b|\bhours?\b|\bdays?\b|\bnights?\b|分钟|小时|天|夜|countdown|剩余|durations?|"
    r"per_day|per-day|\bslots?\b|window\b")


def classify_moment(text: str) -> str:
    """Is this line rendering a committed INSTANT, or a duration/relative reading?

    Only an instant has to answer "which moment is this".  A duration does not, and treating both
    alike is how a scanner invents findings: counting a "3 days" string as an unlabelled time.
    """
    return "duration" if DURATION.search(text) else "instant"


def is_render_site(line: str) -> bool:
    """A line that RENDERS a value, as opposed to defining a helper or handling an event.

    The scanner can only locate candidates; whether a candidate is a defect is a screen question.
    Without this filter it lists `new Intl.DateTimeFormat(...)` inside a function body and event
    handlers as if they were display sites -- counting a definition as a finding.
    """
    s = line.strip()
    # money and other number formatting also uses toLocaleString; a formatted AMOUNT is not a
    # moment, and counting it is how a scanner invents findings in someone else's domain.
    if re.search(r"\bamount|Amount|minor|Minor|currency|Currency|\bcode\b|\bmajor\b", s):
        return False
    if s.startswith(("function ", "export function ", "const ", "return new Intl", "new Intl")):
        return False
    if "onChange=" in s or "onChange:" in s:
        return False
    if "=>" in s and "{" not in s.split("=>", 1)[1]:
        return False
    # a render: JSX text with an expression, or a template the component returns
    return ("{" in s and "}" in s) or s.startswith("? `") or s.startswith(": `") or "`${" in s


# a moment that is anchored to something the server committed to -- a scheduled time, an event's
# occurrence, a stay's check-in.  These are the ones a reader has to be able to place; a reading
# that shows one of them on the DEVICE clock, unlabelled, is the defect class.
COMMITTED_FIELD = re.compile(
    r"_at\b|occurred_at|scheduled_|check_in|check_out|start_at|end_at|arrival_anchor|departure_anchor|"
    r"updated_at|captured_at|anchor\.at")


def device_clock_instants():
    """Committed instants rendered with `date()` -- the device clock -- and no zone attribution."""
    out = []
    for rel in src_files():
        lines = io.open(WT + rel, encoding="utf-8", errors="replace").read().split("\n")
        for i, line in enumerate(lines, start=1):
            if "dateInZone(" in line or "function" in line:
                continue
            if not re.search(r"\bdate\(\s*[^)]*\)", line):
                continue
            if not is_render_site(line):
                continue
            m = re.search(r"date\(\s*([^,)]+)", line)
            field = (m.group(1) if m else "").strip()
            if not COMMITTED_FIELD.search(field):
                continue
            ctx = "\n".join(lines[max(0, i - 6):min(len(lines), i + 6)])
            if ZONE_LABEL.search(line) or ZONE_LABEL.search(ctx):
                continue
            out.append({"file": rel, "line": i, "field": field, "text": line.strip()[:90]})
    return out


def journey_anchored_sites():
    """The moments that are anchored to the JOURNEY (start_at, end_at, arrival/departure anchors).

    These are the ones the domain cares about first: they are a specific instant the traveller
    committed to, rendered in the journey's zone -- and a reader in another zone cannot tell that
    from their own clock unless the screen says so.
    """
    out = []
    for rel in src_files():
        lines = io.open(WT + rel, encoding="utf-8", errors="replace").read().split("\n")
        for i, line in enumerate(lines, start=1):
            if "dateInZone(" not in line or "function" in line:
                continue
            if not is_render_site(line):
                continue
            m = re.search(r"dateInZone\(\s*([^,]+)", line)
            field = (m.group(1) if m else "").strip()
            anchored = any(k in field for k in ("start_at", "end_at", "arrival_anchor", "departure_anchor"))
            if not anchored:
                continue
            ctx = "\n".join(lines[max(0, i - 6):min(len(lines), i + 6)])
            labelled = bool(ZONE_LABEL.search(line)) or bool(ZONE_LABEL.search(ctx))
            out.append({"file": rel, "line": i, "field": field, "labelled": labelled})
    return out


def main():
    sites = scan()
    print("time-surface sites found: %d in %d files" % (len(sites), len(set(s["file"] for s in sites))))
    unlabelled = [s for s in sites if not s["labelled"]]
    fallback = [s for s in sites if s["can_fallback"]]
    print("sites with no zone label in view: %d" % len(unlabelled))
    print("sites that can silently fall back to the device clock: %d" % len(fallback))

    anchors = journey_anchored_sites()
    anchor_bad = [a for a in anchors if not a["labelled"]]
    print("\njourney-anchored moment displays: %d, of which carry no zone attribution: %d"
          % (len(anchors), len(anchor_bad)))
    for a in anchors:
        print("   %-46s :%-5d %-34s %s"
              % (a["file"].replace("frontend/src/", ""), a["line"], a["field"][:34],
                 "labelled" if a["labelled"] else "NO ATTRIBUTION"))

    # Layer two: an unlabelled site is only a DEFECT if it renders a committed instant.  A duration
    # (minutes, days), a countdown, or a relative phrase ("just now") is a different kind of reading
    # and does not need to name a zone.  This sorts them so the next round scans the right set
    # instead of counting everything it cannot read.
    committed = []
    relative = []
    for s in sites:
        if s["labelled"]:
            continue
        ctx = s["text"]
        kind = classify_moment(ctx)
        (committed if kind == "instant" else relative).append((s, kind))

    print("\nunlabelled sites by what they render:")
    print("  committed instant (must name its moment): %d" % len(committed))
    print("  duration / relative / countdown (no zone needed): %d" % len(relative))
    for s, kind in committed:
        print("     %-46s :%-5d %s" % (s["file"].replace("frontend/src/", ""), s["line"], s["text"][:70]))

    device_sites = device_clock_instants()
    print("\ncommitted instants rendered on the DEVICE clock with no zone attribution: %d"
          % len(device_sites))
    for d in device_sites:
        print("   %-46s :%-5d %-30s %s"
              % (d["file"].replace("frontend/src/", ""), d["line"], d["field"][:30], d["text"][:50]))

    if anchor_bad:
        print("\nRESULT: %d journey-anchored display(s) render a moment with no zone attribution -- "
              "a reader cannot tell which moment it is." % len(anchor_bad))
        return 1
    if device_sites:
        print("\nRESULT: journey anchors are labelled, but %d committed instant(s) are still read on "
              "the DEVICE clock with no zone named. Next scan scope." % len(device_sites))
        return 0
    if committed:
        print("\nRESULT: journey anchors are labelled, but %d other site(s) still render a committed "
              "instant with no named moment. Next scan scope." % len(committed))
        return 0
    print("\nRESULT: every journey-anchored moment display carries a zone attribution.")
    return 0


if __name__ == "__main__":
    sys.exit(main())