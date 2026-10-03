"""ORD-0558 counterexample - prove the reproducibility arm still bites, on the shipped bytes.

A green ruler nobody has seen fail measures nothing.  This puts the pre-regeneration client back in
place (straight out of git, so it is the bytes the line actually carried), runs the single arm that
compares the committed client against what the declared toolchain produces, requires it to fail, and
restores the committed file -- then verifies the restore by blob, not by hope.

Writes nothing except the receipt beside it.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

TREE = Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
PY = sys.executable
ARM = "tests/test_qoder_ord0508_generated_client_schemas.py::test_the_client_is_byte_for_byte_what_the_declared_toolchain_makes_from_the_contract"
OUT = Path(__file__).resolve().parent / "REGEN_COUNTERARM_r1.json"
CLI = TREE / "frontend/node_modules/openapi-typescript/bin/cli.js"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(TREE), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout.strip()


def run_arm() -> tuple[int, str]:
    env = dict(os.environ)
    env.update({
        "CNX_OPENAPI_TS": str(CLI),
        "PYTHONIOENCODING": "utf-8",
        "DEEPSEEK_API_KEY": "",
        "CITYNEXUS_AI_API_KEY": "",
    })
    proc = subprocess.run(
        [PY, "-m", "pytest", ARM, "-q", "-p", "no:randomly"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(TREE / "backend"), env=env, timeout=900,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    head = git("rev-parse", "HEAD")
    client_blob = git("rev-parse", "HEAD:frontend/src/generated/api.ts")
    prior_blob = git("rev-parse", "HEAD~1:frontend/src/generated/api.ts")
    if client_blob == prior_blob:
        print("ABORT: the candidate did not change the client, so there is nothing to counter-check")
        return 2

    green_rc, green_out = run_arm()
    try:
        subprocess.run(
            ["git", "-C", str(TREE), "checkout", "HEAD~1", "--", "frontend/src/generated/api.ts"],
            check=True, capture_output=True,
        )
        swapped = hashlib.sha1((TREE / "frontend/src/generated/api.ts").read_bytes()).hexdigest()
        red_rc, red_out = run_arm()
    finally:
        subprocess.run(
            ["git", "-C", str(TREE), "checkout", "HEAD", "--", "frontend/src/generated/api.ts"],
            check=True, capture_output=True,
        )
    restored_blob = git("rev-parse", "HEAD:frontend/src/generated/api.ts")
    on_disk_matches_head = subprocess.run(
        ["git", "-C", str(TREE), "diff", "--quiet", "HEAD", "--", "frontend/src/generated/api.ts"],
        capture_output=True,
    ).returncode == 0

    line = next((l for l in red_out.splitlines() if "生成物不可由契约复现" in l), "")
    receipt = {
        "generated_by": "89f2e2d6",
        "head": head,
        "committed_client_blob": client_blob,
        "prior_client_blob": prior_blob,
        "arm_with_committed_client": {"rc": green_rc, "verdict": "GREEN" if green_rc == 0 else "UNEXPECTED"},
        "arm_with_pre_regen_client_swapped_in": {
            "rc": red_rc,
            "verdict": "RED as the counterexample requires" if red_rc != 0 else "ARM DID NOT BITE",
            "local_bytes_sha1_of_swapped_file": swapped,
            "assertion_line": line.strip(),
        },
        "restore": {
            "restored_client_blob": restored_blob,
            "worktree_matches_head": on_disk_matches_head,
        },
        "verdict": "COUNTERARM_OK"
        if green_rc == 0 and red_rc != 0 and on_disk_matches_head and restored_blob == client_blob
        else "COUNTERARM_REFUSED",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("arm committed rc=%d, arm swapped rc=%d" % (green_rc, red_rc))
    print("assertion %s" % line.strip()[:160])
    print("restored worktree==head %s" % on_disk_matches_head)
    print("verdict %s" % receipt["verdict"])
    print("receipt %s" % OUT)
    print("receipt_sha1 %s" % hashlib.sha1(OUT.read_bytes()).hexdigest())
    return 0 if receipt["verdict"] == "COUNTERARM_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
