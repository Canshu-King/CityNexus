"""Repeat the three nodeids that differ between trees, isolated, several times each side.

A red that is mine must be reliably reproducible on the candidate and absent on the base.  A red
that moves around between rounds on the SAME tree is not attributable to any commit.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import time

VENV_PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
ROOT = pathlib.Path("D:/moodle")
OUT = ROOT / "_qoder_n2_ord0355_r2/review/ord0355-r2-readings"
TREE = {"cand": ROOT / "_qoder_n2_ord0355_r2", "base": ROOT / "_qoder_n2_ord0355_base7e7"}

NODES = [
    "tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation",
    "tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
    "tests/test_qoder_ord197_four_class_receipt.py::test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage",
    "tests/test_sol_guardian_projection.py::test_guardian_status_lists_runs_newest_first",
]

FAILED = re.compile(r"^(?:FAILED|ERROR) (\S+::\S+)", re.M)
PASSED = re.compile(r"^(\d+) passed", re.M)


def one(which: str, node: str, attempt: int) -> dict:
    backend = TREE[which] / "backend"
    db = backend / f"_probe_{which}_{attempt}.db"
    if db.exists():
        db.unlink()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        str(p) for p in (backend, backend.parent / "agent-mcp", backend.parent)
    )
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        env.pop(name, None)
    started = time.time()
    proc = subprocess.run(
        [VENV_PY, "-m", "pytest", "-q", "-p", "no:randomly", node],
        cwd=str(backend), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    log = OUT / f"probe_{which}_a{attempt}.log"
    log.write_text(out, encoding="utf-8", newline="\n")
    passed = PASSED.search(out)
    return {
        "tree": which,
        "attempt": attempt,
        "node": node,
        "exit_code": proc.returncode,
        "wall_seconds": round(time.time() - started, 2),
        "passed_count": int(passed.group(1)) if passed else 0,
        "red": bool(FAILED.findall(out)) or proc.returncode != 0,
        "log": log.as_posix(),
        "log_sha1": hashlib.sha1(log.read_bytes()).hexdigest(),
    }


def main() -> int:
    rows = []
    for attempt in (1, 2, 3):
        for which in ("cand", "base"):
            for node in NODES:
                row = one(which, node, attempt)
                rows.append(row)
                short = node.split("::")[1][:46]
                print(f"a{attempt} {which:4s} {'RED ' if row['red'] else 'GREEN'} {short}", flush=True)
                (OUT / "probe_readings.json").write_text(
                    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
                )
    print()
    for node in NODES:
        for which in ("cand", "base"):
            hits = [r["red"] for r in rows if r["node"] == node and r["tree"] == which]
            print(f"{which:4s} red {sum(hits)}/{len(hits)}  {node.split('::')[1][:52]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
