"""ORD-0556 follow-up, twelfth leg: does the generated client still cover the contract, at the live tip?

Leg four proved the pruned tree has no dangling relative imports; leg five proved the contract and the
generated client both shrank. Neither asked whether they shrank TOGETHER. A generated client that carries
endpoints the contract no longer declares (or misses ones it does) is a silent break: the TypeScript
compiles, and the screen asks for a door that is not in the contract any more.

Read-only: two blobs per ref, compared by set. No ports, no product bytes, no checkout.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT = WT / "review/ord0556/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SWEEP_BASE = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"
CONTRACT = "contracts/openapi.yaml"
GENERATED = "frontend/src/generated/api.ts"
# A contract path is a key at two-space indent directly under `paths:`; the generated client is an
# interface whose members are quoted keys at four-space indent.
PATH_KEY = re.compile(r'^  (/[^:\s]+):\s*$')
CLIENT_KEY = re.compile(r'^\s*"(/[^"]+)":\s*\{\s*$')


def git(*a: str) -> str:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e)
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(a)}: {(r.stderr or '')[:160]}")
    return r.stdout


def contract_paths(src: str) -> list[str]:
    out, inside = [], False
    for line in src.splitlines():
        if line.startswith("paths:"):
            inside = True
            continue
        if inside:
            if line and not line.startswith(" "):
                break
            m = PATH_KEY.match(line)
            if m:
                out.append(m.group(1))
    return out


def client_paths(src: str) -> list[str]:
    return [m.group(1) for m in (CLIENT_KEY.match(l) for l in src.splitlines()) if m]


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    doc: dict = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE,
                                "contract": CONTRACT, "generated": GENERATED, "read_only": True},
                 "refs": {}, "verdict": "CONTRACT_DRIFT_READ"}
    for label, ref in (("live_tip", tip), ("sweep_base", SWEEP_BASE)):
        cpaths = contract_paths(git("show", f"{ref}:{CONTRACT}"))
        gpaths = client_paths(git("show", f"{ref}:{GENERATED}"))
        cset, gset = set(cpaths), set(gpaths)
        doc["refs"][label] = {
            "contract_paths": len(cset), "client_paths": len(gset),
            "client_without_contract": sorted(gset - cset),
            "contract_without_client": sorted(cset - gset),
            "sets_equal": cset == gset,
        }
        r = doc["refs"][label]
        print(f"{label} contract={r['contract_paths']} client={r['client_paths']} "
              f"equal={r['sets_equal']} client_only={len(r['client_without_contract'])} "
              f"contract_only={len(r['contract_without_client'])}")
        for p in r["client_without_contract"][:8]:
            print(f"  client_only {p}")
        for p in r["contract_without_client"][:8]:
            print(f"  contract_only {p}")
    OUT.joinpath(f"contract_drift_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("receipt contract_drift_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
