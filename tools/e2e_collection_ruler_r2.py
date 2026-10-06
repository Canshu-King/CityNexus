#!/usr/bin/env python3
"""ORD-0576 ruler: which specs make the acceptance gate collect nothing, and does the gate collect at all.

Ground truth, not source guessing. The first attempt at this ruler scanned spec text for module-scope
`throw`/`readFileSync` with an indent-zero regex, which also matched `import { readFileSync } ...` and
accused ten compliant files -- a ruler that cries wolf is worse than no ruler. This one asks Playwright
itself, via `--list`, which is exactly the thing ORD-0576 is about: collection.

Two arms:
  collect  -- one whole-directory `--list` under the real gate config; every import error it prints names
             one spec. The set must equal the named debt, so a new offender is red and a fixed spec that
             is still listed is red too.
  skips    -- a skipped test must carry a reason, because `test.skip(cond)` with no second argument turns
             an unmet prerequisite into a quiet pass-shaped line.

Exit codes: 0 clean, 1 a named arm failed, 2 the instrument could not measure (never a silent pass).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Specs that still abort collection. Each row is a file the gate cannot load, not a judgement about its
# author: the fix is to move the prerequisite inside a test as a named skip (ORD-0576).
DEBT = {
    "qoder-e766b154-checkin-words-real-door-r1.spec.ts",
    "qoder-ord0498-poster-multiday.spec.ts",
    "qoder-ord0501-poster-day-seams.spec.ts",
    "qoder-ord0515-poster-pagination.spec.ts",
    "qoder-ord0525-entry-reachability-r3.spec.ts",
    "qoder-ord0528-poster-share.spec.ts",
    "qoder-ord0541-share-idempotent.spec.ts",
    "qoder-ord0542-poster-day-line.spec.ts",
    "qoder-ord0545-family-words-r1.spec.ts",
    "qoder-ord0545s3-refusal-on-glass-r1.spec.ts",
    "qoder-ord0545s4-poi-screen-walkthrough-r1.spec.ts",
    "qoder-ord0545s6-copy-cells-r1.spec.ts",
}

BARE_SKIP = re.compile(r"test\.skip\(\s*[A-Za-z0-9_.$\[\]'\" ]+\s*\)\s*;")
TOTAL = re.compile(r"^Total:\s*(\d+) tests? in (\d+) files?")
AT = re.compile(r"^(\s+)?at (\S+\.spec\.ts):\d+")


def run_list(frontend: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["npx", "playwright", "test", "--config", "playwright.config.ts", "--list"],
        cwd=frontend, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def offenders(out: str) -> set[str]:
    found = set()
    for line in out.splitlines():
        m = AT.match(line)
        if m:
            found.add(Path(m.group(2)).name)
    return found


def arm_collect(frontend: Path) -> dict:
    rc, out = run_list(frontend)
    total = TOTAL.search(out.strip().splitlines()[-1] if out.strip() else "")
    got = offenders(out)
    unjudged = sorted(got - DEBT)
    stale = sorted(DEBT - got)
    notes = [l for l in out.splitlines() if "Error" in l][:3]
    ok = bool(total) and int(total.group(1)) > 0 and not unjudged and not stale
    return {
        "arm": "collect", "ok": ok, "list_exit": rc,
        "tests_collected": int(total.group(1)) if total else 0,
        "files_collected": int(total.group(2)) if total else 0,
        "offenders": len(got), "unjudged": unjudged, "stale_debt": stale,
        "first_error_lines": notes,
    }


def arm_skips(frontend: Path) -> dict:
    bad = []
    for spec in sorted((frontend / "e2e").glob("*.spec.ts")):
        text = spec.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if BARE_SKIP.search(line):
                bad.append(f"{spec.name}:{n}: {line.strip()[:70]}")
    return {"arm": "skips", "ok": not bad, "bare_skips": bad[:10], "count": len(bad)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frontend", default=str(Path(__file__).resolve().parents[1] / "frontend"))
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    frontend = Path(a.frontend)
    if not (frontend / "playwright.config.ts").exists():
        print(f"ABORT: no gate config at {frontend}", file=sys.stderr)
        return 2
    results = [arm_collect(frontend), arm_skips(frontend)]
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
