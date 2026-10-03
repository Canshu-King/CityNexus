"""ORD-0520 glass walk, side finding -- the shipped client is not byte-reproducible from the contract.

Found while re-measuring the parity gates for this hand (0 contract bytes changed here, so the gate
ought to be boring): the pinned toolchain (openapi-typescript 7.13.0) regenerates
`frontend/src/generated/api.ts` with one more token in a comment than the committed file carries, so
the arm `backend/tests/test_qoder_ord0508_generated_client_schemas.py::
test_the_client_is_byte_for_byte_what_the_declared_toolchain_makes_from_the_contract` is RED on the
authoritative line -- and it is RED at the base commit too, which is why this file reports the
finding instead of fixing it under this order.

The path-level and name-level rulers stay green (`formal 175; runtime 175; missing 0; extra 0`,
`schemas formal 87; generated 87`), which is exactly the gap ORD-0508 named: a description-only
contract edit is invisible to them.

This script changes nothing.  It regenerates into a temporary directory, diffs, and writes a receipt.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "contracts" / "openapi.yaml"
GENERATED = REPO / "frontend" / "src" / "generated" / "api.ts"
OUT = Path(__file__).resolve().parent / "GENERATED_CLIENT_DRIFT_r1.json"
TOKEN = "CHECKIN_JOURNEY_UNKNOWN"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.strip()


def main() -> int:
    cli = os.environ.get("CNX_OPENAPI_TS", "")
    node = shutil.which("node")
    if not cli or not node or not os.path.exists(cli):
        print("ABORT: CNX_OPENAPI_TS must name openapi-typescript's cli.js and node must be reachable")
        return 2

    version = json.loads(
        Path(cli).parent.parent.joinpath("package.json").read_text(encoding="utf-8")
    )["version"]

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "api.ts"
        run = subprocess.run(
            [node, cli, str(CONTRACT), "-o", str(out)], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if run.returncode != 0:
            print("ABORT: the declared generator failed: %s" % run.stderr[:400])
            return 1
        regen = out.read_text(encoding="utf-8", errors="replace")

    committed = GENERATED.read_text(encoding="utf-8", errors="replace")
    a = regen.replace("\r\n", "\n").rstrip() + "\n"
    b = committed.replace("\r\n", "\n").rstrip() + "\n"
    first_offset = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), None)

    diff_lines = list(
        difflib.unified_diff(
            b.splitlines(), a.splitlines(), lineterm="", fromfile="committed", tofile="regenerated"
        )
    )
    changed = [line for line in diff_lines if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]

    introduced = git("log", "--format=%H %ad %s", "--date=short", "-S", TOKEN, "--", "contracts/openapi.yaml").splitlines()
    client_touches = git("log", "--format=%H %s", "-S", TOKEN, "--", "frontend/src/generated/api.ts").splitlines()

    receipt = {
        "generated_by": "89f2e2d6",
        "measured_at_head": git("rev-parse", "HEAD"),
        "authoritative_tip_at_measurement": os.environ.get("CITYNEXUS_AUTHORITATIVE_TIP", "not supplied"),
        "generator": "openapi-typescript %s" % version,
        "generator_cli_disk_sha1": hashlib.sha1(Path(cli).read_bytes()).hexdigest(),
        "contract_bytes_sha1": hashlib.sha1(CONTRACT.read_bytes()).hexdigest(),
        "committed_client_bytes": len(GENERATED.read_bytes()),
        "committed_client_chars": len(b),
        "regenerated_client_chars": len(a),
        "byte_identical": a == b,
        "first_differing_offset": first_offset,
        "differing_lines": changed[:12],
        "differing_line_count": len(changed),
        "token": TOKEN,
        "contract_commits_naming_the_token": introduced[:5],
        "client_commits_naming_the_token": client_touches[:5],
        "rulers_that_stay_green": {
            "paths_and_methods": "formal 175; runtime 175; missing 0; extra 0",
            "component_schema_names": "schemas formal 87; generated 87; missing 0; extra 0",
        },
        "meaning": "a description-only edit reached contracts/openapi.yaml without regenerating the "
        "client; the name-level ruler cannot see it, which is the failure ORD-0508 was written to "
        "catch. The repair is one regeneration with the declared toolchain -- it is not this order's "
        "write set, so it is reported rather than landed here.",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("byte_identical %s" % receipt["byte_identical"])
    print("differing lines %d, first offset %s" % (receipt["differing_line_count"], first_offset))
    print("contract commits naming %s: %s" % (TOKEN, receipt["contract_commits_naming_the_token"]))
    print("client commits naming %s: %s" % (TOKEN, receipt["client_commits_naming_the_token"] or "NONE"))
    print("receipt %s" % OUT)
    print("receipt_sha1 %s" % hashlib.sha1(OUT.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
