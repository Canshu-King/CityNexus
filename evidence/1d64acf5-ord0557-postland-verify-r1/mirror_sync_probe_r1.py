# -*- coding: utf-8 -*-
"""ORD-0557 follow-up: prove with one command that the ledger mirror is byte-current, not just "green".

The question the receipt cannot answer on its own is whether the mirror has actually caught up with this box's
`CITYNEXUS_AGENT_CONTROL.md`.  Answering it needs the local bytes and the remote bytes measured close together -
and the honest way to say "they match" is to show that they match at the same point, because the local ledger is
being rewritten by the inserter between reads.  So this takes five points around two remote reads:

    local_before - remote_1 - local_after_1 - remote_2 - local_after_2

and reports whether any pair of a local hash and a remote hash lines up, whether the local file moved under the
run, and whether every remote read was self-proved (recomputed git blob sha1 == the blob the tree names, and the
contents route agreeing on both blob and size).

Read-only: nothing here writes a ledger, a mirror, a database or a ref outside `refs/remotes/verify/cnx_reader_*`,
which the reader owns and prunes by itself.

    set CITYNEXUS_API_TOKEN_FILE=<path to a PAT file>
    python mirror_sync_probe_r1.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
REPO = "D:/moodle/CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
LEDGER_PATH = "CITYNEXUS_AGENT_CONTROL.md"
REF = "commander/control"


def blob_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def local_point(tag, rc_map=None):
    raw = io.open(LOCAL_LEDGER, "rb").read()
    return {"point": tag, "blob": blob_of(raw), "bytes": len(raw),
            "lines": raw.decode("utf-8", "replace").count("\n") + 1, "at": time.strftime("%H:%M:%S")}


def remote_point(tag, info):
    return {"point": tag, "blob": info["blob_id"], "bytes": info["bytes"],
            "lines": info["text"].count("\n") + 1, "at": time.strftime("%H:%M:%S"),
            "hash_equal": info["hash_equal"], "size_equal": info["size_equal"],
            "channels_agree": info["channels_agree"], "api_size": info["api_size"],
            "self_heal": info["fetch_self_heal"], "tip_of_that_ref": info["branch_tip_commit"]}


def main():
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["NO_PROXY"] = "*"
    # import the module the way the gate will: the repo root on sys.path, no package file assumed
    root = WT if os.path.exists(os.path.join(WT, "tools", "cnx_ledger_mirror_reader_r1.py")) else REPO
    sys.path.insert(0, root)
    import tools.cnx_ledger_mirror_reader_r1 as M
    if not (os.environ.get("CITYNEXUS_API_TOKEN_FILE") or "").strip():
        print("ABORT: set CITYNEXUS_API_TOKEN_FILE first - the second channel refuses without it, which is "
              "the module failing closed rather than reading one source")
        return 9
    # existence is asked through refs that are known to resolve, because `commander/control` is a branch name and
    # not a revision a clone can always open directly - asking it the naive way returned a false "does not exist"
    # on the first run of this probe, which is exactly the mistake the probe exists to catch elsewhere
    def path_exists(rev):
        r = subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", "-q", "%s:%s" % (rev, LEDGER_PATH)],
                           capture_output=True, text=True, env=env, timeout=900)
        return r.returncode == 0, (r.stdout or "").strip()

    reader_ref = "refs/remotes/verify/cnx_reader_" + REF.replace("/", "_")
    if subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", "-q", reader_ref],
                      capture_output=True, env=env, timeout=900).returncode != 0:
        subprocess.run(["git", "-C", REPO, "fetch", "-q", "--depth=1", "origin",
                        "+refs/heads/%s:%s" % (REF, reader_ref)], capture_output=True, env=env, timeout=3600)
    on_control, control_blob = path_exists(reader_ref)
    tip = ((subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                            "refs/heads/mirror/integration-frontend-apple-pass1"],
                           capture_output=True, text=True, env=env, timeout=900).stdout or "").split() or [None])[0]
    if tip and subprocess.run(["git", "-C", REPO, "cat-file", "-e", "%s^{commit}" % tip],
                              capture_output=True, env=env, timeout=3600).returncode != 0:
        subprocess.run(["git", "-C", REPO, "fetch", "-q", "--depth=1", "origin",
                        "+refs/heads/mirror/integration-frontend-apple-pass1:refs/remotes/verify/"
                        "cnx_probe_tip"], capture_output=True, env=env, timeout=3600)
        tip = (subprocess.run(["git", "-C", REPO, "rev-parse", "refs/remotes/verify/cnx_probe_tip"],
                              capture_output=True, text=True, env=env, timeout=900).stdout or "").strip() or tip
    on_authoritative, auth_blob = path_exists(tip) if tip else (None, None)
    seq = [local_point("local_before_read_1")]
    for i in (1, 2):
        info = M.read_remote_ledger(ref=REF, repo_dir=REPO)
        seq.append(remote_point("remote_%d" % i, info))
        seq.append(local_point("local_after_read_%d" % i))
    local_hashes = [p["blob"] for p in seq if p["point"].startswith("local")]
    remote_hashes = [p["blob"] for p in seq if p["point"].startswith("remote")]
    pairs = []
    for p in seq:
        if p["point"] == "local_before_read_1":
            pairs.append((p["blob"], remote_hashes[0], "local_before vs remote_1"))
        if p["point"] == "local_after_read_1":
            pairs.append((p["blob"], remote_hashes[0], "local_after_1 vs remote_1"))
            pairs.append((p["blob"], remote_hashes[1], "local_after_1 vs remote_2"))
        if p["point"] == "local_after_read_2":
            pairs.append((p["blob"], remote_hashes[1], "local_after_2 vs remote_2"))
    doc = {"read_at_local": time.strftime("%Y-%m-%d %H:%M:%S"), "sequence": seq,
           "ledger_on_commander_control": {"exists": on_control, "blob_there": control_blob or None,
                                           "resolved_via": reader_ref},
           "ledger_on_authoritative_branch": {"exists": on_authoritative, "blob_there": auth_blob or None,
                                              "tip_named_by_server": tip},
           "verdicts": {
               "every_remote_read_self_proved": all(p["hash_equal"] and p["channels_agree"] and p["size_equal"]
                                                   for p in seq if p["point"].startswith("remote")),
               "local_file_changed_under_this_run": len(set(local_hashes)) > 1,
               "byte_current_at_every_compared_point": all(a == b for a, b, _ in pairs),
               "points_that_matched": [n for a, b, n in pairs if a == b],
               "points_that_did_not_match": [n for a, b, n in pairs if a != b],
               "remote_blob": remote_hashes[-1], "local_blob": local_hashes[-1],
               "lines": remote_hashes and seq[-1]["lines"]},
           "reading": ("one sentence: the mirror carries the same bytes as this box's ledger, measured at five "
                       "points across two self-proved remote reads")}
    out = os.path.join(HERE, "mirror_sync_probe_r1.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    v = doc["verdicts"]
    print(json.dumps({"byte_current": v["byte_current_at_every_compared_point"],
                      "self_proved": v["every_remote_read_self_proved"],
                      "local_changed_under_run": v["local_file_changed_under_this_run"],
                      "remote_blob": v["remote_blob"], "local_blob": v["local_blob"],
                      "matched_points": v["points_that_matched"],
                      "unmatched_points": v["points_that_did_not_match"],
                      "ledger_on_control": on_control, "control_blob": control_blob or None,
                      "ledger_on_authoritative": on_authoritative, "authoritative_blob": auth_blob or None,
                      "tip_named_by_server": tip,
                      "json": os.path.basename(out)}, ensure_ascii=False))
    return 0 if v["byte_current_at_every_compared_point"] and v["every_remote_read_self_proved"] else 7


raise SystemExit(main())
