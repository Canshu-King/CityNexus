"""Run ORD-0280's arms against the PRE-FIX component, so the arms' teeth are on the record.

An arm that passes is worth nothing until it is shown to fail on the shape it forbids.  This swaps
`PlanWithAiSheet.tsx` back to its committed (unfixed) bytes, runs the spec, and restores my working version
in a `finally` - verifying the restored digest, because a script that leaves the lane dirty behind it is the
second-worst thing it can do after lying about the reading.

Nothing here changes what is committed: the unfixed version is simply `git show HEAD:<path>`.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
FE = LANE / "frontend"
REL = "frontend/src/features/planning/PlanWithAiSheet.tsx"
TARGET = FE / "src/features/planning/PlanWithAiSheet.tsx"
BACKUP = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0280_fixed_backup.tsx")
OUT = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924\ord0280_teeth_prefix.out")
SPEC = "e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts"
RUN_ID = os.environ.get("CNX_TEETH_RUN_ID") or "ord0280h"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    fixed = sha(TARGET)
    shutil.copy2(TARGET, BACKUP)
    head_bytes = subprocess.run(["git", "-C", str(LANE), "show", f"HEAD:{REL}"],
                                capture_output=True).stdout
    if not head_bytes:
        print("ABORT: `git show HEAD:` handed back nothing - refusing to run without the pre-fix bytes")
        return 2
    print(f"fixed working copy sha {fixed[:16]}")
    print(f"pre-fix (HEAD)     sha {hashlib.sha256(head_bytes).hexdigest()[:16]}")
    if fixed == hashlib.sha256(head_bytes).hexdigest():
        print("ABORT: working copy already equals HEAD - there is no fix to test against")
        return 2
    try:
        TARGET.write_bytes(head_bytes)
        print("swapped to the UNFIXED component; running the arms (they must fail)")
        env = dict(os.environ)
        env.update({
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_PORT": os.environ.get("CNX_TEETH_FE_PORT") or "4377",
            "CITYNEXUS_BACKEND_PORT": os.environ.get("CNX_TEETH_BE_PORT") or "8127",
            "CITYNEXUS_PYTHON": r"D:\moodle\CityNexus\.venv\Scripts\python.exe",
            "CITYNEXUS_E2E_RUN_ID": RUN_ID,
            # forward slashes: the backend reports the URI it was handed, and the provenance hook compares
            # it by basename — a backslash path made it echo a full Windows path and the hook refused.
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + (LANE / "backend" / ("_" + RUN_ID + ".db"))
                .as_posix().replace(":", ":"),
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": str(OUT.parent / "e2e_prefix"),
        })
        for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
            env.pop(k, None)
        r = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                            "-c", "playwright.config.ts", SPEC, "--reporter=line"],
                           cwd=str(FE), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        text = (r.stdout or "") + (r.stderr or "")
        keep = [ln for ln in text.splitlines()
                if not ln.startswith("[WebServer]") and ln.strip()]
        OUT.write_text("\n".join(keep), "utf-8", newline="\n")
        failed = [ln for ln in keep if "FAILED" in ln or "want" in ln and "label" in ln]
        tail = [ln for ln in keep if " passed" in ln or " failed" in ln]
        print("   ", (tail or ["no tally line"])[-1])
        for ln in keep:
            if '"want"' in ln and "FAILED" in ln:
                print("   teeth:", ln[ln.index("FAILED"):][:170])
        print(f"   rc={r.returncode} (non-zero is the POINT of this run) evidence={len(failed)} label lines")
        if r.returncode == 0:
            print("   PROBLEM: the arms passed against the UNFIXED component -> they are vacuous")
    finally:
        TARGET.write_bytes(BACKUP.read_bytes())
        now = sha(TARGET)
        print("restored fixed working copy:", now[:16], "== expected", fixed[:16], ":", now == fixed)
        dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src"],
                               capture_output=True, text=True).stdout.strip()
        print("frontend/src now:", repr(dirty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
