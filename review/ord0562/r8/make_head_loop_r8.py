# -*- coding: utf-8 -*-
"""Close the loop the blocks kept tripping on: a readiness reading names a head, then shipping the reading
moves the head. Rather than chase an infinite regress, state the exact relationship and prove it: the
reading judged head A, this branch now publishes head B, the only file between them is evidence, and the
paths the ruler judged are byte-identical across that step.
"""

import io
import json
import os
import subprocess

REPO = r"D:/moodle/CityNexus"
BRANCH = "refs/heads/review/cff87c64-ord0562-english-count-nouns-r7"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = r"D:/moodle/_ord0568_r3/r7/head_loop_r8.txt"

env = dict(os.environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(gone, None)


def sh(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, env=env)
    assert proc.returncode == 0, "command failed: git " + " ".join(args) + " :: " + proc.stderr.decode()[:200]
    return proc.stdout.decode("utf-8", "replace").strip()


rdy = json.load(io.open(r"D:/moodle/_ord0568_r3/r8/readiness_r8.json", encoding="utf-8"))
head_now = sh("ls-remote", "--refs", "origin", BRANCH).split()[0]
tip_now = sh("ls-remote", "--refs", "origin", TIP_REF).split()[0]
judged_then = rdy["items"][0]["branch_sha"]

lines = ["Delivery-time readiness, and the exact relationship between the head it judged and the head that ships."]
lines.append("$ git -C D:/moodle/CityNexus ls-remote --refs origin %s" % BRANCH)
lines.append("  now: %s" % head_now)
lines.append("  the readiness run judged: %s" % judged_then)
lines.append("$ git -C D:/moodle/CityNexus ls-remote --refs origin %s" % TIP_REF)
lines.append("  now: %s   (the same value the run recorded: %s, equal=%s)"
             % (tip_now, rdy["tip_sha"], str(tip_now == rdy["tip_sha"])))
lines.append("")
lines.append("What sits between the judged head and the shipped head:")
diff = sh("diff", "--name-only", judged_then, head_now).split("\n")
for name in [d for d in diff if d]:
    lines.append("  " + name)
outside = [d for d in diff if d and not d.startswith("review/")]
lines.append("  files outside review/ in that step: %s" % (outside or "none"))
assert not outside, "product bytes moved after the reading -- the reading must be retaken"
lines.append("")
lines.append("The paths the ruler judged, each compared against the head of the branch it belongs to:")
for item in rdy["items"]:
    own_head = sh("ls-remote", "--refs", "origin", item["branch"]).split()[0]
    now_blob = sh("rev-parse", "%s:%s" % (own_head, item["path"]))
    lines.append("  %s" % item["path"])
    lines.append("    branch %s" % item["branch"])
    lines.append("    head the run compared %s; head now %s; equal=%s"
                 % (item.get("branch_sha"), own_head, str(own_head == item.get("branch_sha"))))
    lines.append("    verdict %s; blob then %s; blob now %s; equal=%s"
                 % (item["verdict"], item["branch_blob"], now_blob, str(now_blob == item["branch_blob"])))
    assert now_blob == item["branch_blob"], item["path"] + ": judged blob moved"
lines.append("")
lines.append("So the CLEAN the ruler printed describes exactly the bytes this branch now publishes. What cannot")
lines.append("be inherited is the tip side: a CLEAN is a statement about the tip at the instant it was read --")
lines.append("hence the tip value printed above, and hence run the ruler again inside the landing window.")

text = "\n".join(lines) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print(text)
print("OK: the judged head and the shipped head agree on every path the ruler read")
