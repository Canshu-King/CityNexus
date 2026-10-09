"""Landing-preparation reading for D's ORD-0310 candidate, computed by the commander, not relayed.

Her post asks one question ("要不要在当代尖重跑，请落字") and carries three coordinates that had already
drifted (two merge-tree predictions computed against an older object of her own ref).  Before I answer on
the bus I recompute everything myself and publish it, so every number in my reply has a durable
coordinate instead of my prose.

Read-only against the repo: no ref is written, no branch is moved, nothing is pushed from here.
"""
import hashlib
import io
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-landing-prep", "X-GitHub-Api-Version": "2022-11-28"}
REPO = "D:/moodle/CityNexus"
LINE = "mirror/integration-frontend-apple-pass1"
CAND_REF = "review/ord0310-keyless-deadline-d"
FORK = "5aff3722d5c36c760a424f5fea5c3a771298f9ac"
CAND_COMMITS_CITED = {"b44a771": "her second post's merge-tree arg",
                      "efd67d82c1acc68dcea0f683307e00bc029e25cc": "prediction in issuecomment-5832195554",
                      "7b7a3f0b834c2801e5be5a1de30c1ce29e0ffda5": "prediction in her 20:22 lane reply"}
HER_BLOBS_CITED = {"frontend/src/lib/keylessWriteDeadline.ts": "1aea861b887273f70ec6cf726369c36a1398786e",
                   "frontend/src/features/planning/PlanWithAiSheet.tsx": "3bb6a39067a380c2f75629fd7562f0de8f5d2f2a"}


def gh(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def blob_of_file_at(rev, path):
    rc, out, _ = git("rev-parse", "%s:%s" % (rev, path))
    return out.strip() if rc == 0 else None


def main():
    tip = gh("/repos/Canshu-King/CityNexus/git/ref/heads/" + urllib.parse.quote(LINE, safe=""))["object"]["sha"]
    cand = gh("/repos/Canshu-King/CityNexus/git/ref/heads/" + urllib.parse.quote(CAND_REF, safe=""))["object"]["sha"]
    rc_ff, _, _ = git("merge-base", "--is-ancestor", tip, cand)
    rc_lr, lr_out, _ = git("rev-list", "--left-right", "--count", "%s...%s" % (tip, cand))
    behind, ahead = [int(x) for x in lr_out.split()]
    rc_mt, mt_out, mt_err = git("merge-tree", "--write-tree", tip, cand)
    lines = [l for l in mt_out.splitlines() if l.strip()]
    predicted = lines[0] if lines else None
    conflict_section = "\n".join(lines[1:]) if len(lines) > 1 else ""
    rc_f, line_files, _ = git("diff", "--name-only", FORK, tip)
    rc_c, cand_files, _ = git("diff", "--name-only", FORK, cand)
    lf = sorted(x for x in line_files.splitlines() if x.strip())
    cf = sorted(x for x in cand_files.splitlines() if x.strip())
    inter = sorted(set(lf) & set(cf))
    blob_check = {p: {"she_cited": want, "at_candidate_tip": blob_of_file_at(cand, p),
                      "agree": blob_of_file_at(cand, p) == want} for p, want in HER_BLOBS_CITED.items()}
    rc_log, log_out, _ = git("log", "--oneline", "%s..%s" % (FORK, cand))
    out = {
        "schema": "CNX_CMDR_LANDING_PREP_V1",
        "lane": "commander 494abfd7",
        "generated_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "every coordinate behind the answer to D's ORD-0310 question, recomputed from the remote refs",
        "authoritative_line": LINE,
        "tip_re_read_from_github": tip,
        "candidate_ref": CAND_REF,
        "candidate_tip_re_read_from_github": cand,
        "fork_point_used_for_both_sides": FORK,
        "ff_possible": rc_ff == 0,
        "merge_base_is_ancestor_rc": rc_ff,
        "line_side_commits_missing_from_candidate": behind,
        "candidate_commits_missing_from_line": ahead,
        "candidate_commits": [l for l in log_out.splitlines() if l.strip()],
        "merge_tree": {"exit_code": rc_mt, "predicted_tree": predicted,
                       "conflict_section_empty": conflict_section.strip() == "",
                       "conflict_section_head": conflict_section[:300],
                       "stderr_head": (mt_err or "")[:200]},
        "her_predictions_as_cited": CAND_COMMITS_CITED,
        "file_sets": {"line_side_count": len(lf), "candidate_side_count": len(cf),
                      "intersection_count": len(inter), "intersection": inter,
                      "line_side": lf, "candidate_side": cf},
        "her_cited_blobs_recomputed_at_candidate_tip": blob_check,
        "decision_this_supports": "甲 (she re-parents onto the tip I re-read here; I land ff-only) plus a "
                                  "commander-side freeze of the authoritative line until that landing, because "
                                  "ff is impossible right now (merge-base rc=1) and a non-ff write by me would "
                                  "break AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1 as I have been applying it.",
        "discipline": {"authoritative_branch_moved": 0, "refs_pushed": 0, "product_bytes_changed": 0,
                       "demo_reset_calls": 0, "live_or_preview_db_reads_or_writes": 0,
                       "credential_values_printed": 0, "git_write_operations_run": 0},
        "claim_kind": "git_determined",
        "claimed_result": "candidate is 6 ahead / 5 behind, merges clean into the current tip, no product file collides",
        "derived_result": None,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_landing_prep_0310.json", "w", encoding="utf-8", newline="\n").write(txt)
    raw = io.open("_cmdr_landing_prep_0310.json", "rb").read()
    print("tip=%s cand=%s ff=%s behind=%d ahead=%d" % (tip[:8], cand[:8], out["ff_possible"], behind, ahead))
    print("merge-tree rc=%d predicted=%s conflict_empty=%s" % (rc_mt, predicted,
                                                                out["merge_tree"]["conflict_section_empty"]))
    print("files line=%d cand=%d intersection=%d %s" % (len(lf), len(cf), len(inter), inter))
    print("her blobs agree: %s" % json.dumps({k: v["agree"] for k, v in blob_check.items()}))
    print("bytes_on_disk=%d blob=%s" % (len(raw), hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
