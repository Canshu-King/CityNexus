"""Publish the avatar hit-area hand, stacked on the touch-floor hand, and check the claims it will make.

The cut itself is deliberately invisible: the painted disc stays 28x28 (the two top-bar screenshots are
byte-identical, verified in this run by SHA-256) and only the pressable extent grows to the same floor the
rest of the phone chrome carries.  That distinction matters because the factory's own mobile gate measures
painted rects, so this hand must say plainly that the gate will still count the control as under the floor.

Refusals in this tool: the parent must be the previous hand's head read from the remote; the worktree must
differ from that head by exactly one product path; the top-bar screenshots must hash the same; and the
avatar's pressable extent in the after reading must be >= 44 on both axes, or the block would be claiming
a fix the reading does not show.
"""
import hashlib
import json
import os
import re
import subprocess

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
WT = os.path.join(LANE, "tip_walk")
BASE_REF = "refs/heads/review/0afdb49b-ord0485-touch-floor-r1"
MY_REF = "refs/heads/review/0afdb49b-avatar-hit-r1"
PRODUCT_PATH = "frontend/src/styles.css"
SUB = "review/0afdb49b-avatar-hit-r1"
ARTIFACTS = [
    ("evidence/topbar_hit_before.json", SUB + "/readings/topbar_hit_before.json"),
    ("evidence/topbar_hit_after.json", SUB + "/readings/topbar_hit_after.json"),
    ("evidence/topbar_hit_before.png", SUB + "/readings/topbar_strip_before.png"),
    ("evidence/topbar_hit_after.png", SUB + "/readings/topbar_strip_after.png"),
    ("evidence/drawer_screens_avatar.json", SUB + "/readings/drawer_screens_painted_boxes_after.json"),
    ("tools/walk_topbar_hit_r1.cjs", SUB + "/tools/walk_topbar_hit_r1.cjs"),
    ("tools/walk_drawer_screens_r1.cjs", SUB + "/tools/walk_drawer_screens_r1.cjs"),
    ("run/tip1021_build_avatar.log", SUB + "/run/build_after.log"),
]
MSG = os.path.join(LANE, "run", "commit_avatar_hit_r1_msg.txt")
IDX = os.path.join(LANE, "run", "avatar_hit_r1.tmp_index")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args, **kw):
    env = kw.pop("env", None) or ENV
    p = subprocess.run(["git", "-C", kw.pop("cwd", REPO)] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def want(cond, msg):
    if not cond:
        raise SystemExit("ABORT " + msg)


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    rc, out = git("ls-remote", "--refs", "origin", BASE_REF)
    want(rc == 0 and out.strip(), "BASE_REF_NOT_ON_REMOTE " + out[:160])
    base = out.split()[0]
    rc, out = git("ls-remote", "--refs", "origin", MY_REF)
    want(not out.strip(), "MY_REF_NOT_FREE " + out[:160])
    rc, kind = git("cat-file", "-t", base)
    want(kind.strip() == "commit", "BASE_NOT_A_COMMIT")

    # `--diff-filter=d` drops deletions: the previous hand was published from a temporary index, so its
    # own readings/ paths exist in that commit but not in this worktree, and reading that as "the cut
    # deletes files" would be an artifact of how the hand was made, not a fact about the change.
    rc, dirty = git("diff", "--name-only", "--diff-filter=d", base, cwd=WT)
    changed = [l.strip() for l in dirty.splitlines() if l.strip()]
    want(changed == [PRODUCT_PATH], "WORKTREE_NOT_A_CLEAN_SINGLE_PATH_CUT %s" % changed)
    rc, gone = git("diff", "--name-only", "--diff-filter=D", base, cwd=WT)
    deleted = [l.strip() for l in gone.splitlines() if l.strip()]
    want(all(d.startswith(SUB.replace("-hit-r1", "-floor-r1")) or d.startswith("review/") for d in deleted),
         "DELETION_OUTSIDE_LANE_ARTIFACTS %s" % deleted[:6])

    before_png = os.path.join(LANE, "evidence/topbar_hit_before.png")
    after_png = os.path.join(LANE, "evidence/topbar_hit_after.png")
    want(sha256(before_png) == sha256(after_png),
         "TOP_BAR_PIXELS_CHANGED -- the claim 'invisible cut' would be false")

    after = json.load(open(os.path.join(LANE, "evidence/topbar_hit_after.json"), encoding="utf-8"))
    want(after["verdict"] == "ALL_TOPBAR_CONTROLS_MEET_FLOOR_AND_LAND",
         "AFTER_VERDICT_NOT_CLEAN %s" % after["verdict"])
    av = [c for c in after["controls"] if c["testid"] == "topbar-avatar"][0]
    want(av["hit_w"] >= 44 and av["hit_h"] >= 44, "AVATAR_HIT_AREA_NOT_RAISED %s" % [av["hit_w"], av["hit_h"]])
    want(av["w"] == 28 and av["h"] == 28, "AVATAR_PAINTED_SIZE_CHANGED %s" % [av["w"], av["h"]])
    before = json.load(open(os.path.join(LANE, "evidence/topbar_hit_before.json"), encoding="utf-8"))
    avb = [c for c in before["controls"] if c["testid"] == "topbar-avatar"][0]
    want(avb["hit_h"] < 44, "BEFORE_ARM_NOT_RED %s" % avb["hit_h"])
    want([t["testid"] for t in after["taps"] if not t["lands"]] == [], "AFTER_TAP_MISSED")

    if os.path.exists(IDX):
        os.remove(IDX)
    env = dict(ENV)
    env["GIT_INDEX_FILE"] = IDX
    rc, out = git("read-tree", base, env=env)
    want(rc == 0, "READ_TREE " + out[:200])
    blobs = {}
    data = open(os.path.join(WT, PRODUCT_PATH), "rb").read().replace(b"\r\n", b"\n")
    rc, b = git("hash-object", "-w", "-t", "blob", "--stdin", input=data)
    want(rc == 0, "HASH_OBJECT styles.css " + b[:160])
    blobs[PRODUCT_PATH] = b.strip()
    for rel, dest in ARTIFACTS:
        src = os.path.join(LANE, rel)
        want(os.path.exists(src), "MISSING_ARTIFACT " + rel)
        payload = open(src, "rb").read()
        if not rel.endswith(".png"):
            payload = payload.replace(b"\r\n", b"\n")
        rc, out2 = git("hash-object", "-w", "-t", "blob", "--stdin", input=payload)
        want(rc == 0, "HASH_OBJECT " + rel + " " + out2[:160])
        blobs[dest] = out2.strip()
    for path, blob in sorted(blobs.items()):
        rc, out2 = git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, path), env=env)
        want(rc == 0, "UPDATE_INDEX %s %s" % (path, out2[:160]))
    rc, tree = git("write-tree", env=env)
    want(rc == 0, "WRITE_TREE " + tree[:200])
    tree = tree.strip()
    rc, commit = git("commit-tree", tree, "-p", base, "-F", MSG)
    want(rc == 0, "COMMIT_TREE " + commit[:200])
    commit = commit.strip()
    rc, out = git("diff", "--name-only", "%s..%s" % (base, commit))
    touched = [l.strip() for l in out.splitlines() if l.strip()]
    product = [p for p in touched if not p.startswith(SUB)]
    want(product == [PRODUCT_PATH], "UNEXPECTED_PRODUCT_PATHS %s" % product)
    for path in sorted(blobs):
        rc, k = git("cat-file", "-e", "%s:%s" % (base, path))
        if path != PRODUCT_PATH:
            want(rc != 0, "WOULD_REPLACE_EXISTING_PATH " + path)
        rc, k = git("cat-file", "-t", blobs[path])
        want(k.strip() == "blob", "BLOB_NOT_RESOLVABLE " + path)
    rc, out = git("push", "origin", "%s:%s" % (commit, MY_REF))
    want(rc == 0, "PUSH " + out[:300])
    rc, back = git("ls-remote", "--refs", "origin", MY_REF)
    want(back.strip() and back.split()[0] == commit, "READ_BACK_MISMATCH " + back[:160])
    os.path.exists(IDX) and os.remove(IDX)
    doc = {"ref": MY_REF, "commit": commit, "parent": base, "parent_ref": BASE_REF,
           "read_back": back.split()[0], "product_paths": product, "paths": len(touched),
           "top_bar_pixels_identical": True,
           "avatar_painted_before": [avb["w"], avb["h"]], "avatar_painted_after": [av["w"], av["h"]],
           "avatar_hit_before": [avb["hit_w"], avb["hit_h"]], "avatar_hit_after": [av["hit_w"], av["hit_h"]],
           "blobs": blobs}
    print(json.dumps(doc, indent=1, ensure_ascii=False))
    json.dump(doc, open(os.path.join(LANE, "run", "avatar_hit_publish_r1.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
