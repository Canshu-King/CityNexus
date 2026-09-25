"""Publish the staged ORD-0310 set through the identical-or-refuse gate, one named file at a time.

This is deliberately not a `--local-dir` publisher (that is the shape that swept 11 junk files into a
shared evidence directory on ORD-0308): the loop walks the published-name list from
`ord0310_pub_names.py`, refuses to run if the staging folder holds anything that is not on that list,
and each PUT goes through `gated_push.py`, which skips identical bytes and refuses changed bytes
under an already-published name.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "D:/moodle/_qoder_d_lane_20260923/review")
from ord0310_pub_names import DIRNAME, PUB  # noqa: E402

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
PUB_DIR = ROOT / "_scratch_0310" / "pub"
GATED = "D:/moodle/HJ-P3_evidence/gated_push.py"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
LOG = ROOT / "_scratch_0310" / ("ord0310-publish-log" + (sys.argv[1] if len(sys.argv) > 1 else "") + ".json")
ONLY = sys.argv[2:] if len(sys.argv) > 2 else None


def main() -> int:
    names = sorted(p.name for p in PUB_DIR.iterdir() if p.is_file())
    unknown = [n for n in names if n not in set(PUB.values())]
    if unknown:
        print(f"ABORT: staged files that are not in the published-name list: {json.dumps(unknown)}")
        return 2
    todo = [n for n in names if (ONLY is None or n in ONLY)]
    out = {}
    for name in todo:
        res = subprocess.run([PY, GATED, str(PUB_DIR / name), f"{DIRNAME}/{name}",
                              f"ORD-0310 (D e345b9d6): {name}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        text = (res.stdout or "") + (res.stderr or "")
        fresh = "FRESH" in text
        ident = "SKIP" in text
        proof = [l for l in text.splitlines() if "PROOF" in l or "MATCH" in l]
        refuse = [l for l in text.splitlines() if "REFUSE" in l]
        out[name] = {"exit": res.returncode, "fresh_path": fresh, "identical_skipped": ident,
                     "refused": refuse, "proof_line": proof[0] if proof else text.strip()[-200:],
                     "bytes": (PUB_DIR / name).stat().st_size}
        print(f"{name}: rc={res.returncode} fresh={fresh} skip={ident} "
              f"{'MATCH' if proof else ('REFUSE' if refuse else 'NO PROOF LINE')}")
    LOG.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    bad = [n for n, v in out.items() if v["exit"] != 0 or v["refused"]]
    print(f"attempted={len(out)} refused_or_nonzero={json.dumps(bad)} log={LOG}")
    return 0 if not bad else 3


raise SystemExit(main())
