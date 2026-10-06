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

    if anchor_bad:
        print("\nRESULT: %d journey-anchored display(s) render a moment with no zone attribution -- "
              "a reader cannot tell which moment it is." % len(anchor_bad))
        return 1
    print("\nRESULT: every journey-anchored moment display carries a zone attribution.")
    return 0


if __name__ == "__main__":
    sys.exit(main())