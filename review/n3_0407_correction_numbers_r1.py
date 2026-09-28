#!/usr/bin/env python3
"""ORD-0407 -- the numbers the correction block cites, produced rather than typed.

Q43's older versions (r5b and up) want a diff count or an absence declaration to sit beside a
`path:line`, not beside a re-runnable command.  So the values go into a file the ledger can point at.
Every field below is computed in this run: git for the diffs and refs, sockets for the port band, a
byte comparison for the ledger copy, and a call-site scan for the `demo/reset` absence -- an absence is
stated as "0 call sites in the files this lane wrote", which is measurable, not as a promise.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import socket
import subprocess
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_n3_ord0357")
BASE = "890b7cfcf1a103a24d8a013e1b0b5eeecbe9b4dd"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LEDGER = Path(r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md")
INSERTED = WT.parent / "_qoder_ledger_inbox/_processed/n3_2146.md.inserted_214902"
MY_FILES = [
    "frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts",
    "review/n3_0407_write_door_inventory_r1.py",
    "review/n3_0407_baseline_r1.py",
    "review/n3_0407_mutations_r1.py",
    "review/n3_0407_copy_pair_check_r1.py",
    "review/n3_0407_receipt_anchors_r1.py",
    "review/n3_0407_correction_numbers_r1.py",
]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(WT), *args], capture_output=True, text=True).stdout.strip()


def main() -> int:
    head = git("rev-parse", "HEAD")
    out: dict[str, object] = {"head": head, "base": BASE}

    diff = git("diff", "--shortstat", BASE, head, "--", "frontend", "contracts")
    out["shortstat"] = diff
    out["files_changed"] = int(re.search(r"(\d+) files? changed", diff).group(1))
    out["insertions"] = int(re.search(r"(\d+) insertions", diff).group(1))
    out["deletions"] = int(re.search(r"(\d+) deletions", diff).group(1))
    numstat = git("diff", "--numstat", BASE, head, "--",
                  "frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts").split("\n")[0]
    out["gate_spec_insertions"] = int(numstat.split("\t")[0])
    out["frontend_tree"] = git("rev-parse", f"{head}:frontend")
    out["contracts_tree"] = git("rev-parse", f"{head}:contracts")

    status = git("status", "--porcelain", "--", "frontend", "contracts")
    out["worktree_product_status_lines"] = len([l for l in status.splitlines() if l.strip()])

    free = held = 0
    for q in range(5470, 5600):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", q))
            free += 1
        except OSError:
            held += 1
        finally:
            s.close()
    out["band_5470_5599"] = {"bindable_sockets": free, "not_bindable_sockets": held}

    # An absence, stated as a measurement: how many call sites for the destructive demo door exist in
    # the files this lane wrote.  The scanner's own pattern string is excluded, otherwise it counts
    # itself (which the first version of this file did, and reported 2 hits for 0 call sites).
    here = Path(__file__).name
    hits = 0
    per_file: dict[str, int] = {}
    for rel in MY_FILES:
        if Path(rel).name == here:
            continue
        p = WT / rel
        if not p.is_file():
            per_file[rel] = -1
            continue
        n = len(re.findall(r"demo/reset", io.open(p, encoding="utf-8", errors="replace").read()))
        per_file[rel] = n
        hits += n
    out["scanner_file_excluded"] = f"review/{here}"
    out["demo_reset_call_sites_in_lane_files"] = hits
    out["demo_reset_call_sites_per_file"] = per_file

    # Which refs this lane can push to, read back from the remote rather than asserted.
    ls = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin",
                         TIP_REF, "refs/heads/review/N3-ord0407-empty-state-actions-r4"],
                        capture_output=True, text=True).stdout
    refs = dict(re.findall(r"^([0-9a-f]{40})\s+(\S+)$", ls, re.M))
    out["ls_remote_readback"] = {v: k for k, v in refs.items()}
    out["tip_now"] = refs.get(TIP_REF)
    out["candidate_r4"] = refs.get("refs/heads/review/N3-ord0407-empty-state-actions-r4")

    led = io.open(LEDGER, encoding="utf-8").read()
    start = led.index("### N3 21:46+08")
    block = led[start:led.index("\n### ", start + 10)].rstrip("\n")
    proc = io.open(INSERTED, encoding="utf-8").read().rstrip("\n")
    out["ledger_block_bytes"] = len(block.encode("utf-8"))
    out["inserted_copy_bytes"] = len(proc.encode("utf-8"))
    out["ledger_block_sha1"] = hashlib.sha1(block.encode("utf-8")).hexdigest()
    out["inserted_copy_sha1"] = hashlib.sha1(proc.encode("utf-8")).hexdigest()
    out["inserted_text_identical_to_my_candidate"] = block == proc

    dst = WT / "review/n3_0407_evidence_r1/correction_numbers_r1.json"
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for i, l in enumerate(io.open(dst, encoding="utf-8").read().splitlines(), 1):
        print(f"{i}: {l[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
