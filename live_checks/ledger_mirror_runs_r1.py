# -*- coding: utf-8 -*-
"""Drive ORD-0552's reads: three runs of the shipping route, one run that forces fresh transport, and the arms.

Nothing here is asserted that a command did not print; every leg's raw json goes into the log file so the
commander can re-run the same invocations. The fresh-transport leg exists because three reads from an
already-populated object store prove the hash gate, not the network - so that distinction is stated in the
output rather than papered over.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
INSTRUMENT = os.path.join(HERE, "ledger_mirror_complete_read_r1.py")
GH_URL = "https://github.com/Canshu-King/CityNexus.git"
TMP = r"D:\moodle\_qoder_ord0552_freshclone"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)


def run(args, timeout=3600):
    t0 = time.time()
    p = subprocess.run([PY, INSTRUMENT] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=timeout, cwd=HERE)
    out = (p.stdout or "") + (p.stderr or "")
    doc = None
    for line in out.splitlines():
        if line.strip().startswith("{"):
            try:
                doc = json.loads(out[out.index("{"):])
            except ValueError:
                doc = None
            break
    return {"cmd": "python ledger_mirror_complete_read_r1.py " + " ".join(args), "rc": p.returncode,
            "seconds": round(time.time() - t0, 1), "json": doc, "raw_tail": out[-400:]}


def fresh_transport():
    """One read where the blob is not in any local store: partial clone, then a lazy blob fetch.

    Nothing here may raise: if the clone or either git call fails, the leg reports what it attempted and
    what came back, and the shipping-route runs still stand on their own.
    """
    tmp = TMP + "_" + str(int(time.time()))
    if os.path.exists(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    p = subprocess.run(["git", "-c", "protocol.version=2", "clone", "--filter=blob:none", "--no-checkout",
                        "--single-branch", "--branch", "commander/control", GH_URL, tmp],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV,
                       timeout=3600, cwd=HERE)
    note = {"clone_rc": p.returncode,
            "clone_said": (((p.stdout or "") + (p.stderr or "")).strip().splitlines() or [""])[-1][:200]}
    if p.returncode != 0:
        note["outcome"] = "NOT_ATTEMPTED_FURTHER"
        shutil.rmtree(tmp, ignore_errors=True)
        return dict(note, attempted=True)
    # the blob id is read out of the tree listing, which is what actually exists in a no-checkout clone
    ls = subprocess.run(["git", "-C", tmp, "ls-tree", "HEAD", "--", "CITYNEXUS_AGENT_CONTROL.md"],
                        capture_output=True, text=True, encoding="utf-8", env=ENV, timeout=900)
    parts = (ls.stdout or "").split()
    note.update({"ls_tree_rc": ls.returncode, "ls_tree_line": (ls.stdout or "").strip()[:160]})
    if len(parts) < 3:
        note.update({"attempted": True, "outcome": "NO_BLOB_ID_FROM_LS_TREE", "stderr": (ls.stderr or "")[-160:]})
        shutil.rmtree(tmp, ignore_errors=True)
        return note
    blob = parts[2]
    t0 = time.time()
    q = subprocess.run(["git", "-C", tmp, "cat-file", "blob", blob], capture_output=True, env=ENV,
                       timeout=3600)
    raw = q.stdout or b""
    import hashlib
    got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    sz = subprocess.run(["git", "-C", tmp, "cat-file", "-s", blob], capture_output=True, text=True,
                        encoding="utf-8", env=ENV, timeout=900)
    declared = int(sz.stdout.strip()) if sz.stdout.strip().isdigit() else None
    note.update({"attempted": True, "cat_file_rc": q.returncode, "blob_named_by_fetched_tree": blob,
                 "bytes_read_over_transport": len(raw), "declared_size": declared,
                 "git_blob_sha1_of_those_bytes": got, "hash_equal": got == blob,
                 "size_equal": declared is not None and len(raw) == declared,
                 "seconds": round(time.time() - t0, 1),
                 "outcome": "FRESH_TRANSPORT_OK" if got == blob else "FRESH_TRANSPORT_MISMATCH",
                 "why_this_leg_exists": "three reads from a populated object store prove the hash gate, "
                                        "not the network"})
    shutil.rmtree(tmp, ignore_errors=True)
    return note


def main():
    legs = []
    for i in (1, 2, 3):
        r = run(["--route", "git", "--out", os.path.join(HERE, "ledger_mirror_run_r1_%d.json" % i)])
        r["label"] = "shipping_route_run_%d" % i
        legs.append(r)
        print(json.dumps({"leg": r["label"], "rc": r["rc"],
                          "verdict": (r["json"] or {}).get("verdict"),
                          "bytes": (r["json"] or {}).get("bytes_fetched"),
                          "recomputed": (r["json"] or {}).get("recomputed_git_blob_sha1"),
                          "reported": (r["json"] or {}).get("remote_blob_from_api"),
                          "agree": (r["json"] or {}).get("two_channel_agreement")}, ensure_ascii=False))
    fr = fresh_transport()
    print(json.dumps({"leg": "fresh_transport", "hash_equal": fr.get("hash_equal"),
                      "bytes": fr.get("bytes_read_over_transport"), "err": fr.get("error")},
                     ensure_ascii=False))
    for arm in ("old_onshot_read", "wrong_expected_sha", "short_body"):
        r = run(["--arm", arm, "--out", os.path.join(HERE, "ledger_mirror_arm_%s_r1.json" % arm)])
        r["label"] = "arm_" + arm
        legs.append(r)
        j = r["json"] or {}
        print(json.dumps({"leg": r["label"], "rc": r["rc"], "verdict": j.get("verdict"),
                          "passes_by_refusing": j.get("arm_passes_by_refusing"),
                          "bytes": j.get("bytes_fetched")}, ensure_ascii=False))
    r = run(["--route", "api", "--out", os.path.join(HERE, "ledger_mirror_api_route_r1.json")])
    r["label"] = "api_size_bounded_route"
    legs.append(r)
    j = r["json"] or {}
    print(json.dumps({"leg": r["label"], "rc": r["rc"], "verdict": j.get("verdict"),
                      "attempts": (j.get("read") or {}).get("attempts"),
                      "shortfalls": [p["short_by"] for p in (j.get("read") or {}).get("per_attempt", [])]},
                     ensure_ascii=False))
    three = [l for l in legs if l["label"].startswith("shipping_route_run")]
    arms = [l for l in legs if l["label"].startswith("arm_")]
    doc = {"checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "three_runs_all_complete": all((l["json"] or {}).get("verdict") == "COMPLETE_AND_HASHED_EQUAL"
                                          and l["rc"] == 0 for l in three),
           "three_runs_same_blob": len({(l["json"] or {}).get("remote_blob_from_api") for l in three}) == 1,
           "arms_all_refused": all((l["json"] or {}).get("arm_passes_by_refusing") and l["rc"] == 0
                                   for l in arms),
           "fresh_transport": fr, "api_route_still_truncates": (j.get("verdict") !=
                                                                "COMPLETE_AND_HASHED_EQUAL"),
           "legs": legs}
    io.open(os.path.join(HERE, "ledger_mirror_runs_summary_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({k: doc[k] for k in ("three_runs_all_complete", "three_runs_same_blob",
                                          "arms_all_refused", "api_route_still_truncates")},
                     ensure_ascii=False))
    return 0 if (doc["three_runs_all_complete"] and doc["arms_all_refused"]) else 7


raise SystemExit(main())
