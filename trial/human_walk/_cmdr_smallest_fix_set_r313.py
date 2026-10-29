"""bw313: the set a text fix would actually have to touch - traveller path AND internal vocabulary.

bw307 published 132 sentences on a traveller path; bw310 published 45 carrying internal vocabulary.
Those are two separate readings and the per-word counts even double-count a sentence, so neither number
is the size of the job.  This ruler takes the sentence-level intersection, prints it row by row, and
aborts if either parent bucket moved out from under it.

Row identity is (path, line).  A helper whose routes are only known module-wide is counted, but the row
says so and carries no URL, because claiming one would be inventing a coordinate.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_surface_of_english_refusals_r302 as ruler  # noqa: E402
import _cmdr_what_traveller_reads_r307 as reader  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw313-traveller-side-and-internal-vocabulary.txt")


def published(name, pattern):
    text = io.open(name, encoding="utf-8", errors="replace").read()
    match = re.search(pattern, text)
    if not match:
        raise SystemExit("ABORT cannot read %s out of %s" % (pattern, os.path.basename(name)))
    return int(match.group(1))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = ruler.collect()
    reachable = [row for row in rows
                 if row["kind"] == "ENGLISH_SENTENCE" and row["surface"] == "ROUTE_REACHABLE"]
    for row in reachable:
        row["module_note"] = ("helper in a module with %d routes" % row["module_route_count"]
                              if not row["routes"] else "")
    traveller = [row for row in reachable if reader.score(row)[0] == 0]
    jargon = [row for row in reachable
              if any(word in row["text"] for word in reader.INTERNAL_JARGON)]
    traveller_keys = {(row["path"], row["line"]) for row in traveller}
    jargon_keys = {(row["path"], row["line"]) for row in jargon}
    intersection = sorted(traveller_keys & jargon_keys)

    published_traveller = published(reader.RECEIPT, r"on a traveller path .*?: (\d+)")
    published_jargon = published(reader.RECEIPT, r"carrying internal vocabulary: (\d+)")
    published_reachable = published(reader.RECEIPT, r"route-reachable English sentences = (\d+)")

    out = ["TRAVELLER SIDE AND INTERNAL VOCABULARY bw313",
           "SAME-SOURCE CHECK route-reachable = %d, traveller path = %d, internal vocabulary = %d"
           % (len(reachable), len(traveller), len(jargon))]
    if (len(reachable), len(traveller), len(jargon)) != (published_reachable, published_traveller,
                                                         published_jargon):
        out.append("ABORT the parents published %d/%d/%d"
                   % (published_reachable, published_traveller, published_jargon))
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 7
    if not (len(intersection) <= min(len(traveller), len(jargon))):
        out.append("ABORT the intersection exceeds one of its parents")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 7

    by_key = {(row["path"], row["line"]): row for row in reachable}
    out.append("INTERSECTION the job a traveller-facing text fix would actually touch: %d 处"
               % len(intersection))
    out.append("  %s %s" % ("#", "coordinate / terms / route"))
    for index, key in enumerate(intersection, start=1):
        row = by_key[key]
        terms = [word for word in reader.INTERNAL_JARGON if word in row["text"]]
        out.append("  %d. %s:%d  terms=%s" % (index, key[0], key[1], ",".join(terms)))
        out.append("     route: %s" % (" | ".join(row["routes"])[:120] or row["module_note"]))
        out.append("     screen: %s" % row["text"][:120])
    only_jargon = len(jargon_keys) - len(intersection)
    out.append("WHERE THE REST SITS internal vocabulary outside a traveller path: %d 处"
               " (agent or admin surface)" % only_jargon)
    jargon_ci = {(row["path"], row["line"]) for row in reachable
                 if any(word.lower() in row["text"].lower() for word in reader.INTERNAL_JARGON)}
    intersection_ci = len(traveller_keys & jargon_ci)
    out.append("CASE SENSITIVITY the same intersection read without case would be %d 处 (%d more); "
               "both %d and the parent bucket %d are case-sensitive figures"
               % (intersection_ci, intersection_ci - len(intersection),
                  len(intersection), len(jargon)))
    out.append("COUNTING_RULE row identity is (path, line); a module-wide helper counts by its own "
               "raise and carries no invented URL")
    out.append("NAMED CONTROL %s asserted to be on a traveller path and to carry a term from the "
               "vocabulary" % (intersection[0][0] + ":" + str(intersection[0][1])))
    control = by_key[intersection[0]]
    if reader.score(control)[0] != 0 or not any(word in control["text"]
                                                for word in reader.INTERNAL_JARGON):
        out.append("ABORT the named control fails one of the two predicates")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 9
    out.append("COVERAGE_LIMIT static source reading: it cannot say which of these a live session "
               "reaches, only which would show internal vocabulary on a traveller URL.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
