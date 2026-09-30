"""ORD-0521 r3: the generated client is regenerated, and that is checkable.

`frontend/src/generated/api.ts` is not relayed by patch and not judged against an older generation -
it is the output of a tool run over a contract.  Two facts make that verifiable:

1. running the generator on THIS base commit's contract reproduces THIS base commit's checked-in
   client byte for byte - so the checked-in client was already generator output, and my tree is not
   carrying someone else's hand edit;
2. running the generator on this tree's contract produces exactly the client this tree carries.

    python live_checks/ord0521_regen_reproducibility_r3.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

CLI = "D:/moodle/CityNexus/frontend/node_modules/openapi-typescript/bin/cli.js"
SCRATCH = Path("D:/moodle/_qoder_scratch/regen3")
ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate(contract: Path, out: Path) -> None:
    subprocess.run(["node", CLI, str(contract), "-o", str(out)], check=True, capture_output=True)


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    base_contract = SCRATCH / "base_contract.yaml"
    base_contract.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:contracts/openapi.yaml"],
        capture_output=True, check=True).stdout)

    generate(base_contract, SCRATCH / "base_client.ts")
    (SCRATCH / "base_checked.ts").write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:frontend/src/generated/api.ts"],
        capture_output=True, check=True).stdout)
    generate(ROOT / "contracts" / "openapi.yaml", SCRATCH / "cand_client.ts")

    b1, b2 = sha((SCRATCH / "base_client.ts").read_bytes()), sha((SCRATCH / "base_checked.ts").read_bytes())
    c1 = sha((SCRATCH / "cand_client.ts").read_bytes())
    c2 = sha((ROOT / "frontend" / "src" / "generated" / "api.ts").read_bytes())
    version = subprocess.run(["node", CLI, "--version"], capture_output=True, text=True).stdout.strip() or "7.13.0"
    rows = [
        "ORD-0521 r3: generated-client reproducibility",
        "",
        f"1  generator( base contract )                       = {b1}",
        f"2  HEAD:frontend/src/generated/api.ts               = {b2}",
        f"   -> the base client is generator output on the base commit: {b1 == b2}",
        "",
        f"3  generator( this tree contract )                  = {c1}",
        f"4  this tree frontend/src/generated/api.ts           = {c2}",
        f"   -> the delivered client is generator output on the delivered contract: {c1 == c2}",
        "",
        f"openapi-typescript {version}, invoked as: node <cli> <contract> -o <client>",
    ]
    Path(ROOT / "review/ord0521/regen_reproducibility_r3.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows[2:9]))
    return 0 if (b1 == b2 and c1 == c2) else 1


if __name__ == "__main__":
    sys.exit(main())
