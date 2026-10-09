"""Re-pin the ORD-0326 field-arrival table onto a newer authoritative tip.

Nothing here re-judges anything: it imports the published citation table out of
_ord0326_fields_r2.py and re-runs it, unchanged, against an export of the new tip.
A citation that moved raises SystemExit, which is the whole point of re-reading.

Usage:
  python -X utf8 _ord0326_fields_repin_r1.py --repo D:/moodle/CityNexus \
      --old <sha> --new <sha> --export <dir-of-new-tip> --out <file>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSTRUMENT = HERE / "_ord0326_fields_r2.py"


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"ABORT git {' '.join(args)} rc={r.returncode} {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def load(repin_tip: str):
    spec = importlib.util.spec_from_file_location("far2", INSTRUMENT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # The instrument's own bytes stay as published; only the generation string it stamps moves,
    # and that is declared in the output rather than hidden.
    mod.TIP = repin_tip
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--export", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    mod = load(a.new)
    paths = sorted({c["path"] for c in mod.CITES})

    unchanged, changed = [], []
    for p in paths:
        try:
            before = git(a.repo, "rev-parse", f"{a.old}:{p}")
            after = git(a.repo, "rev-parse", f"{a.new}:{p}")
        except SystemExit as exc:
            changed.append({"path": p, "old": "ABSENT", "new": str(exc)})
            continue
        (unchanged if before == after else changed).append(
            {"path": p, "old": before, "new": after})

    # Re-run every citation against the new export.  A single moved line aborts the run.
    doc = mod.build(Path(a.export))
    re_cited = sum(f["cite_count"] for f in doc["allowed_fields"].values()) + doc["reachability_count"]

    out = {
        "schema": "CNX_FIELD_ARRIVAL_REPIN_V1",
        "instrument": {
            "local": INSTRUMENT.name,
            "published_path": "evidence/ord0326-server-reason-S1/field_arrival_builder_r2.py",
            "published_blob": "64ec7d8af049f8d2311147d56ba67789ca8d874e",
            "instrument_bytes_rewritten": 0,
            "generation_field_override": "the driver sets the module's TIP constant to --new; "
                                         "no citation, verdict or expectation was edited",
        },
        "old_generation": a.old,
        "new_generation": a.new,
        "read_how": "git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1",
        "repinned_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cited_file_count": len(paths),
        "cited_files_unchanged": unchanged,
        "cited_files_changed": changed,
        "unchanged_count": len(unchanged),
        "changed_count": len(changed),
        "all_citations_pass_at_new_tip": True,
        "re_cited_line_count": re_cited,
        "verdicts_at_new_tip": {f: v["verdict"] for f, v in doc["allowed_fields"].items()},
        "not_emitted_at_new_tip": doc["not_emitted"],
        "census_at_new_tip": doc["census"],
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", a.out, "bytes", Path(a.out).stat().st_size)
    print(f"  cited files {len(paths)} unchanged {len(unchanged)} changed {len(changed)}")
    print(f"  citations re-passed at the new tip: {re_cited}")
    for c in changed:
        print("  CHANGED", c["path"], c["old"][:10], "->", c["new"][:10])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
