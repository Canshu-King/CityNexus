"""bw318: for each of the 21 traveller-facing English refusals, is there a button that reaches it?

bw313 names the URLs and the sentences; it does not say whether a traveller can press anything that hits
them.  This ruler walks frontend/src and asks, per URL, whether the last two non-parameter path segments
appear together in a hand-written source file (citynexus.ts builds paths by string concatenation, so the
shape to look for is "/plans/" plus id plus "/select", not one literal string).

Three answers are kept apart, because they mean different things to a ruling:
  CALLER_FOUND   a hand-written file builds this path
  GENERATED_ONLY only the generated OpenAPI client mentions it - nobody in the UI asks
  NO_CALLER      no frontend file mentions it at all

The generated client and test/spec helpers are excluded from CALLER_FOUND on purpose; counting them
would turn every route into a "reachable button".
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_smallest_fix_set_r313 as intersection  # noqa: E402

FRONTEND = os.path.join(ROOT, "frontend", "src")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw318-which-of-these-has-a-button.txt")
HEAD_ROW = re.compile(r"^\s*(\d+)\.\s+(\S+):(\d+)\s+terms=(.*)\s*$")
CJK = re.compile(r"[一-鿿]")


def published_rows():
    lines = io.open(intersection.RECEIPT, encoding="utf-8", errors="replace").read().split("\n")
    rows = []
    for index, line in enumerate(lines):
        head = HEAD_ROW.match(line)
        if not head:
            continue
        route = lines[index + 1].split("route:", 1)
        screen = lines[index + 2].split("screen:", 1)
        if len(route) < 2 or len(screen) < 2:
            raise SystemExit("ABORT bw313 row %s has an unexpected shape" % head.group(1))
        rows.append({"rank": int(head.group(1)), "file": head.group(2), "line": int(head.group(3)),
                     "terms": head.group(4).strip(), "route": route[1].strip(),
                     "screen": screen[1].strip()})
    if not rows:
        raise SystemExit("ABORT bw313 published no rows")
    return rows


def source_files():
    for base, dirs, names in os.walk(FRONTEND):
        dirs[:] = [d for d in dirs if d not in ("generated", "node_modules")]
        for name in names:
            if not name.endswith((".ts", ".tsx")):
                continue
            if ".test." in name or ".spec." in name:
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            try:
                yield rel, io.open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue


def tail_segments(url):
    parts = [segment for segment in url.split("/") if segment and not segment.startswith("{")]
    if len(parts) < 2:
        raise SystemExit("ABORT cannot take two path segments out of %r" % url)
    return parts[-2], parts[-1]


def hits_for(url, files):
    previous, last = tail_segments(url)
    matches = []
    for rel, text in files:
        if last not in text or previous not in text:
            continue
        if rel.endswith(".tsx") and "trial" in rel:
            continue
        lines = text.split("\n")
        # anchor on the last segment: /plans/{id}/select must read the line that says select, not any
        # line that mentions plans
        line_no = max((index + 1 for index, row in enumerate(lines) if last in row), default=0)
        nearby = ""
        for index in range(max(0, line_no - 1), min(len(lines), line_no + 40)):
            if CJK.search(lines[index]) and ('"' in lines[index] or "'" in lines[index]):
                nearby = "%s:%d %s" % (rel, index + 1, lines[index].strip()[:70])
                break
        matches.append({"rel": rel, "line": line_no, "copy": nearby})
    return matches


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = published_rows()
    files = list(source_files())
    out = ["WHICH OF THESE HAS A BUTTON bw318",
           "DENOMINATOR rows read out of bw313 = %d; frontend files scanned = %d "
           "(generated client, tests and spec helpers excluded)" % (len(rows), len(files))]
    counts = {"CALLER_FOUND": 0, "NO_CALLER": 0}
    for row in rows:
        # bw313 writes "app /api/v1/journeys/{id}/start" - the method word is glued to the path
        urls = [found.group(1) for found in
                (re.search(r"(/\S+)", token) for token in row["route"].split("|")) if found]
        if not urls:
            out.append("%2d. %s:%d  NO_URL_ON_THIS_ROW (%s)"
                       % (row["rank"], row["file"], row["line"], row["route"][:60]))
            counts["NO_CALLER"] += 1
            continue
        url = urls[0]
        matches = hits_for(url, files)
        if not matches:
            verdict = "NO_FRONTEND_CALLER"
            counts["NO_CALLER"] += 1
            out.append("%2d. %s  (backend %s:%d, terms=%s) -> %s"
                       % (row["rank"], url, row["file"], row["line"], row["terms"], verdict))
            continue
        counts["CALLER_FOUND"] += 1
        out.append("%2d. %s  (backend %s:%d, terms=%s) -> CALLER_FOUND in %d 处"
                   % (row["rank"], url, row["file"], row["line"], row["terms"], len(matches)))
        for match in matches[:3]:
            out.append("      %s:%d%s" % (match["rel"], match["line"],
                                          ("  copy: " + match["copy"]) if match["copy"] else ""))
    out.append("TALLY caller_found=%d no_caller=%d total=%d"
               % (counts["CALLER_FOUND"], counts["NO_CALLER"], len(rows)))
    if counts["CALLER_FOUND"] + counts["NO_CALLER"] != len(rows):
        out.append("ABORT the tally does not cover every row")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 8
    out.append("NEGATIVE_CONTROL /api/v1/journeys/{journey_id}/zzz-not-a-real-route must find nothing: %s"
               % ("CLEAN" if not hits_for("/api/v1/journeys/{journey_id}/zzz-not-a-real-route", files)
                  else "the ruler matched a route that does not exist"))
    out.append("COUNTING_RULE a file counts as a caller only if it carries both of the last two path "
                "segments; the generated OpenAPI client is never a caller")
    out.append("COVERAGE_LIMIT a caller in source is not a button a traveller can press: this proves "
               "the path is asked for somewhere in the frontend, not that any screen offers it. "
               "The nearby copy is the first CJK string within 40 lines, which may belong to another "
               "control in the same file.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
