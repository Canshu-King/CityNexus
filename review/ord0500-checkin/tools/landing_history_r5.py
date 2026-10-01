"""ORD-0500 r5: collect every landing judgement this window produced, from the logs that wrote them.

The authoritative branch moved three times while this delivery was being finished, and the landing
tool was re-run against each new tip.  The block must not say "it lands" as my word for it -- it has
to list the tip, the head, the file count and the verdict per run, each parsed out of the log file the
tool itself wrote.  Read-only over `run/*.txt`.
"""
import glob
import json
import os
import re
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REF = "newlane-ord0500-phone-checkin-entry-r5"

rows = []
for path in sorted(glob.glob(os.path.join(LANE, "run", "landing_*.txt"))):
    text = open(path, encoding="utf-8", errors="replace").read()
    tip = re.search(r'"live_tip": "([0-9a-f]{40})"', text)
    took = re.search(r'"took_local": "([^"]+)"', text)
    # only the ORD-0500 row: the same log also carries the 0485 ref, which is a different delivery
    seg = text[text.find(REF):] if REF in text else ""
    commit = re.search(r'"commit": "([0-9a-f]{40})"', seg)
    files = re.search(r'"write_set_files": (\d+)', seg)
    ident = re.search(r'"files_landing_byte_identical": (\d+)', seg)
    recut = re.search(r'"files_needing_another_recut": (\[\])', seg)
    if not (tip and commit and files and ident):
        rows.append({"log": os.path.basename(path), "PARSED": "NO -- the log does not carry a "
                     "complete 0500 row, so it is not quoted"})
        continue
    rows.append({"log": os.path.basename(path), "took_local": took.group(1) if took else None,
                 "live_tip": tip.group(1), "candidate_head": commit.group(1),
                 "write_set_files": int(files.group(1)),
                 "byte_identical": int(ident.group(1)),
                 "needs_recut": 0 if recut else "TRUNCATED_IN_LOG"})
out = {"tool": "landing_history_r5", "took_local": datetime.now().astimezone().isoformat(),
       "ref": "refs/heads/review/" + REF, "runs": rows,
       "every_run_clean": all(r.get("needs_recut") == 0 and r["byte_identical"] == r["write_set_files"]
                              for r in rows if "live_tip" in r),
       "runs_parsed": sum(1 for r in rows if "live_tip" in r)}
path = os.path.join(LANE, "evidence", "landing_history_r5.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
print("WROTE " + path)
