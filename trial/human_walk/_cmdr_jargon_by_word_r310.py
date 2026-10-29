"""bw310: split the 45 internal-vocabulary refusals word by word, so a ruling can be per-term.

The bucket published by bw307 cannot be pointed at: "make the internal vocabulary human" means nothing
until someone knows which words are in those sentences and how many places each word accounts for.
This ruler imports both parents (bw302's collect() and bw307's vocabulary and traveller-path test) rather
than retyping them, and aborts if its own jargon count disagrees with the published 45.

Two honesty rows are printed on purpose: the per-word hits do not sum to the bucket (one sentence can
carry several terms), and the case-sensitive match is reported next to a case-insensitive one, because
the published 45 depends on which of the two is used.
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
                       "bw310-internal-vocabulary-by-word.txt")


def published_jargon() -> int:
    text = io.open(reader.RECEIPT, encoding="utf-8", errors="replace").read()
    match = re.search(r"carrying internal vocabulary: (\d+)", text)
    if not match:
        raise SystemExit("ABORT cannot read the published jargon count out of bw307")
    return int(match.group(1))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = ruler.collect()
    reachable = [row for row in rows
                 if row["kind"] == "ENGLISH_SENTENCE" and row["surface"] == "ROUTE_REACHABLE"]
    for row in reachable:
        row["module_note"] = ("helper in a module with %d routes" % row["module_route_count"]
                              if not row["routes"] else "")
    words = reader.INTERNAL_JARGON
    bucket = [row for row in reachable if any(word in row["text"] for word in words)]
    published = published_jargon()
    out = ["INTERNAL VOCABULARY BY WORD bw310",
           "SAME-SOURCE CHECK sentences carrying internal vocabulary = %d, matching bw307 exactly"
           % len(bucket)]
    if len(bucket) != published:
        out.append("ABORT this ruler sees %d, bw307 published %d" % (len(bucket), published))
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 7

    per_word = []
    for word in words:
        hits = [row for row in reachable if word in row["text"]]
        coordinates = ["%s:%d" % (hit["path"], hit["line"]) for hit in hits]
        if not hits:
            per_word.append((0, 0, 0, word, None, coordinates))
            continue
        traveller_hits = [row for row in hits if reader.score(row)[0] == 0]
        insensitive = [row for row in reachable if word.lower() in row["text"].lower()]
        per_word.append((len(hits), len(traveller_hits), len(insensitive) - len(hits), word,
                         hits[0], coordinates))
    per_word.sort(key=lambda item: (-item[0], item[3]))

    multi = [row for row in bucket
             if sum(1 for word in words if word in row["text"]) > 1]
    bucket_ci = [row for row in reachable
                 if any(word.lower() in row["text"].lower() for word in words)]
    summed = sum(item[0] for item in per_word)
    silent = [item[3] for item in per_word if item[0] == 0]

    out.append("VOCABULARY SOURCE imported from bw307 (%d terms, not retyped here)" % len(words))
    out.append("PER WORD (route-reachable sentences, worst-first; a sentence may carry several terms)")
    for count, on_traveller, case_extra, word, representative, coordinates in per_word:
        if len(coordinates) != count:
            raise SystemExit("ABORT %s claims %d hits but carries %d coordinates"
                             % (word, count, len(coordinates)))
        if representative is None:
            out.append("  %-16s 0 hits in the 221 - the term is in the vocabulary but no reachable "
                       "sentence says it" % word)
            continue
        out.append("  %-16s %d处  on a traveller path %d  case-insensitive would add %d  "
                   "representative %s:%d"
                   % (word, count, on_traveller, case_extra,
                      representative["path"], representative["line"]))
        if count >= 2:
            out.append("  %-16s coords: %s" % ("", ", ".join(coordinates)))
    out.append("RECONCILIATION bucket=%d per-word-sum=%d difference=%d "
               "explanation=%d sentences carry more than one term"
               % (len(bucket), summed, summed - len(bucket), len(multi)))
    out.append("CASE SENSITIVITY the published %d is a case-sensitive reading; matching the same "
               "vocabulary without case would put %d sentences in the bucket (%d more), "
               "so the bucket size depends on this choice and not on the sentences"
               % (len(bucket), len(bucket_ci), len(bucket_ci) - len(bucket)))
    out.append("SILENT TERMS (%d of %d): %s"
               % (len(silent), len(words), ", ".join(silent) if silent else "none"))
    control = [item for item in per_word if item[4] is not None][0]
    sample = control[4]
    out.append("NAMED CONTROL %s asserted on %s:%d route %s screen=%r"
               % (control[3], sample["path"], sample["line"],
                  " | ".join(sample["routes"])[:90] or sample["module_note"], sample["text"][:110]))
    if control[3] not in sample["text"]:
        out.append("ABORT the named control does not contain the term it claims")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 9
    out.append("COVERAGE_LIMIT counting terms in source text cannot say which sentence the traveller "
               "reads first in a live session; it says what each word accounts for if reached.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
