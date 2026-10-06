"""Building C cell seven: whose tests are the pre-existing red ones? (read-only locate)

Cell six proved the full-suite red set is not the route-shape fix's. This cell answers the question the
building's last block raised -- whose are they -- by reading each red test file's own header, which names
the order and lane that owns it. It touches no assertion and writes no product bytes.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
TESTS = WT / "backend/tests"
OUT = WT / "review/ord0577/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RED = ["test_qoder_anywhere_gates.py", "test_qoder_anywhere_lock_duration.py",
       "test_qoder_anywhere_matrix_truth.py", "test_qoder_anywhere_provider_independence.py",
       "test_qoder_anywhere_provider_truth.py", "test_qoder_g3_xproc_http.py"]


def git(*a: str) -> str:
    import os
    e = dict(os.environ); e["NO_PROXY"] = "*"
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e)
    return (r.stdout or "").strip() if r.returncode == 0 else ""


def main() -> int:
    tip = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    doc = {"generation": {"run": RUN, "read_only": True, "auth_tip": tip,
                          "note": "reads each red test file's own header; changes no assertion"},
           "files": [], "verdict": None}
    for name in RED:
        p = TESTS / name
        head = p.read_text(encoding="utf-8", errors="replace")[:900]
        first = next((l.strip() for l in head.split("\n") if l.strip().startswith(('"""', "#", "'''"))), "")
        ords = sorted(set(re.findall(r"ORD-\d+", head)))
        lane = sorted(set(re.findall(r"lane\s+([A-F])", head)))
        in_tree = bool(git("ls-tree", "-r", "--name-only", tip).split("backend/tests/" + name)[-1].strip())
        doc["files"].append({"file": "backend/tests/" + name, "orders": ords, "lane_tags": lane,
                             "header_line": first[:120], "in_auth_tree": in_tree})
    mine = "6a773af1"
    owned_by_other = [f for f in doc["files"] if mine not in f["header_line"]]
    doc["counts"] = {"files": len(doc["files"]), "named_to_other_lane": len(owned_by_other)}
    doc["verdict"] = "RED_SET_OWNED_BY_OTHER_LANES" if len(owned_by_other) == len(doc["files"]) else "MIXED_OWNERSHIP"
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"red_owner_locate_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for f in doc["files"]:
        print(f"{f['file']} orders={','.join(f['orders']) or '?'} lanes={','.join(f['lane_tags']) or '?'} "
              f"in_auth={f['in_auth_tree']}")
    print(f"verdict {doc['verdict']} other_lane={len(owned_by_other)} of {len(doc['files'])}")
    print("receipt red_owner_locate_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
