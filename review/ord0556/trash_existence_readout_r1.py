"""Leg-six supporting readout: does /v8/trash exist at the live tip at all?

The screen reading (review/ord0556/readouts/trash_reach_*.json) was taken against THIS LANE's tree.
Before that can be reported as a fact about the product it has to be pinned which generation owns the
route. Three tips are measured with identical patterns in one run: the live tip read now from the
remote, the older sweep base named in my applied blocks, and this lane's own branch tip.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/review/ord0556/readouts")
OUT = DATA / "trash_existence_readout_r1.json"

ENV = {"GIT_SSH_COMMAND": "ssh -p 443 -o StrictHostKeyChecking=no", "PATH": __import__("os").environ["PATH"],
       "HOME": __import__("os").environ.get("HOME", ""), "NO_PROXY": "*"}


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**__import__("os").environ,
                                                               "NO_PROXY": "*", "HTTP_PROXY": "",
                                                               "HTTPS_PROXY": ""})
    return (r.stdout or "") + (r.stderr or "")


live = git("ls-remote", "origin", "HEAD").split()[0]
older = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"
mine = git("rev-parse", "HEAD").strip()

PAT = re.compile(r"trash|recycle", re.I)
out = {"live_tip_from_ls_remote": live, "older_sweep_base": older, "lane_branch_tip": mine, "tips": {}}
for label, ref in (("live_tip", live), ("older_sweep_base", older), ("lane_branch_tip", mine)):
    # `ls-tree -r --name-only` prints the path ALONE, with no mode/type/sha columns, so the first
    # version of this line (`split("\t")` guarded by `"\t" in ln`) matched nothing and reported
    # paths_total = 0 for all three tips -- a false "no trash paths" that looked like a finding.
    paths = [ln for ln in git("ls-tree", "-r", "--name-only", ref).splitlines() if ln.strip()]
    hits = sorted(p for p in paths if PAT.search(p))
    route_blob = git("rev-parse", f"{ref}:frontend/src/routes/v8Routes.ts").strip()
    route_src = git("show", f"{ref}:frontend/src/routes/v8Routes.ts")
    keys = sorted(set(re.findall(r'key: "([a-z]+)"', route_src)))
    css = git("show", f"{ref}:frontend/src/styles.css")
    kicker_rule = next((ln for ln in css.splitlines() if ".v8-kicker {" in ln), "")
    transform = bool(re.search(r"\.v8-kicker\b[^}]*text-transform:\s*uppercase", kicker_rule))
    out["tips"][label] = {
        "ref": ref,
        "paths_total": len(paths),
        "trash_named_paths": len(hits),
        "trash_named_sample": hits[:4],
        "v8Routes_blob": route_blob,
        "route_keys": keys,
        "route_keys_count": len(keys),
        "trash_is_a_route": "trash" in keys,
        "kicker_rule_has_uppercase": transform,
    }

tip_keys = set(out["tips"]["live_tip"]["route_keys"])
lane_keys = set(out["tips"]["lane_branch_tip"]["route_keys"])
out["route_key_sets"] = {"on_live_tip": sorted(tip_keys), "on_lane_tree": sorted(lane_keys),
                         "only_on_lane_tree": sorted(lane_keys - tip_keys),
                         "only_on_live_tip": sorted(tip_keys - lane_keys)}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
for label, t in out["tips"].items():
    print(f"{label} paths={t['paths_total']} trash_named={t['trash_named_paths']} "
          f"route_keys={t['route_keys_count']} trash_route={t['trash_is_a_route']} "
          f"css_upper={t['kicker_rule_has_uppercase']} blob={t['v8Routes_blob'][:12]}")
print("only_on_lane_tree=" + ",".join(out["route_key_sets"]["only_on_lane_tree"]))
print("only_on_live_tip=" + (",".join(out["route_key_sets"]["only_on_live_tip"]) or "NONE"))
print("written " + OUT.name)
