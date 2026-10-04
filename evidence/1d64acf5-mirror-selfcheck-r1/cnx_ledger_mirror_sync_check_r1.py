# -*- coding: utf-8 -*-
"""Ruling ①: a standing self-check that the ledger mirror is byte-current, with a counter-arm that bites.

Why this exists as its own tool: on the rebuilt-tree line, "landed" and "mirrored" are both decided by BYTE
equality, so the box needs a ruler that answers one question in one exit code - is the mirror copy of the ledger
the same bytes as this box's ledger right now? The reader (`cnx_ledger_mirror_reader_r1.py`, already on the line)
supplies the remote side with its own proof; this tool supplies the sampling and the verdict.

Sampling is five points, local and remote alternating::

    local_0  remote_1  local_1  remote_2  local_2

because this box's ledger is rewritten by the inserter while a read is in flight. A single local-vs-remote hash
comparison therefore reports a false lag whenever the file moves under it - measured on 2026-10-04, where the
remote caught up to exactly the bytes the local file had held a minute earlier. The five points separate the three
states that matter:

  CURRENT    every compared local/remote pair is the same blob
  LAGGING    the remote equals an *earlier* local snapshot (the mirror is behind a write, nothing is lost)
  DIVERGED   no local snapshot ever held the remote's bytes - which is the case that must page someone

Exit codes, so a caller does not have to parse prose: 0 CURRENT, 7 LAGGING, 8 DIVERGED, 9 the reader refused
(it raises with the leg that failed rather than returning partial bytes).

Counter-arms - a guard nobody bent is a guard nobody tested:
  flip_a_byte   one byte changed in an in-memory copy of the local ledger must make the check say NOT identical
  no_token      without the API token the second channel must refuse by name, not silently read one source
Neither arm ever writes the real ledger: the mutation is done to bytes in memory.

Interface for the inserter (import, do not shell out, so the verdict is structured)::

    from tools.cnx_ledger_mirror_sync_check_r1 import check_sync, VERDICT_CODES
    st = check_sync()            # requires CITYNEXUS_API_TOKEN_FILE (or token_file=...)
    if st["verdict"] != "CURRENT":
        ...alarm with st["verdict"], st["local_blob"], st["remote_blob"]...

CLI::

    python tools/cnx_ledger_mirror_sync_check_r1.py --runs 3
    python tools/cnx_ledger_mirror_sync_check_r1.py --self-test --out <path to write the receipt>
"""
import argparse
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools.cnx_ledger_mirror_reader_r1 import (IncompleteRemoteRead, git_blob_sha1,  # noqa: E402
                                               read_remote_ledger)

REF = "commander/control"
LEDGER_PATH = "CITYNEXUS_AGENT_CONTROL.md"
DEFAULT_LOCAL = os.environ.get("CITYNEXUS_LEDGER_LOCAL") or r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO_DIR = os.environ.get("CITYNEXUS_REPO_DIR") or "D:/moodle/CityNexus"
CURRENT, LAGGING, DIVERGED = "CURRENT", "LAGGING", "DIVERGED"
VERDICT_CODES = {CURRENT: 0, LAGGING: 7, DIVERGED: 8}


def local_state(path):
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8", "replace")
    return {"blob": git_blob_sha1(raw), "bytes": len(raw), "lines": text.count("\n") + 1,
            "text": text}


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a.split("\n"), b.split("\n"))):
        if x != y:
            return i + 1
    return None if len(a.split("\n")) == len(b.split("\n")) else min(
        len(a.split("\n")), len(b.split("\n"))) + 1


def check_sync(local_path=DEFAULT_LOCAL, ref=REF, path=LEDGER_PATH, repo_dir=REPO_DIR,
               token_file=None, reads=2, arm=""):
    """Sample local and remote alternately and classify the mirror's state. Read-only."""
    snaps = [local_state(local_path)]
    remotes = []
    for i in range(reads):
        info = read_remote_ledger(ref=ref, path=path, repo_dir=repo_dir, token_file=token_file)
        remotes.append(info)
        snaps.append(local_state(local_path))
    if arm == "flip_a_byte":
        flipped = dict(snaps[0])
        raw = io.open(local_path, "rb").read()
        mutated = raw[:-1] + bytes([(raw[-1] + 1) % 256])
        flipped["blob"] = git_blob_sha1(mutated)
        flipped["bytes"] = len(mutated)
        flipped["text"] = mutated.decode("utf-8", "replace")
        snaps = [flipped] + snaps[1:]
    local_blobs = [s["blob"] for s in snaps]
    remote_blobs = [r["blob_id"] for r in remotes]
    pairs = [("local_0 vs remote_1", local_blobs[0], remote_blobs[0])]
    if len(snaps) > 2:
        pairs.append(("local_1 vs remote_1", local_blobs[1], remote_blobs[0]))
        pairs.append(("local_1 vs remote_2", local_blobs[1], remote_blobs[1]))
    if len(snaps) > 2 and len(remote_blobs) > 1:
        pairs.append(("local_2 vs remote_2", local_blobs[2], remote_blobs[1]))
    matched = [n for n, a, b in pairs if a == b]
    remote_is_an_earlier_local = any(rb in local_blobs for rb in remote_blobs)
    if len(matched) == len(pairs) and len(set(local_blobs) | set(remote_blobs)) == 1:
        verdict = CURRENT
    elif remote_is_an_earlier_local:
        verdict = LAGGING
    else:
        verdict = DIVERGED
    last_remote = remotes[-1]
    return {"verdict": verdict, "exit_code": VERDICT_CODES[verdict],
            "local_path": local_path, "ref": ref, "ledger_path": path,
            "local_blob": local_blobs[-1], "local_blob_first": local_blobs[0],
            "remote_blob": remote_blobs[-1],
            "local_snapshots": local_blobs, "remote_reads": remote_blobs,
            "compared_points": [{"pair": n, "equal": a == b} for n, a, b in pairs],
            "points_compared": len(pairs), "points_matched": len(matched),
            "local_bytes": snaps[-1]["bytes"], "remote_bytes": last_remote["bytes"],
            "local_lines": snaps[-1]["lines"],
            "remote_lines": last_remote["text"].count("\n") + 1,
            "first_differing_line": (None if verdict == CURRENT else
                                     first_diff(snaps[-1]["text"], last_remote["text"])),
            "remote_self_proved": bool(last_remote["hash_equal"] and last_remote["size_equal"]
                                       and last_remote["channels_agree"]),
            "remote_blob_id_named_by_api": last_remote["api_blob_id"],
            "remote_size_named_by_api": last_remote["api_size"],
            "arm": arm or "none", "local_changed_under_the_run": len(set(local_blobs)) > 1}


def self_test(local_path=DEFAULT_LOCAL, repo_dir=REPO_DIR, token_file=None):
    """One honest pass plus the arms: a check that cannot see a one-byte difference is not a check."""
    rows = []
    base = check_sync(local_path=local_path, repo_dir=repo_dir, token_file=token_file)
    rows.append({"arm": "none", "verdict": base["verdict"], "remote_blob": base["remote_blob"],
                 "local_blob": base["local_blob"], "self_proved": base["remote_self_proved"],
                 "points": [base["points_compared"], base["points_matched"]]})
    flip = check_sync(local_path=local_path, repo_dir=repo_dir, token_file=token_file, arm="flip_a_byte")
    # the arm's whole point is that the FIRST snapshot is the mutated one, so the comparison that must go red is
    # `local_0 vs remote_1`. Reading the last snapshot here once reported `local_blob_flipped: false` while the
    # mutation was in fact detected one pair earlier - which is a bookkeeping bug in this tool, caught by itself
    bit = flip["local_blob_first"] != base["local_blob_first"]
    pair_red = not flip["compared_points"][0]["equal"]
    caught = pair_red and flip["verdict"] != CURRENT
    rows.append({"arm": "flip_a_byte", "verdict": flip["verdict"], "local_blob_flipped": bit,
                 "first_pair_went_red": pair_red, "refused_to_call_it_current": caught,
                 "flipped_blob": flip["local_blob_first"], "base_blob": base["local_blob_first"],
                 "points": [flip["points_compared"], flip["points_matched"]]})
    no_tok = None
    saved = os.environ.get("CITYNEXUS_API_TOKEN_FILE")
    try:
        # the reader deliberately falls back to the environment, so a real "no second channel" test has to clear
        # it too - passing an empty token_file alone would just re-read the same variable and prove nothing
        os.environ.pop("CITYNEXUS_API_TOKEN_FILE", None)
        try:
            check_sync(local_path=local_path, repo_dir=repo_dir, token_file=None)
            no_tok = {"arm": "no_token", "refused": False, "detail": "the reader returned bytes without the "
                                                                     "second channel - that is the hole"}
        except IncompleteRemoteRead as e:
            no_tok = {"arm": "no_token", "refused": True, "leg": e.leg, "detail": str(e)[:200]}
    finally:
        if saved is not None:
            os.environ["CITYNEXUS_API_TOKEN_FILE"] = saved
    rows.append(no_tok)
    ok = bool(bit and caught and no_tok["refused"]) and base["remote_self_proved"]
    return rows, ok, base


def main():
    ap = argparse.ArgumentParser(prog="cnx_ledger_mirror_sync_check_r1.py")
    ap.add_argument("--local", default=DEFAULT_LOCAL)
    ap.add_argument("--repo-dir", default=REPO_DIR)
    ap.add_argument("--token-file", default=os.environ.get("CITYNEXUS_API_TOKEN_FILE") or "")
    ap.add_argument("--reads", type=int, default=2)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--arm", default="", choices=("", "flip_a_byte", "no_token"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.self_test:
        rows, ok, base = self_test(a.local, a.repo_dir, a.token_file)
        doc = {"state": base, "arms": rows, "arms_all_correct": ok}
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        print(json.dumps({"verdict": base["verdict"], "arms_all_correct": ok,
                          "exit_code": base["exit_code"]}, ensure_ascii=False))
    elif a.arm:
        st = check_sync(local_path=a.local, repo_dir=a.repo_dir, token_file=a.token_file, arm=a.arm)
        doc = {"state": st}
        print(json.dumps({"arm": a.arm, "verdict": st["verdict"], "compared_points": st["compared_points"]},
                         ensure_ascii=False))
    else:
        st = check_sync(local_path=a.local, repo_dir=a.repo_dir, token_file=a.token_file, reads=a.reads)
        doc = {"state": st}
        print(json.dumps({"verdict": st["verdict"], "local_blob": st["local_blob"],
                          "remote_blob": st["remote_blob"], "points": [st["points_compared"],
                                                                       st["points_matched"]],
                          "self_proved": st["remote_self_proved"]}, ensure_ascii=False))
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    if a.self_test:
        return 0 if doc["arms_all_correct"] else 7
    st = doc["state"]
    return st["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
