"""ORD-0500 r5: read the earlier generations' denominators out of their own frozen refs.

The delivery quotes a run of stop-control censuses across generations.  Q24 forbids carrying a number
from one generation to another, and the earlier faces no longer exist to be re-measured -- but their
receipts do, committed on the frozen review refs.  So this reads each ref's own phone/desktop JSON and
records, per generation: controls, centre-hit pressable, notices after a duplicate tap, and the blob
id of the file the number came from, so every figure in the block names the object it was read out of.
Read-only: `git ls-tree` and `git cat-file` against the local object store.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

REPO = r"D:/moodle/CityNexus"
LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
LS_REMOTE = os.path.join(LANE, "run", "ls_remote_r9.txt")
REFS = [("r1", "refs/heads/review/newlane-ord0500-phone-checkin-entry-r1"),
        ("r2", "refs/heads/review/newlane-ord0500-phone-checkin-entry-r2"),
        ("r4", "refs/heads/review/newlane-ord0500-phone-checkin-entry-r4")]


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=180)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def sha_of(ref):
    """Server truth, from the ls-remote this lane captured -- NOT `git rev-parse` of a local ref:
    this repo holds a stale `refs/heads/review/newlane-ord0500-...-r1` pointing at the commit r1 was
    cut ON rather than the candidate r1 delivered, so a local lookup would silently read the wrong
    tree."""
    if not os.path.exists(LS_REMOTE):
        return None
    for line in open(LS_REMOTE, encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            return parts[0]
    return None


def main():
    res = {"tool": "prior_denominators_r5", "took_local": datetime.now().astimezone().isoformat(),
           "refs": []}
    for label, ref in REFS:
        commit = sha_of(ref)
        row = {"generation": label, "ref": ref, "commit": commit or "UNRESOLVABLE", "faces": []}
        if commit:
            rc, listing = git("ls-tree", "-r", "--name-only", commit)
            names = [n.strip() for n in listing.splitlines() if n.strip()]
            row["all_checkin_receipts"] = [os.path.basename(n) for n in names
                                           if re.search(r"review/.*checkin_", n)]
            if not any(re.search(r"checkin_TIP_[0-9a-f]+_phone_.*\.json$", n) for n in names):
                row["GAP"] = ("这一代的枝上没有自己基座面的手机普查 JSON（只有截图），"
                              "所以它那一代的中心命中枚数在这里不可读，写 NOT_AVAILABLE_IN_THAT_REF")
            for path in names:
                if not re.search(r"review/.*checkin_.*(phone|desktop).*\.json$", path):
                    continue
                blob = git("rev-parse", "%s:%s" % (commit, path))[1].strip()
                rc2, text = git("cat-file", "-p", blob)
                if rc2 != 0:
                    continue
                try:
                    d = json.loads(text)
                except ValueError:
                    continue
                ts = d.get("tap_summary") or {}
                notices = None
                for r in d.get("rows", []):
                    if re.search(r"duplicate|same_stop", str(r.get("arm", ""))):
                        notices = (r.get("state") or {}).get("notice_count")
                row["faces"].append({"file": os.path.basename(path), "blob": blob,
                                     "generation_tag": d.get("generation"),
                                     "viewport": d.get("viewport"),
                                     "controls": ts.get("buttons"),
                                     "pressable_by_centre_hit": ts.get("pressable_by_centre_hit"),
                                     "unpressable_indices": ts.get("unpressable_indices"),
                                     "notices_after_duplicate": notices})
        res["refs"].append(row)
    # this generation, from the live sweep, in the same shape
    sweep = json.load(open(os.path.join(LANE, "evidence", "gen9_checkin_sweep_r1.json"),
                           encoding="utf-8"))
    now = {"generation": "r5", "ref": "refs/heads/review/newlane-ord0500-phone-checkin-entry-r5",
           "commit": sha_of("refs/heads/review/newlane-ord0500-phone-checkin-entry-r5"),
           "faces": []}
    for r in sweep.get("runs", []):
        c = (r.get("readings") or {}).get("census") or {}
        dup = (r.get("readings") or {}).get("after_duplicate") or {}
        now["faces"].append({"generation_tag": r.get("tag"), "viewport": r.get("viewport"),
                             "controls": c.get("controls"),
                             "pressable_by_centre_hit": c.get("pressable_by_centre_hit"),
                             "unpressable_indices": c.get("unpressable_indices"),
                             "notices_after_duplicate": dup.get("notice_count"),
                             "file": r.get("arm", {}).get("evidence")})
    res["refs"].append(now)
    rc, local = git("for-each-ref", "--format=%(refname) %(objectname)",
                    "refs/heads/review/newlane-ord0500*")
    res["local_refs_in_this_repo"] = [x for x in local.splitlines() if x.strip()]
    res["hazard"] = ("a local ref with the same name as a frozen delivery ref can point somewhere "
                     "else than the server; every commit above came from run/ls_remote_r9.txt")
    path = os.path.join(LANE, "evidence", "prior_denominators_r5.json")
    json.dump(res, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for row in res["refs"]:
        print(row["generation"], row["commit"], "faces", len(row["faces"]))
        for f in row["faces"]:
            print("   ", f.get("generation_tag"), f.get("controls"), f.get("pressable_by_centre_hit"),
                  f.get("notices_after_duplicate"), str(f.get("blob"))[:12])
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
