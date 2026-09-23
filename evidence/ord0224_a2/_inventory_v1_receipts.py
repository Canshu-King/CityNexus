"""Read-only inventory of every CNX_REVERSE_MUTATION_RECEIPT_V1 file in this directory.

Written because F's complaint was "拿不到 scope 键": a receipt that cannot be re-read mechanically
(a different layout per emitter version) is as good as unpublished. So the inventory is the check
that all of them carry the same three keys, and it flags the ones that predate a field instead of
silently skipping them.
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path

OWN = hashlib.sha1(b"blob %d\x00" % Path("xproc_v1_gate_receipt.py").stat().st_size
                   + Path("xproc_v1_gate_receipt.py").read_bytes()).hexdigest()


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def rows() -> list[dict]:
    out = []
    for f in sorted(glob.glob("v1_gate_receipt_*.json")) + sorted(glob.glob("v1_http_receipt_*.json")):
        p = Path(f)
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema_version") != "CNX_REVERSE_MUTATION_RECEIPT_V1":
            out.append({"file": f, "problem": f"schema_version={d.get('schema_version')!r}"})
            continue
        s, dr, prov = d["scope"], d["derivation"], d.get("provenance") or {}
        runs = d["mutated_runs"]["runs"]
        out.append({
            "file": f, "bytes": p.stat().st_size, "git_blob_sha1": blob(p),
            "scope_key": {
                "exact_sha": s["exact_sha"],
                "nodeid": (s["target_nodeids"] or ["?"])[0],
                "run_shape": s["run_shape"],
                "tree_kind": s.get("tree_kind"),
                "tree_identical": all(v["identical"] for v in (s.get("tree_kind_check") or {}).values()),
            },
            "mutation_id": d["mutation"]["mutation_id"],
            "carriers_removed": d["mutation"]["carriers_removed"],
            "claimed_result": dr["claimed_result"],
            "derived_result": dr["derived_result"],
            "rounds": d["mutated_runs"]["rounds"],
            "primary_red_rounds": dr["primary_red_rounds"],
            "baseline_outcome": list(d["baseline"]["target_outcomes"].values()),
            "every_round_fresh_db": dr.get("every_round_named_a_fresh_db",
                                            all(r.get("db_fresh") for r in runs)),
            "every_round_restored": dr["every_round_restored_byte_exact"],
            "anchor_hits": sorted({a.get("anchor_hits") for r in runs for a in r.get("anchor_receipts", [])}),
            "marker_residue": sum(r["restore"].get("mutant_marker_hits_after_restore", -1) for r in runs),
            "collected": sorted({v for v in ([d["baseline"].get("this_run_collected")]
                                              + [r.get("collected") for r in runs]) if v is not None}),
            "rows_baseline": dr.get("baseline_catalog_rows"),
            "rows_mutated": dr.get("mutated_catalog_rows"),
            "has_provenance": bool(d.get("provenance")),
            "emitter_blob": prov.get("emitter_git_blob_sha1_this_file"),
            "emitter_is_current_file": prov.get("emitter_git_blob_sha1_this_file") == OWN if prov else None,
            "ruler_blob": (d["environment"].get("row_column_instrument") or {}).get("git_blob_sha1"),
        })
    return out


def main() -> int:
    rs = rows()
    print(f"emitter xproc_v1_gate_receipt.py blob now = {OWN[:16]}…  ({Path('xproc_v1_gate_receipt.py').stat().st_size} B)")
    for r in rs:
        if "problem" in r:
            print(f"!! {r['file']}: {r['problem']}")
            continue
        k = r["scope_key"]
        print(f"{r['file']}")
        print(f"    {r['bytes']:6d} B  blob {r['git_blob_sha1'][:16]}  {r['mutation_id']}")
        print(f"    key: sha={k['exact_sha'][:7]} shape={k['run_shape']} tree={k['tree_kind']}"
              f" identical={k['tree_identical']} nodeid=…{k['nodeid'][-52:]}")
        print(f"    carriers={r['carriers_removed']}")
        print(f"    claimed={r['claimed_result']} derived={r['derived_result']} reds="
              f"{len(r['primary_red_rounds'])}/{r['rounds']} {r['primary_red_rounds']}")
        print(f"    hygiene: fresh_db={r['every_round_fresh_db']} restored={r['every_round_restored']} "
              f"anchor_hits={r['anchor_hits']} marker_residue={r['marker_residue']} "
              f"collected={r['collected']} baseline={r['baseline_outcome']}")
        print(f"    rows: base={r['rows_baseline']} mutated={r['rows_mutated']}")
        print(f"    provenance={r['has_provenance']} emitter_blob="
              f"{(r['emitter_blob'] or '-')[:16]} is_current={r['emitter_is_current_file']} "
              f"ruler={(r['ruler_blob'] or '-')[:16]}")
    keys = sorted({x['scope_key']['exact_sha'][:7] + '|' + x['scope_key']['run_shape']
                   for x in rs if 'scope_key' in x})
    print(json.dumps({"count": len(rs), "distinct_scope_keys": keys}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
