"""bw326: across the panels the registry mounts, how many catch blocks read the server's own words?

bw325 walked the 20 caller rows and found none of them showing the server sentence, which raises the
broader question: is that the product's habit, or those 20 sites?  This ruler does not answer for a
request; it answers for a file - every mounted panel module is read, every `catch` body in it is
classified by whether it touches the caught error at all, and the two numbers are kept apart.

  READS_THE_REFUSAL   the catch body reads an attribute of the caught error (detail / message / response /
                      data / statusText), so a server sentence can reach the screen from here
  HIDES_THE_REFUSAL   the catch body never touches the error, so whatever the backend said is gone at this
                      point and only the frontend's own words are left

A mounted module with no catch at all is reported as such instead of counted as hiding anything.  The two
controls are the same shape bw325 uses, taken from this tree rather than asserted.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402  (owns the file scan)
import _cmdr_panel_ask_r322 as panel  # noqa: E402  (owns the import-and-JSX mount test)
import _cmdr_screen_text_r325 as screen  # noqa: E402  (owns CATCH, SERVER_READ, catch_body)

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw326-what-the-panels-do-with-a-refusal.txt")


def read(rel):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % rel)
    return io.open(path, encoding="utf-8", errors="replace").read()


def bodies(rel):
    """Every catch body in the file, with its line."""
    lines = read(rel).split("\n")
    found = []
    index = 0
    while index < len(lines):
        if index + 1 not in screen.comment_spans(lines) and screen.CATCH.search(lines[index]):
            caught_at, body = screen.catch_body(lines, index)
            found.append((caught_at, body))
            index = caught_at
        else:
            index += 1
    return found


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = dict(reach.source_files())
    mounted_keys, imported_modules, rendered = panel.registry_panels(files[panel.REGISTRY_REL])

    shows_rel, shows_line = screen.passthrough_site(list(files.items()))
    bare_rel = screen.catchless_site(list(files.items()))
    if (screen.classify(shows_rel, shows_line)[0],
         screen.classify(bare_rel, 1)[0] if bare_rel else "",
         screen.classify("frontend/src/features/execution/LiveRecovery.tsx", 270)[0]) != (
            "SHOWS_SERVER_TEXT", "NO_CATCH_IN_WINDOW", "OWNS_ITSOWN_TEXT"):
        print("ABORT a control site did not classify as the source proves it should")
        return 7

    out = ["WHAT THE PANELS DO WITH A REFUSAL bw326",
           "DENOMINATOR the registry imports %d module(s), %d of them rendered as a component, so %d "
           "mounted files are read here; the registry's own JSX names %d components in total, which is a "
           "wider set than modules because one module can render several"
           % (len(imported_modules), len(mounted_keys), len(mounted_keys), len(rendered))]
    rows = []
    reading_sites = []
    for key in sorted(mounted_keys):
        candidates = [rel for rel in files if rel.split("src/", 1)[-1].rsplit(".", 1)[0] == key]
        if not candidates:
            raise SystemExit("ABORT a mounted module has no scanned file behind it: %s" % key)
        rel = candidates[0]
        caught = bodies(rel)
        shows = sum(1 for _, body in caught if screen.SERVER_READ.search(body))
        reading_sites += [(rel, line) for line, body in caught if screen.SERVER_READ.search(body)]
        rows.append((rel, len(caught), shows))
    total_caught = sum(count for _, count, _ in rows)
    total_shows = sum(shows for _, _, shows in rows)
    for rel, count, shows in sorted(rows, key=lambda item: (-item[1], item[0])):
        out.append("  %s  catch %d 处，读服务端原文 %d 处，吞掉 %d 处"
                   % (rel, count, shows, count - shows))
    out.append("TALLY panels=%d catch=%d reads_the_refusal=%d hides_the_refusal=%d"
               % (len(rows), total_caught, total_shows, total_caught - total_shows))
    out.append("READS_THE_REFUSAL_AT %s"
               % (", ".join("`%s:%d`" % (rel, line) for rel, line in reading_sites) or "no site"))
    for rel, line in reading_sites:
        cells = read(rel).split("\n")
        tell = next((index + 1 for index in range(line, min(line + 12, len(cells)))
                     if re.search(r"\bdrop(?:ped|s)?\b", cells[index], re.I)), 0)
        if tell:
            out.append("READS_BUT_DROPS `%s:%d` - the body says at `%s:%d` that the sentence is dropped "
                       "and only a machine token is matched, so reading the error here is not the same as "
                       "putting it on screen" % (rel, line, rel, tell))
        else:
            out.append("READS_KEEP_UNKNOWN `%s:%d` reads the error and no statement about dropping it "
                       "appears in the lines after it, so this ruler claims neither outcome"
                       % (rel, line))
    loose = re.compile(r"(?:as Error\)\.message|String\(\s*(?:err|error|e)\b|\.message\b|\.detail\b|"
                       r"instanceof (?:Error|V8Rejection))")
    wide = sum(1 for rel, _, _ in rows for _, body in bodies(rel) if loose.search(body))
    out.append("WIDE_PATTERN_CHECK the same bodies tested with a deliberately loose pattern "
               "(`.message`, `.detail`, `instanceof Error` or `V8Rejection`, `String(err)`, "
               "`as Error).message`) read the refusal %d time(s) against the strict pattern's %d, so the "
               "count is not an artifact of the attribute names I picked" % (wide, total_shows))
    if wide != total_shows:
        out.append("ABORT the loose pattern disagrees, so the strict pattern is hiding sites")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 9
    if total_shows > total_caught - total_shows:
        out.append("SHAPE more catch bodies read the refusal than hide it, so the panel habit is to "
                   "surface what the server said")
    else:
        out.append("SHAPE most catch bodies never touch the caught error, so the panel habit is to "
                   "replace the server's words with its own")
    no_catch = [rel for rel, count, _ in rows if count == 0]
    out.append("NO_CATCH_AT_ALL %d of the %d mounted files hold no catch block, so a refusal there is "
               "handled by whoever called them, not by the panel: %s"
               % (len(no_catch), len(rows), ", ".join(no_catch) or "none"))
    out.append("CONTROLS `%s:%d` before a catch that reads the error classified as reading it; `%s` with "
               "no catch classified as having no answer; the LiveRecovery handler that assigns its own "
               "bilingual sentence classified as hiding it. The ruler aborts if any disagrees."
               % (shows_rel, shows_line, bare_rel))
    out.append("COUNTING_RULE one mounted file is read as a whole; every `catch` in it gives one body, "
               "and that body counts as reading the refusal only if it takes an attribute off the caught "
               "error (detail, message, response, data, statusText)")
    out.append("COVERAGE_LIMIT a catch that reads the error and then drops it on the floor still counts as "
               "reading it, and a refusal handled outside the panel file (in a shared hook, or by the "
               "shell's V8Rejection path at frontend/src/app/V8Experience.tsx:307) is not attributed to "
               "the panel at all. This measures the panel's habit, not what any traveller saw.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
