"""ORD-0558 r3 - a re-runnable check: is the shipped client reproducible from the shipped contract?

Why r2/r3 exist: the landing sequencer ABORT-ed the r1 candidate with `1 file(s) did not merge to the
lane's own bytes`, and the reason is measured here rather than guessed -- while this hand was open
another lane landed `7a8a1db39` (ORD-0551), which added two lines to `contracts/openapi.yaml` **and
regenerated `frontend/src/generated/api.ts` in the same commit**.  That regeneration already carries
the token ORD-0558 was opened for (`CHECKIN_JOURNEY_UNKNOWN`), so the product goal is met on the
authoritative line and any client this lane produces from an older contract would be a downgrade.
The gate was right to refuse.

This file therefore ships no product bytes.  It answers one question, for whatever HEAD it is run
at: does the declared toolchain (openapi-typescript 7.13.0, the version the pinned arms name)
reproduce the committed client byte for byte -- twice, so the answer is not one run's luck.

`--counterarm` additionally swaps a *known-stale* client in (the blob the line carried before
ORD-0551 regenerated it) and requires the shipped ruler's byte-for-byte arm to go red, because a
ruler nobody has seen fail is not measuring anything.  The file is always restored from HEAD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLIENT = REPO / "frontend/src/generated/api.ts"
CONTRACT = REPO / "contracts/openapi.yaml"
CLI = REPO / "frontend/node_modules/openapi-typescript/bin/cli.js"
ARM = (
    "tests/test_qoder_ord0508_generated_client_schemas.py::"
    "test_the_client_is_byte_for_byte_what_the_declared_toolchain_makes_from_the_contract"
)
STALE_BLOB = "988015e270a218d9ed43eecdade256ae9ee18e3b"
OUT = Path(__file__).resolve().parent / "CLIENT_REPRODUCIBLE_r3.json"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout.strip()


def generate(target: Path) -> int:
    return subprocess.run(
        ["node", str(CLI), str(CONTRACT), "-o", str(target)], capture_output=True, text=True
    ).returncode


def run_arm() -> tuple[int, str]:
    env = dict(os.environ)
    env.update({"CNX_OPENAPI_TS": str(CLI), "PYTHONIOENCODING": "utf-8",
                "DEEPSEEK_API_KEY": "", "CITYNEXUS_AI_API_KEY": ""})
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", ARM, "-q", "-p", "no:randomly"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO / "backend"), env=env, timeout=900,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def line_diff(a: bytes, b: bytes) -> dict:
    la = a.decode("utf-8", "replace").splitlines()
    lb = b.decode("utf-8", "replace").splitlines()
    first = next((i for i, (x, y) in enumerate(zip(la, lb)) if x != y), None)
    return {
        "lines_regen": len(la), "lines_committed": len(lb),
        "first_differing_line": (first + 1) if first is not None else None,
        "regen_line": la[first].strip()[:200] if first is not None else None,
        "committed_line": lb[first].strip()[:200] if first is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counterarm", action="store_true")
    args = parser.parse_args()

    head = git("rev-parse", "HEAD")
    tip_of_line = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
    version = json.loads((CLI.parent.parent / "package.json").read_text(encoding="utf-8"))["version"]

    tmp = REPO.parent / "tmp"
    a = tmp / "r2_regen_a.ts"
    b = tmp / "r2_regen_b.ts"
    rc_a, rc_b = generate(a), generate(b)
    gen_bytes = a.read_bytes() if a.exists() else b""
    committed = CLIENT.read_bytes()

    reading = {
        "generated_by": "89f2e2d6",
        "hand": "ORD-0558 r3 (evidence only; 0 product bytes; re-cut onto the current tip)",
        "measured_at_head": head,
        "authoritative_ref_line": tip_of_line,
        "toolchain": {"package": "openapi-typescript", "version": version,
                       "cli_disk_sha1_8": hashlib.sha1(CLI.read_bytes()).hexdigest()[:8]},
        "contract": {"blob": git("rev-parse", "HEAD:contracts/openapi.yaml"), "bytes": CONTRACT.stat().st_size},
        "client": {"blob": git("rev-parse", "HEAD:frontend/src/generated/api.ts"),
                    "bytes": len(committed), "cr_bytes": committed.count(b"\r"),
                    "local_sha1_8": hashlib.sha1(committed).hexdigest()[:8]},
        "token_ORD0558_was_opened_for": {
            "name": "CHECKIN_JOURNEY_UNKNOWN",
            "in_the_committed_client": b"CHECKIN_JOURNEY_UNKNOWN" in committed,
            "in_the_contract": b"CHECKIN_JOURNEY_UNKNOWN" in CONTRACT.read_bytes(),
            "introduced_into_the_contract_by": "97bf72736a753633b0d3d8d4c2b48dd65f48b08e",
            "client_last_regenerated_by": git(
                "log", "-1", "--format=%H %ad %s", "--date=iso", "HEAD", "--",
                "frontend/src/generated/api.ts")[:120],
        },
        "two_runs": {
            "rc_a": rc_a, "rc_b": rc_b,
            "sha1_8_a": hashlib.sha1(gen_bytes).hexdigest()[:8],
            "sha1_8_b": hashlib.sha1(b.read_bytes()).hexdigest()[:8] if b.exists() else None,
            "identical": a.exists() and b.exists() and a.read_bytes() == b.read_bytes(),
            "regenerated_equals_committed": gen_bytes == committed,
        },
        "verdict": "REPRODUCIBLE_AT_HEAD" if gen_bytes == committed and a.read_bytes() == b.read_bytes()
        else "NOT_REPRODUCIBLE_AT_HEAD",
    }
    if reading["verdict"] != "REPRODUCIBLE_AT_HEAD":
        reading["diff_detail"] = line_diff(gen_bytes, committed)

    if args.counterarm:
        stale = subprocess.run(
            ["git", "-C", str(REPO), "cat-file", "blob", STALE_BLOB], capture_output=True
        ).stdout
        green_rc, green_out = run_arm()
        try:
            CLIENT.write_bytes(stale)
            red_rc, red_out = run_arm()
        finally:
            subprocess.run(
                ["git", "-C", str(REPO), "checkout", "HEAD", "--", "frontend/src/generated/api.ts"],
                check=True, capture_output=True,
            )
        restored = CLIENT.read_bytes() == committed
        digits = [c for c in "0123456789"]
        candidates = [
            l for l in red_out.splitlines()
            if "生成物不可由契约复现" in l and any(d in l for d in digits)
        ]
        assertion = candidates[-1] if candidates else next(
            (l for l in red_out.splitlines() if "生成物不可由契约复现" in l), "")
        reading["counterarm"] = {
            "stale_blob_swapped_in": STALE_BLOB,
            "stale_bytes": len(stale),
            "arm_with_committed_client": {"rc": green_rc, "output_tail": green_out.strip().splitlines()[-1][:160]},
            "arm_with_stale_client": {"rc": red_rc, "assertion_line": assertion.strip(),
                                       "output_tail": red_out.strip().splitlines()[-1][:160]},
            "restored_to_committed_bytes": restored,
            "verdict": "COUNTERARM_OK" if green_rc == 0 and red_rc != 0 and restored else "COUNTERARM_REFUSED",
        }
        reading["counterarm_verdict"] = reading["counterarm"]["verdict"]

    OUT.write_text(json.dumps(reading, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("head %s" % head)
    print("ref line %s" % tip_of_line)
    print("contract blob %s bytes %d" % (reading["contract"]["blob"], reading["contract"]["bytes"]))
    print("client blob %s bytes %d CR %d" % (
        reading["client"]["blob"], reading["client"]["bytes"], reading["client"]["cr_bytes"]))
    print("token in committed client: %s (contract: %s)" % (
        reading["token_ORD0558_was_opened_for"]["in_the_committed_client"],
        reading["token_ORD0558_was_opened_for"]["in_the_contract"]))
    print("two runs identical %s; regenerated == committed %s" % (
        reading["two_runs"]["identical"], reading["two_runs"]["regenerated_equals_committed"]))
    print("verdict %s" % reading["verdict"])
    if "counterarm" in reading:
        ca = reading["counterarm"]
        print("counterarm committed rc=%d, stale rc=%d, restored=%s -> %s" % (
            ca["arm_with_committed_client"]["rc"], ca["arm_with_stale_client"]["rc"],
            ca["restored_to_committed_bytes"], ca["verdict"]))
        print("assertion %s" % ca["arm_with_stale_client"]["assertion_line"][:170])
    print("receipt %s" % OUT)
    print("receipt_sha1_8 %s" % hashlib.sha1(OUT.read_bytes()).hexdigest()[:8])
    return 0 if reading["verdict"] == "REPRODUCIBLE_AT_HEAD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
