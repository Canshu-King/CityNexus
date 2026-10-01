"""ORD-0500 r5: re-anchor the shipped comments to the bytes this generation actually holds.

Two comments in the write set asserted coordinates that were measured one or two generations back:
the door-family anchors in `backend/tests/test_qoder_ord0500_journey_refusal.py` (797/3812/3848/3865)
and the reachability sentence in `frontend/src/features/checkin/footprint.css`.  Every replacement
here is a line this lane read out of `wt23` (= the tip, byte-identical to the base face) or out of
this generation's own door probe, and the script prints what each anchor actually says so a reviewer
can re-check it without opening three files.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
NL = chr(10)
TIP = subprocess.run(["git", "-C", os.path.join(LANE, "wt23"), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip()

report = {"tool": "fix_shipped_comments_r5", "took_local": datetime.now().astimezone().isoformat(),
          "tip": TIP, "anchors": [], "edits": []}

tip_lines = open(os.path.join(LANE, "wt23/backend/app/main.py"), encoding="utf-8").read().splitlines()


def anchor(line_no, must_contain, label):
    text = tip_lines[line_no - 1]
    ok = must_contain in text
    report["anchors"].append({"line": line_no, "label": label, "text": text.strip()[:120],
                              "carries": must_contain, "verified": ok})
    if not ok:
        raise SystemExit("ANCHOR_REFUSED %s @ %s does not carry %r -- line reads %r"
                         % (label, line_no, must_contain, text.strip()[:120]))
    return line_no


REQ = anchor(810, "def require(", "shared require() helper")
LOOKUP = anchor(3912, "existing = session.scalars(", "door's own duplicate lookup")
INTEGRITY = anchor(3948, "except IntegrityError as exc:", "index catch branch")
CAUGHT = anchor(3965, '"caught_by": "unique_index"', "caught_by marker")

# the base door's unnamed refusal, as this generation's probe actually answered it
doors = json.load(open(os.path.join(LANE, "evidence/gen9_doors_wt23-wt22-mutgen9.json"),
                       encoding="utf-8"))
base = [r for r in doors["runs"] if r.get("tree") == "wt23"][0]
probe = [p for p in base["probes"] if p.get("case") == "write_door_unknown_journey"][0]
assert probe["http_status"] == 404 and probe["details_is_null"] is True, json.dumps(probe)[:300]
assert probe["uuid_in_message"] is True and probe["reason_code"] is None, json.dumps(probe)[:300]
sentence = probe["message"]
body_bytes = probe["body_bytes"]
receipt = "review/ord0500-checkin/receipts/gen9_doors_wt23-wt22-mutgen9.json"

path = os.path.join(LANE, "wt22/backend/tests/test_qoder_ord0500_journey_refusal.py")
src = open(path, encoding="utf-8").read()

old_head = src.split('"""', 2)[1]
new_head = (
    """ORD-0500: the footprint doors name the trip they cannot find, without printing an id.

The measured starting shape, read on this lane's own base tree at tip
`TIPSHA` (the very bytes the base face serves), and kept in
`RECEIPT`, probe case
`write_door_unknown_journey`:

    POST /api/v1/journeys/<uuid>/checkins   -> http_status 404, body_bytes NBYTES
        message      "SENTENCE"
        details      null
        reason_code  null

Three things wrong in one answer, all of them the family this project keeps having to fix: a uuid
inside a traveller's sentence, no name to switch on, and a null where the contract says a reason
rides.  It came from the shared `require()` helper (`backend/app/main.py:REQLINE`), which every door
uses, so the fix is inside the footprint doors' own journey read -- and these arms keep it there.

Nothing here calls `POST /api/v1/demo/reset`, and nothing runs against a shared store: the engine is
pointed at a one-off file by the runner (`CITYNEXUS_DATABASE_URL`), the way the sibling
`tests/test_qoder_ord0476_checkins.py` insists on it.
""".replace("TIPSHA", TIP).replace("RECEIPT", receipt).replace("NBYTES", str(body_bytes))
   .replace("SENTENCE", sentence).replace("REQLINE", str(REQ))
)
assert src.count('"""' + old_head + '"""') == 1, "docstring opener not found once"
src = src.replace('"""' + old_head + '"""', '"""' + new_head + '"""')
report["head_replaced"] = True

old_body = (
    "    Two guards refuse a second tap on the same stop: the door looks its own table up first" + NL +
    "    (`backend/app/main.py:3812`), and the `UNIQUE (journey_id, target_key)` index catches a race the" + NL +
    "    lookup could not see (`:3848`), which is the only branch that adds `caught_by: unique_index`" + NL +
    "    (`:3865`).  A screen-side check of the sentence cannot tell those apart -- delete the door's")
new_body = (
    "    Two guards refuse a second tap on the same stop, both of them on this tip: the door looks" + NL +
    "    its own table up first (`backend/app/main.py:LOOKUP`), and the `UNIQUE (journey_id," + NL +
    "    target_key)` index catches a race that lookup cannot see (`:INTEGRITY`), which is the only" + NL +
    "    branch that adds `caught_by: unique_index` (`:CAUGHT`).  A screen-side check of the" + NL +
    "    sentence cannot tell those apart -- delete the door's")
if src.count(old_body) == 1:
    src = (src.replace(old_body, new_body)
              .replace("LOOKUP", str(LOOKUP)).replace("INTEGRITY", str(INTEGRITY))
              .replace("CAUGHT", str(CAUGHT)))
    report["body_replaced"] = "from the stale anchors"
else:
    # a re-run: the anchors this script writes must already be the ones this tip carries, or the
    # shipped comment is rot again -- so verify the numbers in place instead of replacing blindly.
    found = re.findall(r"backend/app/main\.py:(\d+)|`:(\d+)`", src)
    nums = sorted({int(a or b) for a, b in found})
    want = sorted({REQ, LOOKUP, INTEGRITY, CAUGHT})
    assert nums == want, "re-run found anchors %s, this tip says %s" % (nums, want)
    report["body_replaced"] = "already anchored; the four numbers in place equal this tip's lines"
open(path, "w", encoding="utf-8", newline=NL).write(src)
import ast
ast.parse(src)
report["edits"].append({"file": "backend/tests/test_qoder_ord0500_journey_refusal.py",
                        "sha256_after": hashlib.sha256(src.encode("utf-8")).hexdigest()[:16],
                        "ast": "parsed"})

css = os.path.join(LANE, "wt22/frontend/src/features/checkin/footprint.css")
css_text = open(css, encoding="utf-8").read()
report["edits"].append({"file": "frontend/src/features/checkin/footprint.css",
                        "bytes": len(css_text.encode("utf-8")),
                        "sha256_after": hashlib.sha256(css_text.encode("utf-8")).hexdigest()[:16],
                        "asserts_5_of_6": "5 of the 6 stop controls" in css_text,
                        "no_stale_all_six": "all six stops answer" not in css_text})
mut = os.path.join(LANE, "wt24/frontend/src/features/checkin/footprint.css")
open(mut, "w", encoding="utf-8", newline=NL).write(css_text)
report["edits"].append({"file": "wt24 (CE-2 mutant) footprint.css synced",
                        "identical_to_candidate":
                            open(mut, "rb").read() == open(css, "rb").read()})

out = os.path.join(LANE, "run", "fix_shipped_comments_r5.json")
json.dump(report, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(json.dumps(report, indent=2, ensure_ascii=False))
print("WROTE " + out)
