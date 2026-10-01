"""Does each of my refs still land byte-for-byte on the tip the sequencer is reading now?

The rule this lane follows after two bounced rebases: ancestry proves nothing, bytes do.  For every
file in a candidate's write-set the tool compares the candidate's own blob with the blob the read-only
merge predicts on the live tip; a file that differs is exactly what a recut gate would stop on, so it
is named with both ids instead of being smoothed over.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, r"D:/moodle/_qoder_phone_ord0485_20260930/tools")
from git_blob_probe_r1 import blob_at  # noqa: E402

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
BRANCHES = {"review/newlane-ord0500-phone-checkin-entry-r5": "b604f50d1645d028c2dd1d4406caee8198a3bc2d",
            "review/newlane-ord0485-phone-walkthrough-r5":
                "0989713aa687b97f4cd40bae009a6ce493425a4b"}


def pick_sha(text, needle):
    """ls-remote answers one line per ref; a warning line from the ssh transport can be printed
    first and this tool merges stderr into stdout, so the sha is taken from the line whose second
    field is exactly the ref asked for -- never from the first token of the blob."""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == needle and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def git(*args):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    env["NO_PROXY"] = "api.github.com"
    return subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=240,
                          env=env).stdout.decode("utf-8", "replace").strip()


TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
tip = pick_sha(git("ls-remote", "origin", TIP_REF), TIP_REF)
if tip is None:
    raise SystemExit("ABORT_NO_LIVE_TIP -- ls-remote did not answer a line for " + TIP_REF)
out = {"tool": "gen9_landing_check_r1", "took_local": datetime.now().astimezone().isoformat(),
       "live_tip": tip, "refs": []}
for name, base in BRANCHES.items():
    listed = git("ls-remote", "origin", "refs/heads/" + name)
    found = pick_sha(listed, "refs/heads/" + name)
    if found:
        sha, sha_source = found, "remote ls-remote"
    else:
        # the ref is not on the server yet in this round: the prediction is still meaningful on the
        # bytes I am about to push, as long as the receipt says where the sha came from.
        local = git("rev-parse", "refs/heads/" + name)
        if not re.fullmatch(r"[0-9a-f]{40}", local):
            out["refs"].append({"ref": "refs/heads/" + name, "ABSENT": "NOT_ON_REMOTE_AND_NO_LOCAL_REF"})
            continue
        sha, sha_source = local, "local ref, not yet pushed -- the push carries exactly these bytes"
    merged = git("merge-tree", "--write-tree", tip, sha).splitlines()[0]
    files = git("diff", "--name-only", base, sha).splitlines()
    differs, identical = [], 0
    for f in files:
        mine = git("rev-parse", "%s:%s" % (sha, f))
        in_merge = git("rev-parse", "%s:%s" % (merged, f))
        if mine != in_merge:
            differs.append({"path": f, "candidate_blob": mine, "merge_blob": in_merge,
                            "live_tip_blob": blob_at(tip, f)})
        else:
            identical += 1
    out["refs"].append({"ref": "refs/heads/" + name, "commit": sha, "cut_on": base,
                        "predicted_tree": merged, "write_set_files": len(files),
                        "files_landing_byte_identical": identical,
                        "files_needing_another_recut": differs})
path = os.path.join(LANE, "evidence", "gen9_landing_check_r1.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False)[:2000])
print("WROTE " + path)
