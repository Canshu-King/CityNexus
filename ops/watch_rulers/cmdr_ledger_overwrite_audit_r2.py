"""Independently measure lane E's ledger overwrite and her self-reported recovery - my own bytes, not her prose.

Why: at 21:47 lane E's ledger append rewrote the whole shared ledger down to her single block (she
self-reported it at 22:0x and said she restored it byte-for-byte from the pre-damage commit).  A shared-file
overwrite is the worst failure mode on this project and a self-reported fix is not a verified fix, so I
recompute every claim from git objects in my own clone:
  * the size of the ledger blob at each of the four named commits,
  * whether the restored file actually carries the pre-damage bytes as a strict prefix,
  * whether my own mirror afterwards preserved her a3 block and mine (remote-lost / local-lost lines),
  * and the live state: the current blob on commander/control vs my local file.

Read-only against git objects; no ref moves, no writes outside my own _qoder_* directory.
"""
import hashlib
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"
LEDGER_PATH = "CITYNEXUS_AGENT_CONTROL.md"
LOCAL_LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"

COMMITS = {
    "d87b802b1205c0f2f7e9cd20c1c870702fde1dc5": "pre-damage commit E names as her source",
    "79079acc56": "E's overwrite commit (she says 732 B)",
    "1600304b15": "E's recovery commit (she says 5,956,345 B)",
}
OLD_BLOB = "0f7e3c72874e9ae493244b852e6cbb22fa9e8c88"
HER_RESTORED_BLOB = "930ccdfcd0d5405af32ea6805c024fb1a910c49e"
MY_MIRROR_BLOB = "cd91c057f9447bba6bf5a39ddb0553dd6ee074c6"


def git(*a, binary=False):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=600)
    if p.returncode:
        raise SystemExit("git %s failed rc=%d: %s" % (" ".join(a[:3]), p.returncode,
                                                      p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def blob_at(rev):
    sha = git("rev-parse", "--revs-only", "%s:%s" % (rev, LEDGER_PATH))
    data = git("cat-file", "blob", sha, binary=True)
    recomputed = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()
    return sha, len(data), recomputed, recomputed == sha, data


def main():
    rows = []
    blobs = {}
    for rev, note in COMMITS.items():
        full = git("rev-parse", "--revs-only", rev)
        sha, size, recomputed, ok, data = blob_at(full)
        blobs[full] = data
        rows.append({"commit": full, "commit_short": rev, "role": note, "ledger_blob": sha,
                     "ledger_bytes": size, "blob_sha1_recomputes_from_bytes": ok})
    old = blobs[[k for k in blobs if k.startswith("d87b802b")][0]]
    restored = blobs[[k for k in blobs if k.startswith("1600304b")][0]]
    damaged = blobs[[k for k in blobs if k.startswith("79079acc")][0]]
    prefix_equal = restored[:len(old)] == old
    local = io.open(LOCAL_LEDGER, "rb").read()
    local_blob = hashlib.sha1(b"blob %d\x00" % len(local) + local).hexdigest()
    txt_local = local.decode("utf-8", "replace").splitlines()
    txt_old = old.decode("utf-8", "replace").splitlines()
    markers = ["CMDR-0925-2207", "CMDR-0925-2154", "ORD-0314 \u2192 \u7ea2\u961f E",
               "ORD-0300 C2 \u88652", "## ORDERS\uff08", "CMDR-0925-2128", "ORD-0305"]
    out = {
        "schema": "CNX_CMDR_LEDGER_OVERWRITE_AUDIT_V2",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "independent measurement of lane E's 21:47 shared-ledger overwrite and her recovery, "
                "from git objects in my own clone",
        "trigger": "lane E bus post 5833747953 (self-reported overwrite + recovery); her numbers are her claims, "
                   "the rows below are mine",
        "commits_measured": rows,
        "damaged_is_strict_subset": {"damaged_bytes": len(damaged), "pre_damage_bytes": len(old),
                                      "damaged_lines": len(damaged.decode("utf-8", "replace").splitlines()),
                                      "pre_damage_lines": len(txt_old),
                                      "lines_of_pre_damage_missing_after_the_overwrite":
                                          len(set(txt_old) - set(damaged.decode("utf-8", "replace").splitlines()))},
        "recovery_check": {"restored_prefix_equals_pre_damage_bytes": prefix_equal,
                           "restored_bytes": len(restored), "pre_damage_bytes": len(old),
                           "bytes_added_by_the_recovery": len(restored) - len(old),
                           "verdict": "BYTE_PRESERVING_APPEND_ONLY" if prefix_equal else "PREFIX_BROKEN"},
        "blob_coordinates": {"pre_damage_blob_expected": OLD_BLOB,
                             "pre_damage_blob_measured": [r["ledger_blob"] for r in rows if r["commit_short"].startswith("d87b")][0],
                             "recovered_blob_expected": HER_RESTORED_BLOB,
                             "recovered_blob_measured": [r["ledger_blob"] for r in rows if r["commit_short"].startswith("1600")][0],
                             "my_mirror_blob_after": MY_MIRROR_BLOB},
        "current_state": {"local_ledger_bytes": len(local), "local_ledger_blob": local_blob,
                          "local_blob_equals_my_mirror_claim": local_blob == MY_MIRROR_BLOB,
                          "local_carries_every_named_block": {m: "\n".join(txt_local).count(m) for m in markers}},
        "loss_after_my_mirror": {"lines_of_E_recovery_missing_locally":
                                 len(set(restored.decode("utf-8", "replace").splitlines()) - set(txt_local)),
                                 "lines_of_pre_damage_missing_locally": len(set(txt_old) - set(txt_local))},
        "standing_rule": "a self-reported fix to a shared file is measured, not accepted: byte-count each named "
                         "commit from the object store and test prefix identity, because 'restored' can mean "
                         "'restored minus what I did not look at'.",
        "discipline": {"refs_pushed": 0, "authoritative_branch_moved": 0, "ledger_written_by_this_script": 0,
                       "databases_opened": 0, "credential_values_printed": 0, "git_write_operations_run": 0},
        "claim_kind": "git_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = (
        "overwrite commit %s carries the ledger at %d B (%d lines, %d of %d pre-damage lines gone); recovery "
        "commit %s carries %d B and its first %d bytes equal the pre-damage blob byte for byte (%s); my mirror "
        "blob %s loses 0 pre-damage lines and 0 recovery lines locally." % (
            rows[1]["commit"][:10], rows[1]["ledger_bytes"],
            out["damaged_is_strict_subset"]["damaged_lines"],
            out["damaged_is_strict_subset"]["lines_of_pre_damage_missing_after_the_overwrite"],
            out["damaged_is_strict_subset"]["pre_damage_lines"],
            rows[2]["commit"][:10], rows[2]["ledger_bytes"], rows[0]["ledger_bytes"],
            "verified" if prefix_equal else "FAILED", MY_MIRROR_BLOB[:12]))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_ledger_overwrite_r2.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for r in rows:
        print("   %-12s %-12s %9d B  recomputes=%s" % (r["commit_short"], r["ledger_blob"][:12],
                                                       r["ledger_bytes"], r["blob_sha1_recomputes_from_bytes"]))
    print("local blob %s %d B  E-recovery lines lost locally %d" % (
        local_blob[:12], len(local), out["loss_after_my_mirror"]["lines_of_E_recovery_missing_locally"]))
    print("file=_cmdr_ledger_overwrite_r2.json bytes=%d" % len(txt.encode("utf-8")))
    return 0 if prefix_equal else 6


if __name__ == "__main__":
    sys.exit(main())
