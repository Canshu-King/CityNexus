"""Derive ORD0355_R2_RECEIPT.md from the run receipts - every number parsed back out of its log.

Nothing here is typed from memory: the table is built from `readings.json`, `probe_readings.json`
and `g3_readings.json`, each of which was written by the run it describes, and each row carries the
sha1 of the raw log it came from.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

D = pathlib.Path("D:/moodle/_qoder_n2_ord0355_r2/review/ord0355-r2-readings")


def load(name: str) -> list[dict]:
    return json.loads((D / name).read_text(encoding="utf-8"))


def main() -> int:
    runs = {r["run_id"]: r for r in load("readings.json")}
    probe = load("probe_readings.json")
    g3 = load("g3_readings.json")

    lines: list[str] = []
    lines.append("# ORD-0355 r2 readings - derived, not typed")
    lines.append("")
    lines.append("Interpreter: D:/moodle/CityNexus/.venv/Scripts/python.exe (Python 3.12.14).")
    lines.append("Command form: `python -m pytest -q -p no:randomly [args]`, cwd `<tree>/backend`,")
    lines.append("PYTHONPATH=`<tree>/backend;<tree>/agent-mcp;<tree>`,")
    lines.append("CITYNEXUS_DATABASE_URL=`sqlite:///<tree>/backend/<_*.db>` (removed before each run).")
    lines.append("Candidate tree `D:/moodle/_qoder_n2_ord0355_r2` HEAD 6fd43627e717a97ea779da866eb4546b8acb9deb;")
    lines.append("base tree `D:/moodle/_qoder_n2_ord0355_base7e7` HEAD 7e728268a90c9d0f4accc7f117af1de73f65bc7a.")
    lines.append("")
    lines.append("## Named runs")
    lines.append("")
    lines.append(
        "| run_id | tree | collected | failed | passed | skipped | xfailed | exit | wall_s | db | raw log sha1 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for rid in sorted(runs):
        r = runs[rid]
        tail = r["tail_line"] or ""

        def num(pat: str, default: str = "-") -> str:
            m = re.search(pat, tail)
            return m.group(1) if m else default

        passed = num(r"(\d+) passed")
        skipped = num(r"(\d+) skipped")
        xfailed = num(r"(\d+) xfailed")
        failed_cell = str(len(r["failed_nodeids"])) if r["failed_nodeids"] else num(r"(\d+) failed", "0")
        db_name = pathlib.PurePath(r["database"]).name
        lines.append(
            f"| {rid} | {r['tree']} | {r['collected'] if r['collected'] is not None else '-'} "
            f"| {failed_cell} | {passed} | {skipped} "
            f"| {xfailed} | {r['exit_code']} | {r['wall_seconds']} "
            f"| {db_name} | {r['log_sha1']} |"
        )
    lines.append("")
    lines.append("## Red nodeids per full-suite run")
    for rid in ("N2R2-D", "N2R2-E", "N2R2-G"):
        r = runs[rid]
        lines.append("")
        lines.append(f"- {rid} ({r['tree']}, log {r['log_sha1']}): {len(r['failed_nodeids'])} rows")
        for node in sorted(r["failed_nodeids"]):
            lines.append(f"  - {node}")

    stable = set(runs["N2R2-D"]["failed_nodeids"]) & set(runs["N2R2-E"]["failed_nodeids"]) & set(
        runs["N2R2-G"]["failed_nodeids"]
    )
    lines.append("")
    lines.append(
        f"## Stable across both trees: {len(stable)} nodeids (red in N2R2-D, N2R2-E and N2R2-G)"
    )
    for node in sorted(stable):
        lines.append(f"- {node}")

    lines.append("")
    lines.append("## Differing nodeids, isolated repeats")
    lines.append("")
    lines.append("| nodeid | cand red/attempts | base red/attempts | raw log sha1 (first red seen) |")
    lines.append("|---|---|---|---|")
    nodes = []
    for r in probe:
        if r["node"] not in nodes:
            nodes.append(r["node"])
    for node in nodes:
        c = [r for r in probe if r["node"] == node and r["tree"] == "cand"]
        b = [r for r in probe if r["node"] == node and r["tree"] == "base"]
        first_red = next((r["log_sha1"] for r in c + b if r["red"]), "-")
        lines.append(
            f"| {node.split('backend/')[-1]} | {sum(1 for r in c if r['red'])}/{len(c)} "
            f"| {sum(1 for r in b if r['red'])}/{len(b)} | {first_red} |"
        )
    g3c = [r for r in g3 if r["tree"] == "cand"]
    g3b = [r for r in g3 if r["tree"] == "base"]
    lines.append(
        f"| tests/test_qoder_anywhere_gates.py::test_g3_xproc_loser_readback_five_processes_one_operation "
        f"(6 more per side) | {sum(1 for r in g3c if r['red'])}/{len(g3c)} "
        f"| {sum(1 for r in g3b if r['red'])}/{len(g3b)} "
        f"| {next((r['log_sha1'] for r in g3c + g3b if r['red']), 'none red')} |"
    )

    lines.append("")
    lines.append("## Set arithmetic (computed above from the rows in this file)")
    cand_union = set(runs["N2R2-D"]["failed_nodeids"]) | set(runs["N2R2-E"]["failed_nodeids"])
    base = set(runs["N2R2-G"]["failed_nodeids"])
    lines.append(f"- candidate(D|E) minus base(G) = {len(cand_union - base)} nodeids:")
    for node in sorted(cand_union - base):
        lines.append(f"  - {node}")
    lines.append(f"- base(G) minus candidate(D&E) = {len(base - (set(runs['N2R2-D']['failed_nodeids']) & set(runs['N2R2-E']['failed_nodeids'])))} nodeids:")
    for node in sorted(base - (set(runs["N2R2-D"]["failed_nodeids"]) & set(runs["N2R2-E"]["failed_nodeids"]))):
        lines.append(f"  - {node}")

    text = "\n".join(lines) + "\n"
    out = D / "ORD0355_R2_RECEIPT.md"
    out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", out.as_posix(), len(text.encode('utf-8')), "bytes")
    print("sha1", hashlib.sha1(out.read_bytes()).hexdigest())
    print(text[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
