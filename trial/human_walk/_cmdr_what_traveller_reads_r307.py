"""bw307: rank the 221 route-reachable English refusals by what a traveller would actually read.

bw302 gave the surface split; a traveller does not care about a count, they care about which sentence
lands on their screen when they press something.  This ruler reuses bw302's own classifier (imported,
not retyped, so the two cannot drift apart) and ranks each route-reachable English sentence by three
things a reader can see: whether it carries internal vocabulary or a bare identifier, whether the
route that raises it is a traveller path (POST/GET under /api/v1/journeys or /plans) rather than a
demo or admin path, and how much of the sentence is prose rather than a code.

Same-source check: the count of ROUTE_REACHABLE English sentences must equal the number bw302 already
published in its receipt, or this ruler aborts - a second ruler quietly disagreeing with the first is
exactly the failure this shift has already hit twice.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_surface_of_english_refusals_r302 as ruler  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw307-what-a-traveller-would-read.txt")
BW302 = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                     "bw302-which-surface-says-it-in-english.txt")

TRAVELLER_ROUTE = re.compile(r"/api/v1/(journeys|plans|trips|travellers)")
NON_TRAVELLER = re.compile(r"/demo|/admin|/internal|/health|/providers|/debug")
INTERNAL_JARGON = ("journey", "plan_version", "planVersion", "snapshot", "idempotency", "payload",
                   "provider", "principal", "Journey member", "trace_id", "adcode", "place_id",
                   "counterfactual", "commitment", "receipt", "authority", "envelope")
IDENTIFIER_HINT = re.compile(r"\{[a-z_]+\}|[0-9a-fA-F]{8}|\buuid\b|\bid\b")


def published_route_reachable() -> int:
    text = io.open(BW302, encoding="utf-8", errors="replace").read()
    match = re.search(r"ENGLISH SENTENCES \d+ split by surface:.*ROUTE_REACHABLE=(\d+)", text)
    if not match:
        raise SystemExit("ABORT cannot read the published ROUTE_REACHABLE count out of bw302")
    return int(match.group(1))


def score(row) -> tuple:
    text = row["text"]
    jargon = sum(1 for word in INTERNAL_JARGON if word in text)
    identifiers = len(IDENTIFIER_HINT.findall(text))
    words = len([token for token in re.findall(r"[A-Za-z']+", text) if not token.isupper()])
    route_text = " ".join(row["routes"]) if row["routes"] else row.get("module_note", "")
    traveller_route = bool(TRAVELLER_ROUTE.search(route_text)) and not NON_TRAVELLER.search(
        route_text or "")
    # worst first: a traveller path, then internal vocabulary, then bare identifiers, then length
    return (0 if traveller_route else 1, -jargon, -identifiers, -words)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = ruler.collect()
    english_reachable = [row for row in rows
                         if row["kind"] == "ENGLISH_SENTENCE" and row["surface"] == "ROUTE_REACHABLE"]
    published = published_route_reachable()
    if len(english_reachable) != published:
        print("ABORT this ruler sees %d route-reachable sentences, bw302 published %d"
              % (len(english_reachable), published))
        return 7
    if not any(TRAVELLER_ROUTE.search(" ".join(row["routes"])) for row in english_reachable):
        print("ABORT no sentence maps to a traveller path, so the ranking would be meaningless")
        return 7

    for row in english_reachable:
        row["module_note"] = ("helper in a module with %d routes" % row["module_route_count"]
                              if not row["routes"] else "")
    ordered = sorted(english_reachable, key=score)
    top = ordered[:14]
    out = ["WHAT A TRAVELLER WOULD READ bw307",
           "SAME-SOURCE CHECK route-reachable English sentences = %d, matching bw302 exactly"
           % len(english_reachable),
           "RANKED worst-first: traveller path before other paths, then internal vocabulary, "
           "then bare identifiers, then length",
           ]
    for index, row in enumerate(top, start=1):
        out.append("%2d. %s:%d  (%s)" % (index, row["path"], row["line"], row["via"]))
        out.append("     route: %s" % (" | ".join(row["routes"])[:130] or row["module_note"]))
        out.append("     screen would show: %s" % row["text"][:130])
        out.append("     internal terms: %d, identifier slots: %d"
                   % (sum(1 for word in INTERNAL_JARGON if word in row["text"]),
                      len(IDENTIFIER_HINT.findall(row["text"]))))
    traveller_rows = [row for row in english_reachable
                      if TRAVELLER_ROUTE.search(" ".join(row["routes"]))]
    jargon_rows = [row for row in english_reachable
                   if any(word in row["text"] for word in INTERNAL_JARGON)]
    identifier_rows = [row for row in english_reachable if IDENTIFIER_HINT.search(row["text"])]
    out.append("SHAPES INSIDE THE %d" % len(english_reachable))
    out.append("  on a traveller path (/journeys, /plans, /trips, /travellers): %d"
               % len(traveller_rows))
    out.append("  carrying internal vocabulary: %d" % len(jargon_rows))
    out.append("  carrying a bare identifier slot: %d" % len(identifier_rows))
    out.append("COVERAGE_LIMIT ranking is static: it cannot say which of these a traveller reaches "
               "first in a real session, only which would read worst if reached.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
