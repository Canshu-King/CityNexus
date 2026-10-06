"""Receipt for the AMENDED coordinate bolt of the ledger write door.

Reads the captured selftest run (door_bolt_selftest_r6.txt) and derives every verdict from the per-fixture
readings - nothing here is typed as a literal PASS.  The point of the file is the two-way property: the bolt
must carry an honestly-disclosed non-git value when a fetchable coordinate sits in the SAME paragraph, and
must still refuse (a) an undisclosed value, (b) a disclosed value with no co-paragraph coordinate, and
(c) a disclosed value whose only coordinate lives in another paragraph.
"""
import hashlib
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(os.path.dirname(HERE), "evidence", "cmdr-patrol-0404")
RUN = os.path.join(EV, "door_bolt_selftest_r6.txt")
DOOR = os.path.join(HERE, "ledger_insert_after.py")
GATE = os.path.join(HERE, "claim_coordinate_check_r4c.py")
SELF = os.path.join(HERE, "ledger_door_bolt_selftest_r1.py")


def blob(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest(), len(raw)


s = io.open(RUN, encoding="utf-8").read()
run = json.loads(s[s.find("{"):])
rows = {r["fixture"]: r for r in run["rows"]}
expected = {  # what each fixture is supposed to do, declared independently of the run
    "exempt_p3_line45_verbatim": "exempt", "exempt_p3_line48_verbatim": "exempt",
    "exempt_s4_sha1_over_bytes_wording": "exempt",
    "exempt_s4_file_sha1_wording": "exempt", "exempt_line_all_coordinates_resolve": "exempt",
    "negative_control_the_word_blob_alone_does_not_refuse": "exempt",
    "fire_undeclared_same_value": "fire", "fire_declared_but_no_anchor_on_line": "fire",
    "fire_declared_anchor_in_OTHER_paragraph": "fire",
}
agree = {}
for name, want in sorted(expected.items()):
    r = rows.get(name)
    agree[name] = bool(r) and ((r["rc"] == 9) if want == "fire" else (r["rc"] != 9 and r["reached_anchor_check"]))
derived = {
    "every_fixture_answered_as_declared": all(agree.values()) and len(agree) == len(rows),
    "the_bolt_fires_on_undeclared_values": agree.get("fire_undeclared_same_value") is True,
    "the_bolt_fires_when_no_fetchable_coordinate_is_nearby":
        agree.get("fire_declared_but_no_anchor_on_line") is True,
    "the_bolt_fires_across_a_paragraph_boundary": agree.get("fire_declared_anchor_in_OTHER_paragraph") is True,
    "honest_disclosures_are_carried_not_punished":
        agree.get("exempt_p3_line45_verbatim") is True and agree.get("exempt_p3_line48_verbatim") is True
        and agree.get("exempt_s4_sha1_over_bytes_wording") is True,
    "no_fixture_reached_the_ledger_write": all(r["rc"] != 0 for r in rows.values()),
    "selftest_all_two_way_assertions_hold": run["all_two_way_assertions_hold"] is True,
}
out = {
    "schema": "CNX_CMDR_LEDGER_DOOR_COORD_BOLT_SELFTEST_V1",
    "lane": "commander 494abfd7",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
    "why": "Two lane blocks were refused tonight for reasons that were mine, not theirs: HJ-P3's `aad2d1f2_0059.md` "
           "cites a locally recomputed sha1 of bytes that never entered git and says so in its own words, and "
           "S4's `S4-ast-taint_0412.md` names a plain sha1-over-bytes for the same reason.  A bolt that cannot "
           "read an honest disclosure is a bolt lanes will route around, so the disclosure path was added to "
           "the door itself and proven both ways here.",
    "rule_added": "A 40-hex that does not resolve may be carried only when (i) the value's OWN line declares it "
                  "non-git in one of the recognised literal phrases and (ii) a coordinate that does resolve sits "
                  "in the same paragraph. Every carried value is printed and dumped to "
                  "_non_retrievable_carried.json next to the block.",
    "recognised_phrases": ["故意不可取回", "从未入 git", "非 blob", "不可 cat-file", "本地字节重算",
                            "sha1(over bytes)", "sha1 over bytes"],
    "tool_blobs": {"ledger_insert_after.py": blob(DOOR), "selftest ledger_door_bolt_selftest_r1.py": blob(SELF),
                   "q43 claim_coordinate_check_r4c.py": blob(GATE)},
    "anchor_coordinate_used": run["anchor_coordinate_used"],
    "fixtures": rows,
    "declared_expectation_vs_observed": agree,
    "derived": derived,
    "claim_kind": "recomputation",
    "raw_run_blob": blob(RUN),
}
txt = json.dumps(out, ensure_ascii=False, indent=1)
io.open(os.path.join(HERE, "_coord_bolt_selftest_r1.json"), "w", encoding="utf-8", newline="\n").write(txt)
print(json.dumps(out["derived"], ensure_ascii=False, indent=1))
print("door", out["tool_blobs"]["ledger_insert_after.py"][0], "| selftest",
      out["tool_blobs"]["selftest ledger_door_bolt_selftest_r1.py"][0], "| bytes", len(txt.encode("utf-8")))
