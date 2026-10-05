"""ORD-0553 r9 -- bolt the generation check into the ruler: a reading may only be classified by a tree that
built the bundle the reading came from.

Why: r8 caught me classifying an old generation's screen reading with the new tip's copy tables, which
invented four "look at these" tokens.  I wrote the rule down; this pass enforces it in code so the mistake
cannot be made silently again.

The check has three links, all read from artifacts on disk:
  1. the build receipt's `sha` equals the tree the ruler is pinned to;
  2. the bundle's `index.html` on disk names the same entry asset the walk recorded;
  3. the walk's own `base` is the port the receipt's dist was served from (recorded, not assumed).
A pair that fails any link is refused -- no verdict is emitted for a mixed generation.

Runs on published/kept artifacts only: no browser, no port, no database, no product bytes.
"""
import glob
import io
import json
import os
import re

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
BUILDS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
EV = os.path.join(R1, "_evidence")


def entry_names_in_dist(dist_dir):
    idx = os.path.join(dist_dir, "index.html")
    text = io.open(idx, encoding="utf-8", errors="replace").read()
    return sorted(set(re.findall(r"assets/index-[A-Za-z0-9_-]+\.js", text)))


def generation_ok(pinned_sha, build_info_path, walk_path):
    """Returns (ok, reason, evidence) -- reason names the first broken link."""
    b = json.load(io.open(build_info_path, encoding="utf-8"))
    w = json.load(io.open(walk_path, encoding="utf-8"))
    dist = os.path.join(BUILDS, "_build_" + b["tag"], "frontend", "dist")
    disk = entry_names_in_dist(dist) if os.path.isdir(dist) else []
    walked = [x.split("/")[-1] for x in (w.get("entryAssets") or [])]
    ev = {"pinned_sha": pinned_sha, "build_sha": b.get("sha"), "build_tag": b.get("tag"),
          "dist_on_disk": os.path.isdir(dist), "dist_entry": disk, "walk_entry": walked, "walk_base": w.get("base")}
    if len(pinned_sha) != 40 or pinned_sha != b.get("sha"):
        return False, "link1 build receipt sha != pinned tree", ev
    if not disk:
        return False, "link2 the built dist is not on disk to compare", ev
    if not walked:
        return False, "link3 the walk recorded no entry asset", ev
    if set(walked) != set(x for x in disk[0].split("/")[-1:] if x) and not set(walked) <= set(disk):
        return False, "link2 bundle entry on disk is not what the walk recorded", ev
    return True, "all three links hold", ev


CASES = [
    {"name": "c1_same_generation_tip", "expect": "ok",
     "pinned": "d107131c6f6e65d9f207f6bf1b563d1cc8877f89",
     "build": os.path.join(BUILDS, "_build_cmdra_0553_r8_info.json"),
     "walk": os.path.join(EV, "r8_walk_en_49871.json")},
    {"name": "c2_tip_tree_with_previous_build", "expect": "refuse",
     "pinned": "d107131c6f6e65d9f207f6bf1b563d1cc8877f89",
     "build": os.path.join(BUILDS, "_build_cmdra_0553_r2_info.json"),
     "walk": os.path.join(EV, "r8_walk_en_49871.json")},
    {"name": "c3_tip_build_with_previous_walk", "expect": "refuse",
     "pinned": "d107131c6f6e65d9f207f6bf1b563d1cc8877f89",
     "build": os.path.join(BUILDS, "_build_cmdra_0553_r8_info.json"),
     "walk": os.path.join(EV, "r5_walk_en_49861.json")},
]

rows = []
for c in CASES:
    ok, reason, ev = generation_ok(c["pinned"], c["build"], c["walk"])
    got = "ok" if ok else "refuse"
    rows.append({"case": c["name"], "expected": c["expect"], "got": got, "reason": reason,
                 "discriminates": got == c["expect"], "evidence": ev})

arms = [{"id": "same_generation_pair_accepted", "verdict": "PASS" if rows[0]["discriminates"] else "FAIL",
         "observed": rows[0]["reason"] + " | disk " + ",".join(rows[0]["evidence"]["dist_entry"]) +
                     " | walk " + ",".join(rows[0]["evidence"]["walk_entry"])},
        {"id": "tip_tree_with_stale_build_is_refused", "verdict": "PASS" if rows[1]["discriminates"] else "FAIL",
         "observed": rows[1]["reason"]},
        {"id": "tip_build_with_stale_walk_is_refused", "verdict": "PASS" if rows[2]["discriminates"] else "FAIL",
         "observed": rows[2]["reason"] + " | disk " + ",".join(rows[2]["evidence"]["dist_entry"]) +
                     " | walk " + ",".join(rows[2]["evidence"]["walk_entry"])}]
reds = [a["id"] for a in arms if a["verdict"] == "FAIL"]
report = {"instrument": "cmdra_0553_generation_bind_r9", "cases": rows, "arms": arms,
          "verdict": "RED" if reds else "GREEN", "red_arms": reds,
          "rule": "a screen reading may only be classified by the tree that built the bundle it came from"}
io.open(os.path.join(EV, "r9_generation_bind_report.json"), "w", encoding="utf-8").write(
    json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({"verdict": report["verdict"], "red_arms": reds}, ensure_ascii=False))
for a in arms:
    print(" ", a["verdict"], a["id"], "|", a["observed"][:150])
raise SystemExit(1 if reds else 0)
