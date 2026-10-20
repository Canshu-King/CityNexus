"""Name the review heads that still have no common ancestor with the live tip.

The full census bucketed 2323 heads but only wrote out the names of the three buckets that share
ancestry with the line, which is the wrong half: the branches with no merge base are the ones no
prescription can reach, and a lane needs its own name on the list to act on it.  Two git calls per
head, progress appended as it goes.
"""

import io
import json
import os
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
OUTDIR = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot"
LIST = os.path.join(OUTDIR, "stranded_no_base.txt")
JSON_OUT = os.path.join(OUTDIR, "stranded_no_base_r1.json")
ENVS = dict(os.environ, NO_PROXY="*")


def run(args):
    p = subprocess.run(args, cwd=REPO, capture_output=True, env=ENVS)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def owner_of(ref):
    return ref.split("/")[-1].split("-")[0]


def main():
    rc, out, err = run(["git", "ls-remote", "origin",
                        "refs/heads/mirror/integration-frontend-apple-pass1"])
    parts = out.split("\t")
    tip = parts[0] if len(parts) == 2 else ""
    if len(tip) != 40:
        print("ABORT no live tip :: " + err[:120])
        sys.exit(3)

    rc, out, err = run(["git", "ls-remote", "origin", "refs/heads/review/*"])
    heads = []
    for l in out.splitlines():
        p2 = l.split("\t")
        if len(p2) == 2 and len(p2[0]) == 40:
            heads.append((p2[1], p2[0]))
    if len(heads) < 10:
        print("ABORT the remote review population read " + str(len(heads)))
        sys.exit(3)

    started = time.time()
    fh = io.open(LIST, "w", encoding="utf-8", newline="\n")
    fh.write("与现尖无共同祖先的 review 枝，取于 %s｜现尖 %s｜人口 %d\n"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), tip, len(heads)))
    stranded = []
    no_object = []
    for i, (ref, sha) in enumerate(heads):
        if run(["git", "cat-file", "-e", sha + "^{commit}"])[0] != 0:
            no_object.append(ref)
        elif not run(["git", "merge-base", tip, sha])[1]:
            stranded.append({"ref": ref, "sha": sha, "owner": owner_of(ref)})
            fh.write("%s | %s | %s\n" % (len(stranded), ref, sha))
        if (i + 1) % 200 == 0:
            fh.flush()
            sys.stdout.buffer.write(("拍 %d/%d 用去 %d 秒｜已列出无祖先 %d 枝\n"
                                     % (i + 1, len(heads), int(time.time() - started),
                                        len(stranded))).encode("utf-8", "replace"))
    fh.write("合计无共同祖先 %d 枝｜本机取不到对象的 %d 枝｜扫完用去 %d 秒\n"
             % (len(stranded), len(no_object), int(time.time() - started)))
    fh.close()

    per_owner = {}
    for s in stranded:
        per_owner[s["owner"]] = per_owner.get(s["owner"], 0) + 1
    ranked = sorted(per_owner.items(), key=lambda kv: (-kv[1], kv[0]))
    receipt = {
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "live_tip": tip,
        "heads": len(heads),
        "seconds": int(time.time() - started),
        "stranded_count": len(stranded),
        "no_local_object_count": len(no_object),
        "owners_ranked": ranked,
        "stranded_refs": stranded,
        "no_local_object_refs": no_object[:50],
    }
    io.open(JSON_OUT, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    sys.stdout.buffer.write(json.dumps(
        {k: v for k, v in receipt.items() if k not in ("stranded_refs", "no_local_object_refs")},
        ensure_ascii=False, indent=1).encode("utf-8", "replace"))
    print("\nSTRANDED-LIST-DONE")


if __name__ == "__main__":
    main()
