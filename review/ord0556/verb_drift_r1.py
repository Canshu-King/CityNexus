"""ORD-0556 follow-up, thirteenth leg: same doors, same verbs?

Leg twelve compared the contract's path set with the generated client's path set and found them equal at
both generations. That answer cannot see the break it most easily hides: a path that is present in both
files but carries a DIFFERENT verb in each. A client generated from an older contract keeps compiling, and
the screen asks for `get` where the server now answers `post`.

The contract states verbs as `get:` / `post:` under each path; the generated client states them as
`get: operations[...]` or `get?: never` in a fixed per-path order. Both are read here and compared as
(path, verb) sets.
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
VERBS = ("get", "post", "put", "delete", "patch", "options", "head", "trace")
PATH_KEY = re.compile(r"^  (/[^:\s]+):\s*$")
CLIENT_PATH = re.compile(r'^\s*"(/[^"]+)":\s*\{\s*$')
CLIENT_VERB = re.compile(r"^\s*(" + "|".join(VERBS) + r")(\?)?:")


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


def contract_verbs(src: str) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    path, inside = None, False
    for line in src.splitlines():
        if line.startswith("paths:"):
            inside = True
            continue
        if not inside:
            continue
        if line and not line.startswith(" "):
            break
        m = PATH_KEY.match(line)
        if m:
            path = m.group(1)
            continue
        m = re.match(r"^    (" + "|".join(VERBS) + r"):\s*$", line)
        if m and path:
            out.add((path, m.group(1)))
    return out


def client_verbs(src: str) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    path = None
    for line in src.splitlines():
        m = CLIENT_PATH.match(line)
        if m:
            path = m.group(1)
            continue
        m = CLIENT_VERB.match(line)
        # `get?: never` means the verb is NOT offered on this path; a bare `get:` means it is.
        if m and path and not m.group(2):
            out.add((path, m.group(1)))
    return out


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    doc: dict = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE,
                                "contract": CONTRACT, "generated": GENERATED, "read_only": True},
                 "refs": {}, "verdict": "VERB_DRIFT_READ"}
    for label, ref in (("live_tip", tip), ("sweep_base", SWEEP_BASE)):
        cv = contract_verbs(git("show", f"{ref}:{CONTRACT}"))
        gv = client_verbs(git("show", f"{ref}:{GENERATED}"))
        entry = {"contract_verbs": len(cv), "client_verbs": len(gv),
                 "client_only": sorted(f"{m.upper()} {p}" for p, m in gv - cv)[:40],
                 "contract_only": sorted(f"{m.upper()} {p}" for p, m in cv - gv)[:40],
                 "client_only_count": len(gv - cv), "contract_only_count": len(cv - gv),
                 "sets_equal": cv == gv}
        doc["refs"][label] = entry
        print(f"{label} contract_verbs={entry['contract_verbs']} client_verbs={entry['client_verbs']} "
              f"equal={entry['sets_equal']} client_only={entry['client_only_count']} "
              f"contract_only={entry['contract_only_count']}")
        for row in entry["client_only"][:8]:
            print("  client_only " + row)
        for row in entry["contract_only"][:8]:
            print("  contract_only " + row)
    OUT.joinpath(f"verb_drift_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("receipt verb_drift_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
