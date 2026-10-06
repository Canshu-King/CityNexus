"""ORD-0556 follow-up, ninth leg: is the gap between the two generations front-end only, or full stack?

Leg eight named five route keys the live tip does not carry. A screen can be missing while its API stays
(dead surface) or the whole feature can be missing. This counts the same five families on the server side
at both refs, plus three whole-tree sizes, read-only.
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
MAIN = "backend/app/main.py"
CONTRACT = "contracts/openapi.yaml"
DECO = re.compile(r"@app\.(?:get|post|put|delete|patch)")
FAMILIES = {
    "trash": ["/api/v1/recycle-bin/journeys"],
    "access": ["/members", "/member-role-limits"],
    "shared": ["/api/v1/shared/journeys/"],
    "import": ["/poi-import/parse"],
    "footprints": ["/checkins"],
}
STILL_THERE = {"import": ["/inbox/import"]}


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


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    refs = {"live_tip": tip, "sweep_base": SWEEP_BASE}
    doc: dict = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE,
                                "read_only": True, "refs": {}}, "verdict": "STACK_SHRINK_READ"}
    for label, ref in refs.items():
        # splitlines(), not split("\n"): the file ends with a newline, so splitting on the newline yields a
        # trailing empty element and reports one line more than the file has (9762 where it is 9761).
        main_src = git("show", f"{ref}:{MAIN}").splitlines()
        try:
            contract = git("show", f"{ref}:{CONTRACT}").splitlines()
        except SystemExit:
            contract = []
        entry = {"ref": ref,
                 "paths_total": len([p for p in git("ls-tree", "-r", "--name-only", ref).split("\n") if p.strip()]),
                 "main_py_lines": len(main_src),
                 "route_decorators": len([l for l in main_src if DECO.search(l)]),
                 "contract_lines": len(contract),
                 "families": {}, "still_there": {}}
        for fam, needles in FAMILIES.items():
            hits = {n: len([l for l in main_src if n in l]) for n in needles}
            entry["families"][fam] = {"needles": needles, "hits": hits,
                                      "present": any(v > 0 for v in hits.values())}
        for fam, needles in STILL_THERE.items():
            entry["still_there"][fam] = {n: len([l for l in main_src if n in l]) for n in needles}
        doc["generation"]["refs"][label] = entry

    live, old = doc["generation"]["refs"]["live_tip"], doc["generation"]["refs"]["sweep_base"]
    doc["endpoints_lost"] = sorted(f for f, v in old["families"].items()
                                   if v["present"] and not live["families"][f]["present"])
    doc["endpoints_kept"] = sorted(f for f, v in live["families"].items() if v["present"])
    OUT.joinpath(f"stack_shrink_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"live_tip={tip} sweep_base={SWEEP_BASE}")
    for label, e in doc["generation"]["refs"].items():
        print(f"{label} paths={e['paths_total']} main_py_lines={e['main_py_lines']} "
              f"route_decorators={e['route_decorators']} contract_lines={e['contract_lines']}")
    for fam in FAMILIES:
        o, n = old["families"][fam], live["families"][fam]
        print(f"family {fam} sweep_present={o['present']} live_present={n['present']} "
              f"sweep_hits={sum(o['hits'].values())} live_hits={sum(n['hits'].values())}")
    for fam, hits in live["still_there"].items():
        print(f"still_there {fam} " + " ".join(f"{k}={v}" for k, v in hits.items()))
    print("endpoints_lost=" + ",".join(doc["endpoints_lost"]))
    print("receipt stack_shrink_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
