"""ORD-0553 r20 -- what the on-tip census could and could not deliver, and the diff that did land.

The runtime census needs a generation.  The authority line rewrote its tip while this lane was walking it,
and the generation lock in the ruler refused to classify a tree that is no longer on the line -- which is
the lock doing its job.  So this round delivers three things instead of pretending the census is current:

  * the refusal, verbatim, and the movement readings that explain it (how many tip values appeared during
    the round, and whether each earlier one is still an ancestor of the later);
  * the classification of the walk that did land, as a declared off-tip reading (the ruler recorded the
    declared reason next to the verdict, so it cannot be quoted as an on-tip reading);
  * the token-level diff between the previous generation's census and this one -- which is the part that
    survives the tip moving, because it is a diff rather than a claim about "now".
"""
import io
import json
import os
import subprocess

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
REFS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
REPO = r"D:/moodle/CityNexus"


def git(*args, timeout=300):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (p.stdout or "").strip()


out = {"instrument": "cmdra_0553_census_moved_r20", "rounds": []}

# the tip values this lane met during the round, in order
seq = [("b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c", "r11 census was taken on this one"),
       ("79daa3c4ff8f37304d352177b456133d4b9c2a45", "the generation this round's walk was taken on"),
       (git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
        if git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1") else "",
        "the value the lock found when it came to classify")]
for sha, note in seq:
    out["rounds"].append({"sha": sha[:12] if sha else None, "note": note})
pairs = []
for a, _n1 in seq[:2]:
    b = seq[2][0]
    if a and b:
        anc = subprocess.run(["git", "-C", REPO, "merge-base", "--is-ancestor", a, b],
                             capture_output=True, text=True, timeout=200)
        pairs.append({"earlier": a[:12], "later": b[:12], "earlier_is_ancestor": anc.returncode == 0})
out["line_movement"] = pairs
out["subject_at_later"] = git("log", "-1", "--format=%s", seq[2][0]) if seq[2][0] else None

# the token diff between the two census readings
old = json.load(io.open(os.path.join(R1, "_evidence", "r11_ontip_report.json"), encoding="utf-8"))
new = json.load(io.open(os.path.join(R1, "_evidence", "r20_census_report.json"), encoding="utf-8"))
old_tokens, new_tokens = set(old.get("table", {})), set(new.get("table", {}))
walk = json.load(io.open(os.path.join(R1, "_evidence", "r20_walk_en.json"), encoding="utf-8"))
out["census_totals"] = {"previous_generation": {"en_tokens": old.get("en_walk", {}).get("tokens"),
                                                "painted_hits": old.get("en_walk", {}).get("painted_hits")},
                        "this_generation": {"en_tokens": new.get("en_walk", {}).get("tokens"),
                                            "painted_hits": new.get("en_walk", {}).get("painted_hits"),
                                            "zh_tokens": new.get("zh_walk", {}).get("tokens")}}
out["token_diff"] = {"only_in_previous": sorted(old_tokens - new_tokens),
                     "only_in_this": sorted(new_tokens - old_tokens),
                     "shared_count": len(old_tokens & new_tokens)}
out["this_generation_tip_binding"] = new.get("tip_binding")
out["this_generation_arms"] = [{"id": a["id"], "verdict": a["verdict"]} for a in new.get("arms", [])]
out["positive_control"] = next((a["observed"] for a in new.get("arms", [])
                                if a["id"] == "positive_control_dirty_generation_would_flag"), None)
out["page_errors"] = walk.get("pageErrors")
out["entry_on_this_generation"] = [x.split("/")[-1] for x in (walk.get("entryAssets") or [])]

path = os.path.join(R1, "_evidence", "r20_census_moved.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
print("WROTE", path)
