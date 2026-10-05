"""Print the numbers the BB copy of the fleet re-scan hand claims, straight off the published artifacts.

The hub refuses a post whose body carries a number that no evidence output contains, so this printer is
the evidence: it re-reads the side ref's blobs from git and prints key=value.  It also refuses to print
a line the block does not need and, more importantly, refuses to let the block quote a number that this
printer cannot vouch for -- which is the difference between "the hub would probably take it" and "I ran
the check the hub runs".
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BLOCK = os.path.join(LANE, "run", "fleet_r2_block_composed.md")
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
REF = "refs/heads/review/0afdb49b-fleet-rescan-r2"
SUB = "review/fleet-rescan-r2"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def _bus():
    """Borrow the hub's own 'which numbers need a source' function.  Reimplementing it is how a lane
    ends up with a private rule that the write door does not share: a bare 40-hex inside backticks is a
    digit run as far as the hub is concerned (NUM_RE does not know about hex), so a hand-written
    approximation either over- or under-vouches and the post dies at the hub instead of here."""
    spec = importlib.util.spec_from_file_location("cnx_bus_client", r"D:/moodle/agent_bus/bus.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.numeric_claims


def git(*args):
    q = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, timeout=600, env=ENV)
    return q.returncode, q.stdout.decode("utf-8", "replace")


def published_head():
    """The side ref lives on the remote: this lane pushes with `<commit>:<ref>` and never creates a
    local tracking ref, so `git ls-tree refs/heads/review/…` answers 'not a valid object name'.  Ask
    the remote where the ref is, then read the object -- which is also the coordinate the block quotes.
    """
    rc, out = git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_NOT_ON_REMOTE " + REF)
    return out.split()[0]


def blob(name, at):
    rc, out = git("ls-tree", "-r", "--format=%(objectname) %(path)", at)
    if rc:
        raise SystemExit("ABORT_LS_TREE rc=%d %s" % (rc, out[:120]))
    for line in out.splitlines():
        sha, path = line.split(" ", 1)
        if path.endswith("/" + name):
            rc, data = git("cat-file", "blob", sha)
            if rc:
                raise SystemExit("ABORT_BLOB_UNREADABLE " + name)
            return data
    raise SystemExit("ABORT_NAME_NOT_ON_REF " + name)


def this_generation_title():
    """The ledger title of the block this generation delivered -- the receipt is found by that title,
    not by a remembered HHMM that would go stale the moment the applier moves the file."""
    return open(BLOCK, encoding="utf-8").read().splitlines()[0].strip()


def main():
    inject = None
    args = sys.argv[1:]
    bb_body = None
    while args:
        if args[0] == "--negative-control":
            inject = args[1]; args = args[2:]
        elif args[0] == "--write-body":
            # render the BB copy from THIS key/value map and vouch those bytes: hand-typing the same
            # numbers into a second artifact is how the two drift apart
            bb_body = args[1]; args = args[2:]
        else:
            raise SystemExit("ABORT_UNKNOWN_ARG " + args[0])
    text = open(BLOCK, encoding="utf-8").read()
    head = published_head()
    s = json.loads(blob("fleet_rescan_r2_summary_r2.json", head))
    d = json.loads(blob("label_delta_r2.json", head))
    a = json.loads(blob("fleet_rescan_arms_r2.json", head))
    ct = s["class_tally"]
    rc, pars = git("rev-list", "--parents", "--no-walk", head)
    parent = pars.split()[1]
    rc, names = git("diff", "--name-only", "%s..%s" % (parent, head))
    touched = len([l for l in names.splitlines() if l.strip()])
    rc, live = git("ls-remote", "--refs", "origin", TIP_REF)
    tip = live.split()[0]
    roster_raw = blob("fleet_rescan_r2_roster_r2.tsv", head).splitlines()
    roster = [l for l in roster_raw if l.strip() and not l.startswith("#")]
    kv = {
        "tip": tip, "published_ref": REF, "published_ref_head": head, "published_parent": parent,
        "tip_tree_paths": s["tip_tree_paths"], "review_refs": s["review_refs"],
        "distinct_heads": s["distinct_review_heads"], "refs_sharing_a_head": s["refs_sharing_a_head"],
        "heads_unresolvable_locally": s["heads_unresolvable_locally"],
        "heads_quiet_in_batch": s["heads_quiet_in_batch"], "heads_empty_commit": s["heads_empty_commit"],
        "HELD": ct["HELD"], "MIXED": ct["MIXED"], "ALL_DIFFERENT_ON_LINE": ct["ALL_DIFFERENT_ON_LINE"],
        "ALL_NOT_ON_LINE": ct["ALL_NOT_ON_LINE"], "SNAPSHOT_SHAPED": ct["SNAPSHOT_SHAPED"],
        "NONE_HELD_SPLIT": ct["NONE_HELD_SPLIT"], "ALL_DELETIONS_HELD": ct["ALL_DELETIONS_HELD"],
        "EMPTY_COMMIT": ct["EMPTY_COMMIT"], "tally_sum": sum(ct.values()),
        "candidate_hands_judged": s["candidate_hands_judged"],
        "candidate_paths_total": s["candidate_paths_total"], "candidate_same": s["candidate_same"],
        "candidate_absent": s["candidate_absent"], "candidate_changed": s["candidate_changed"],
        "candidate_deletion_undone": s["candidate_deletion_undone"],
        "snapshot_shaped_paths_total": s["snapshot_shaped_paths_total"],
        "labels_changed": d["labels_changed"], "refs_compared": d["refs_compared"],
        "count_moves_rows": d["rows_with_per_path_counts_moved"],
        "unattributed_count_moves": d["unattributed_count_moves"],
        "head_moves": len(d["head_moves"]),
        "arms_count": len(a["arms"]), "every_arm_bit": a["every_arm_bit"],
        "published_paths": touched, "roster_data_rows": len(roster),
        "roster_header_rows": len([l for l in roster_raw if l.startswith("#")]),
        "roster_bytes": len(blob("fleet_rescan_r2_roster_r2.tsv", head).encode("utf-8")),
        "summary_bytes": len(blob("fleet_rescan_r2_summary_r2.json", head).encode("utf-8")),
        "full_json_bytes": os.path.getsize(os.path.join(LANE, "evidence", "fleet_rescan_r2",
                                                        "fleet_rescan_r2.json")),
        "block_bytes": os.path.getsize(BLOCK),
    }
    # the block quotes published blobs by 40-hex, and the hub's NUM_RE has no idea a hex is a
    # coordinate -- `951610708048d547…` reads to it as the number 951610708048.  So every blob this
    # ref carries is printed here, which is also the honest statement of what the block cites.
    rc, listing = git("ls-tree", "-r", "--format=%(objectname) %(path)", head)
    for line in sorted(l for l in listing.splitlines()):
        sha, path = line.split(" ", 1)
        if path.startswith(SUB + "/"):
            kv["blob_" + os.path.basename(path)] = sha
    drop = [f for f in os.listdir(os.path.join(INBOX, "_processed"))
            if f.startswith("0afdb49b_0108")]
    kv["prior_erratum_receipt"] = drop[0] if drop else "NOT_FOUND"
    # the hub's NUM_RE does not know a filename from a number: `…_0351.md.inserted_035934` leaves
    # 0351 and 035934 as claims, so the receipt naming this very delivery is part of the evidence.
    booked = [f for f in os.listdir(os.path.join(INBOX, "_processed"))
              if f.startswith("0afdb49b_") and ".md" in f
              and open(os.path.join(INBOX, "_processed", f), encoding="utf-8",
                       errors="replace").readline().strip() == this_generation_title()]
    if len(booked) != 1:
        raise SystemExit("ABORT_DELIVERY_RECEIPT %d booked for this generation: %s" % (
            len(booked), json.dumps(booked[:4], ensure_ascii=False)))
    kv["inbox_receipt"] = booked[0]
    kv["published_sub"] = SUB
    kv["title_tail"] = this_generation_title()
    for p in d["changed_pairs"]:
        kv["pair_%s_to_%s" % (p["from"], p["to"])] = p["refs"]
    top = max(d["changed_pairs"], key=lambda p: p["refs"])
    kv["top_pair"] = "%s->%s" % (top["from"], top["to"])
    kv["top_pair_refs"] = top["refs"]
    for k, v in d["count_move_causes"].items():
        kv["cause_" + k] = v
    # a quoted 40-hex can still read as a number to the hub: NUM_RE has no notion of hex, so the
    # leading digit run of `5971231736e175…` is a claim that needs a source.  The head-move refs the
    # block names are printed here for exactly that reason.
    for i, hm in enumerate(d["head_moves"]):
        kv["head_move_r1_head_%d" % i] = hm["r1_head"]
        kv["head_move_r2_head_%d" % i] = hm["r2_head"]
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    hay = line.replace(",", "")

    bodies = [("ledger block", BLOCK, text)]
    if bb_body:
        closing = open(CLOSING, "rb").read()
        if len(closing) != 83:
            raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
        ctext = closing.decode("utf-8").strip()
        rendered = open(os.path.join(LANE, "run", "fleet_r2_bb_body.tpl"), encoding="utf-8").read()
        rendered = rendered.format(**kv).rstrip() + "\n\n" + ctext + "\n"
        if rendered.count(ctext) != 1:
            raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED %d" % rendered.count(ctext))
        # bus.py reads --body-file first and runs the evidence command afterwards, so this printer is
        # allowed to touch the file only if touching it cannot change what is already being posted.
        if os.path.exists(bb_body):
            cur = open(bb_body, encoding="utf-8").read()
            if cur != rendered:
                raise SystemExit("ABORT_WOULD_CHANGE_THE_POST -- the body on disk is not what this "
                                 "kv map renders; post nothing and re-render in one pass")
        open(bb_body, "w", encoding="utf-8", newline="\n").write(rendered)
        bodies.append(("bb copy", bb_body, rendered))
    ok = True
    for label, path, body in bodies:
        claimed = sorted(set(_bus()(body)))
        if inject:
            claimed = sorted(set(claimed) | {inject})
        missing = [t for t in claimed if t not in hay]
        if missing:
            ok = False
            print("%s NOT_VOUCHED %s (%d of %d) -- the hub would refuse this post" % (
                label, ",".join(missing[:12]), len(missing), len(claimed)))
        else:
            print("%s VOUCHED all %d number tokens appear in this output (%s)" % (
                label, len(claimed), path))
    print(line)
    if not ok:
        raise SystemExit("ABORT_BB_NOT_VOUCHED -- fix the body or extend the printer's kv map, "
                         "never hand-type a number past the check")


if __name__ == "__main__":
    main()
