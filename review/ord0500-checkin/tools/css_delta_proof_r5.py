"""ORD-0500 r5: prove what my CSS block's second edit did, and what it did not touch.

The r4 delivery claimed `footprint.css` merged to the same blob as the generation before.  r5 changes
that file again -- one sentence in MY comment asserted "all six stops answer a centre hit" while this
lane's census measures 5 of 6 -- so the claim must be re-derived per blob: r4's bytes, r5's bytes,
which lines moved, and whether ORD-0530's by-day block (the 40 lines that landed at 04:27) is
byte-identical in both.  Read-only: it writes one JSON and creates no git object.
Pass "INDEX" as the first argument to hash the file as this worktree's staged index holds it.
"""
import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

REPO = r"D:/moodle/CityNexus"
WT = r"D:/moodle/_qoder_phone_ord0485_20260930/wt22"
R4 = "469d72be6d1b1348d4fab7ad0bb3f9256a888d7d"
PATH = "frontend/src/features/checkin/footprint.css"
LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"


def _git(cwd, *args):
    p = subprocess.run(["git", "-C", cwd] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def blob_of(rev):
    """`rev` is a commit in the shared object store, or INDEX for this worktree's staged copy."""
    if rev == "INDEX":
        rc, out = _git(WT, "rev-parse", ":%s" % PATH)
    else:
        rc, out = _git(REPO, "rev-parse", "%s:%s" % (rev, PATH))
    if rc != 0:
        return "ABSENT_OR_UNPARSABLE:" + out[:80]
    return out


def text_of(blob):
    if not re.fullmatch(r"[0-9a-f]{40}", blob):
        return ""
    rc, out = _git(REPO, "cat-file", "-p", blob)
    return out if rc == 0 else ""


def main():
    r5_rev = sys.argv[1] if len(sys.argv) > 1 else "lane/ord0500-r5"
    b4, b5 = blob_of(R4), blob_of(r5_rev)
    rc_res, resolved = (_git(WT, "rev-parse", "HEAD") if r5_rev == "INDEX"
                        else _git(REPO, "rev-parse", r5_rev))
    out = {"tool": "css_delta_proof_r5", "took_local": datetime.now().astimezone().isoformat(),
           "path": PATH, "r4_rev": R4, "r5_rev_queried": r5_rev,
           "r5_side_meaning": ("the staged blob of this worktree; the branch head at query time was "
                               "this commit, so the commit that carries the blob is a later one"
                               if r5_rev == "INDEX" else "blob as that commit stores it"),
           "r5_rev_resolved": resolved if rc_res == 0 else "UNRESOLVABLE",
           "blob_r4": b4, "blob_r5": b5,
           "blob_r4_resolvable": re.fullmatch(r"[0-9a-f]{40}", b4) is not None
                                 and _git(REPO, "cat-file", "-e", b4)[0] == 0,
           "blob_r5_resolvable": re.fullmatch(r"[0-9a-f]{40}", b5) is not None
                                 and (re.fullmatch(r"[0-9a-f]{40}", b5) is not None
                                      and _git(REPO, "cat-file", "-e", b5)[0] == 0)}
    t4, t5 = text_of(b4), text_of(b5)
    assert t5, "NO_R5_TEXT: blob %s unreadable -- the comparison cannot be made vacuously" % b5
    l4, l5 = t4.splitlines(), t5.splitlines()
    diff = list(difflib.unified_diff(l4, l5, lineterm="", n=0))
    added = [x for x in diff if x.startswith("+") and not x.startswith("+++")]
    removed = [x for x in diff if x.startswith("-") and not x.startswith("---")]
    out["lines"] = {"r4": len(l4), "r5": len(l5), "added": len(added), "removed": len(removed)}
    out["changed_lines_preview"] = [x[:110] for x in (removed + added)][:24]
    # every removed line must be prose inside my own ORD-0500 comment, never a selector or a rule
    selectorish = [x for x in removed if re.match(r"^-\s*[.#@:a-zA-Z\[]", x.strip("- \t"))
                   and not x.strip("- \t").startswith("*")]
    out["removed_are_prose_only"] = {"count_removed": len(removed),
                                     "removed_that_look_like_rules": len(selectorish),
                                     "clean": len(selectorish) == 0,
                                     "examples": selectorish[:6]}
    day4 = [x for x in l4 if "cn-footprints__day" in x]
    day5 = [x for x in l5 if "cn-footprints__day" in x]
    out["ord0530_section"] = {"day_class_lines_r4": len(day4), "day_class_lines_r5": len(day5),
                              "identical": day4 == day5,
                              "day_class_occurrences_r5": len(re.findall("cn-footprints__day", t5))}
    out["own_block"] = {"markers_r5": len(re.findall(r"/\* ORD-0500", t5)),
                        "stop_checkin_rules_r5": len(re.findall(r"\.cn-stop-checkin", t5))}
    m = re.search(r"(\d+) of the 6 stop controls", t5)
    out["sentence_claims_n_of_6"] = m.group(1) if m else None
    out["stale_all_six_phrase_present"] = "all six stops answer" in t5
    path = os.path.join(LANE, "evidence", "css_delta_proof_r5.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE " + path)
    return 0 if out["ord0530_section"]["identical"] and out["sentence_claims_n_of_6"] else 1


if __name__ == "__main__":
    sys.exit(main())
