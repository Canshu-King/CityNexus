"""ORD-0556 follow-up, fourteenth leg: same door, same verb, same named shapes?

Legs twelve and thirteen compared the path set and the (path, verb) set and found them equal at both
generations. Neither can see the next level down: a named schema that exists in the contract but not in the
generated client (or the reverse). A screen typed against a shape the server no longer returns fails at
runtime, and TypeScript will not object if the client still carries the old copy.

The contract states schemas as `components: schemas: Name:` at four-space indent; the generated client as
members of `components["schemas"]` at eight-space indent. Both sets are read here and compared.
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
SCHEMA_KEY = re.compile(r"^    ([A-Za-z0-9_]+):\s*$")
# The generated client writes them UNQUOTED at eight spaces (`PlanningMode: {`), not as
# `"PlanningMode": {`; the first version of this regex demanded quotes and read zero.
CLIENT_SCHEMA = re.compile(r"^        ([A-Za-z0-9_]+):\s*")


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


def contract_schemas(src: str) -> list[str]:
    out, inside = [], False
    for line in src.splitlines():
        if line == "  schemas:":
            inside = True
            continue
        if inside:
            if line and not line.startswith(" "):
                break
            m = SCHEMA_KEY.match(line)
            if m:
                out.append(m.group(1))
    return out


def client_schemas(src: str) -> list[str]:
    """Members of components["schemas"]. The section runs until the next top-level export."""
    out, inside = [], False
    for line in src.splitlines():
        if line.startswith("export interface components"):
            inside = True
            continue
        if inside:
            if line.startswith("export interface"):
                break
            m = CLIENT_SCHEMA.match(line)
            if m:
                out.append(m.group(1))
    return out


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    doc: dict = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE,
                                "contract": CONTRACT, "generated": GENERATED, "read_only": True},
                 "refs": {}, "verdict": "SHAPE_DRIFT_READ"}
    for label, ref in (("live_tip", tip), ("sweep_base", SWEEP_BASE)):
        csrc = git("show", f"{ref}:{CONTRACT}")
        gsrc = git("show", f"{ref}:{GENERATED}")
        cs = contract_schemas(csrc)
        gs = client_schemas(gsrc)
        cset, gset = set(cs), set(gs)
        # A client-only name is not automatically drift: the generator lifts inline shapes out of the
        # contract's response bodies and names them, so a name the contract never declares can still be
        # fully grounded in it. The question that matters is whether each extra name OCCURS in the
        # contract at all; an ungrounded one is the real break.
        extras = sorted(gset - cset)
        grounded = {n: len(re.findall(r"\b" + re.escape(n) + r"\b", csrc)) for n in extras}
        entry = {"contract_schemas": len(cset), "client_schemas": len(gset),
                 "contract_only": sorted(cset - gset)[:40],
                 "client_only": extras[:40],
                 "contract_only_count": len(cset - gset),
                 "client_only_count": len(gset - cset),
                 "client_only_grounded_in_contract": len([n for n, k in grounded.items() if k]),
                 "client_only_ungrounded": sorted(n for n, k in grounded.items() if not k),
                 "grounding_hits": grounded,
                 "declared_sets_equal": cset == gset,
                 "no_ungrounded_client_names": all(grounded.values()),
                 "verdict_line": ("CLIENT_COVERS_CONTRACT_WITH_GROUNDED_EXTRAS"
                                  if not (cset - gset) and all(grounded.values())
                                  else "SHAPE_DRIFT_FOUND")}
        doc["refs"][label] = entry
        print(f"{label} contract_schemas={entry['contract_schemas']} client_schemas={entry['client_schemas']} "
              f"declared_equal={entry['declared_sets_equal']} contract_only={entry['contract_only_count']} "
              f"client_only={entry['client_only_count']} grounded={entry['client_only_grounded_in_contract']} "
              f"ungrounded={len(entry['client_only_ungrounded'])}")
        print(f"  verdict {entry['verdict_line']}")
        for n in entry["client_only_ungrounded"][:6]:
            print("  UNGROUNDED " + n)
    OUT.joinpath(f"shape_drift_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("receipt shape_drift_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
