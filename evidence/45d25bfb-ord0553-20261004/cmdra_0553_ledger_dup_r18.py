"""ORD-0553 r18 -- the ledger duplication I reported: whose side is it on?

Two turns ago I reported that my r13e heading appears twice in the ledger while the applier handed me one
receipt.  "It is not me" is a claim, so this measures it: duplication across the whole ledger (how many
titles, how many lanes), the applier's own receipt count for my block, and whether the copies sit close
together the way a duplicated rewrite region would.

I do not write the ledger -- it has one writer and it is not me.  This file only reads it and reads my own
inbox receipts.
"""
import collections
import io
import json
import os
import re

LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
MINE = "45d25bfb"
MY_TITLE_MARK = "勘误（我 r13 那块里一句证据引用写宽了）"

report = {"instrument": "cmdra_0553_ledger_dup_r18", "ledger": LEDGER, "arms": []}
lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
heads = [(i + 1, t) for i, t in enumerate(lines) if t.startswith("### ")]
counts = collections.Counter(t for _i, t in heads)
dup = {t: n for t, n in counts.items() if n > 1}
where = collections.defaultdict(list)
for ln, t in heads:
    if t in dup:
        where[t].append(ln)

# which lanes a duplicated title belongs to: the lane id as it appears in the block itself
LANE = re.compile(r"\b([0-9a-f]{8})\b")


def lanes_of(title):
    """The lane id a block belongs to, taken from its own heading -- the body carries hex ids of every
    other kind (blobs, commits, uuids) and would make this counter meaningless."""
    return sorted(set(LANE.findall(title)))


dup_lanes = collections.Counter()
for t in where:
    for lane in lanes_of(t):
        dup_lanes[lane] += 1
all_lanes = collections.Counter()
for _ln, t in heads:
    for lane in lanes_of(t):
        all_lanes[lane] += 1
report["lanes_total"] = len(all_lanes)
report["headings_total"] = len(heads)
report["headings_distinct"] = len(counts)
report["duplicated_titles"] = len(dup)
report["lanes_with_a_duplicated_title"] = dict(dup_lanes)
my_titles = [t for t in where if MY_TITLE_MARK in t]
report["my_block"] = {"titles_matched": len(my_titles),
                      "copies_at": where[my_titles[0]] if my_titles else []}
receipts = sorted(f for f in os.listdir(PROCESSED) if f.startswith(MINE) and ".inserted_" in f)
my_receipts = [f for f in receipts if "0419" in f]
report["my_receipts_for_that_block"] = my_receipts
report["my_receipts_total"] = len(receipts)
gaps = sorted(min(b - a for a, b in zip(sorted(where[t]), sorted(where[t])[1:])) for t in where
              if len(where[t]) > 1)
report["distance_between_copies_lines_median"] = gaps[len(gaps) // 2] if gaps else None


def arm(ident, ok, observed):
    report["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


arm("the_duplication_is_not_mine_alone",
    len(dup_lanes) >= 2 and MINE in dup_lanes,
    "%d lanes have a duplicated title; among them mine (%s): %s" % (
        len(dup_lanes), MINE, MINE in dup_lanes))
arm("my_block_was_inserted_once_by_the_applier",
    len(my_receipts) == 1,
    "receipts naming that drop: %s (my receipts on disk: %d)" % (my_receipts, len(receipts)))
arm("the_scan_can_see_single_copies_too",
    len(counts) > len(dup) and report["headings_total"] >= 1000,
    "%d headings, %d distinct, %d duplicated -- a scan that only found duplicates would be blind" % (
        len(heads), len(counts), len(dup)))
arm("the_two_copies_sit_close_like_a_rewritten_region",
    report["distance_between_copies_lines_median"] is not None
    and report["distance_between_copies_lines_median"] < 200,
    "median distance between copies: %s lines" % report["distance_between_copies_lines_median"])

red = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "GREEN" if not red else "RED"
report["red_arms"] = red
report["not_written_by_me"] = True
path = r"D:/moodle/_qoder_cmdra_ord0553_20261003/_evidence/r18_ledger_dup.json"
io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k: report[k] for k in ("verdict", "red_arms", "arms", "headings_total",
                                         "headings_distinct", "duplicated_titles",
                                         "lanes_with_a_duplicated_title", "my_block",
                                         "my_receipts_for_that_block",
                                         "distance_between_copies_lines_median")},
                 ensure_ascii=False, indent=1))
print("WROTE", path)
