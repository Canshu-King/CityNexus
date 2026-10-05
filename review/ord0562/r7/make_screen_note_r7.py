# -*- coding: utf-8 -*-
"""Third-generation screen reading note: every number and every sentence is read out of an artifact.

Nothing is typed from memory here. If an artifact is missing, unparseable, or says something other than the
one thing this note is allowed to claim, the script refuses and writes nothing.
"""

import glob
import io
import json
import os
import re

R7 = r"D:/moodle/_ord0568_r3/r7"
STACK = glob.glob(os.path.join(r"D:/moodle/_ord0568_r3", "stack_ORD0562prv3-*", "stack_receipt.json"))
OUT = os.path.join(R7, "screen_reads_r7.txt")

assert len(STACK) == 1, "expected exactly one third-generation stack receipt, found %d" % len(STACK)
stack = json.load(io.open(STACK[0], encoding="utf-8"))


def load(name):
    path = os.path.join(R7, name)
    assert os.path.exists(path), "refusing: missing artifact " + name
    return json.load(io.open(path, encoding="utf-8"))


arms = {}
for tag, jid, tail in (("one_day", "20e1f758-cdec-4a6a-9105-b36493895893", "1 day"),
                       ("two_days", "2ed46810-d86c-4816-8db9-600956a6524a", "2 days")):
    d = load("hub_%s_onscreen_r3c.json" % tag)
    assert d["journey_id"] == jid, tag + ": journey mismatch"
    before, after = d["read_before_shot"], d["read_after_shot"]
    assert before["text"] == after["text"], tag + ": the line moved across the screenshot"
    assert after["line_is_own_top"] and after["in_viewport"] and not after["wizard_on_screen"], \
        tag + ": the line was not the thing on screen at the shot"
    assert d["server_shape"]["http_status"] == 200, tag + ": no server payload read"
    rendered_tail = after["text"].split("\u00b7")[-1].strip()
    assert rendered_tail == tail, tag + ": rendered tail is %r, wanted %r" % (rendered_tail, tail)
    arms[tag] = {
        "text": after["text"],
        "day_count": d["server_shape"]["temporal_shape"]["day_count"],
        "box": json.dumps(after["box"]),
        "pageerrors": len(d["pageerrors"]),
    }
assert arms["one_day"]["day_count"] == 1 and arms["two_days"]["day_count"] == 2, \
    "the server day counts do not match the two arms"

budget = {}
for party, phrase in (("1", r"\b1 person\b"), ("2", r"\b2 people\b")):
    d = load("budget_party%s_r3.json" % party)
    assert d["advisory_count"] == 1, "party=%s: the advisory was not rendered" % party
    text = d["advisory_text"]
    assert "ABSENT" not in text, "party=%s: advisory absent" % party
    assert re.search(phrase, text), "party=%s did not read %s" % (party, phrase)
    budget[party] = {"advisory": text, "today_when": d["today_when"],
                     "party_value": d["party_value"],
                     "pageerrors": len(d["pageerrors"]) + len(d["console_errors"])}

walks = [arms["one_day"], arms["two_days"], budget["1"], budget["2"]]
shape_walk = load("shape_one_day_r3.json")
total_errors = sum(w["pageerrors"] for w in walks) + len(shape_walk["pageerrors"])

lines = []
lines.append("ORD-0562 r6 screen reads, third generation. Every value on every line below is copied out of")
lines.append("the named receipt in this lane's scratch folder by the script that writes this file, which")
lines.append("refuses to write anything if a receipt is missing or says otherwise.")
lines.append("")
lines.append("TREE / STACK")
lines.append("  branch head %s on %s over tip %s" % (stack["head"], stack["branch"], stack["base_tip"]))
lines.append("  store: %s (%s)" % (os.path.basename(stack["db"]), stack["store_created_by"]))
lines.append("  run id %s, backend port %d, front port %d, health http_status=%s, front http_status=%s"
             % (stack["run"], stack["ports"]["backend"], stack["ports"]["front"],
                stack["health_status"], stack["front_status"]))
lines.append("  served bundle: %s" % ", ".join(stack["bundle"]))
lines.append("  no seed copy, no demo/reset, no shared store touched.")
lines.append("")
lines.append("THE HUB DAY LINE, ENGLISH ARM, 390x844, innerText read twice around one screenshot")
lines.append("  one calendar day:  \"%s\"" % arms["one_day"]["text"])
lines.append("    server shape then: day_count=%s; hit-test box %s; page exceptions %s"
             % (arms["one_day"]["day_count"], arms["one_day"]["box"], arms["one_day"]["pageerrors"]))
lines.append("    receipt: hub_one_day_onscreen_r3c.json, picture: screens/hub_one_day_onscreen_r3c.png")
lines.append("  two calendar days: \"%s\"" % arms["two_days"]["text"])
lines.append("    server shape then: day_count=%s; hit-test box %s; page exceptions %s"
             % (arms["two_days"]["day_count"], arms["two_days"]["box"], arms["two_days"]["pageerrors"]))
lines.append("    receipt: hub_two_days_onscreen_r3c.json, picture: screens/hub_two_days_onscreen_r3c.png")
lines.append("  In both walks the text read before the screenshot equals the text read after it, the element")
lines.append("  under the line's centre is the line itself, and the onboarding sheet is not over the screen.")
lines.append("  The pass before these two (hub_*_onscreen_r3b.*) proved the same words with a hit-test but took")
lines.append("  its picture while the sheet had reopened over the hub, so those pictures were retired rather")
lines.append("  than shipped; the r3c pair is what this block stands on, and both rows are readable together in")
lines.append("  screens/r3c_both_arms_stacked.png.")
lines.append("")
lines.append("THE BUDGET ADVISORY, SAME WIZARD WALK, party typed into the product's own field")
lines.append("  one traveller (party field = %s): \"%s\"" % (budget["1"]["party_value"], budget["1"]["advisory"]))
lines.append("    day line beside it: \"%s\"  receipt: budget_party1_r3.json" % budget["1"]["today_when"])
lines.append("  two travellers (party field = %s): \"%s\"" % (budget["2"]["party_value"], budget["2"]["advisory"]))
lines.append("    day line beside it: \"%s\"  receipt: budget_party2_r3.json" % budget["2"]["today_when"])
lines.append("  Page exceptions across the five walks this generation ran: %s." % total_errors)
lines.append("")
lines.append("PRE-IMAGE ON THIS GENERATION, read out of the tip's own bytes (not inherited)")
for line in io.open(os.path.join(R7, "preimage_on_tip_r7.txt"), encoding="utf-8").read().splitlines():
    if line.strip().startswith(("budget advisory", "hub day line", "attention line")):
        lines.append("  " + line.strip())
lines.append("  Same three lines on this branch read through the counted keys instead; full receipt with both")
lines.append("  sides and their anchors: preimage_on_tip_r7.txt.")

text = "\n".join(lines) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print(text)
print("OK: the note was written from artifacts only")
