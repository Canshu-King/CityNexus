#!/usr/bin/env python3
"""ORD-0440 - do the survey's own checks actually bite? (mutation arms, restored by bytes)

A gate that stays green when the thing it names is removed is not a gate. Each arm below edits ONE
product file, rebuilds the bundle this lane serves, re-runs the traveller walk, and records which
named checks went red. Afterwards the file is restored and compared by sha1 against the bytes it
started from, and the bundle is rebuilt clean, so no arm leaves a residue behind.

    python review/ord0440/mutations_r1.py <worktree> <preview-base> <reset-token> <out-json>
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:49970"
TOKEN = sys.argv[3] if len(sys.argv) > 3 else ""
OUT = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "review/n3_0440_evidence_r1/mutations_r1.json"
PANEL = ROOT / "frontend/src/features/discovery/DestinationPreparationPanel.tsx"
SHEET = ROOT / "frontend/src/features/discovery/PrepAbandonSurvey.tsx"
WALK = ROOT / "review/ord0440/walk_r1.cjs"
VITE = str(ROOT / "frontend/node_modules/vite/bin/vite.js")


def sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)


def build() -> dict:
    proc = run(["node", VITE, "build"], cwd=ROOT / "frontend")
    return {"rc": proc.returncode, "tail": (proc.stdout or "")[-160:] + (proc.stderr or "")[-160:]}


def walk() -> dict:
    proc = run(["node", str(WALK), BASE, TOKEN, str(ROOT / "review/n3_0440_evidence_r1/walk"), "zh-CN"])
    out = proc.stdout or ""
    red = re.findall(r"^  RED (.+?) \{", out, re.M)
    crash = "WALK_CRASH" in out
    summary = re.search(r"checks=(\d+) pass=(\d+) fail=(\d+)", out)
    return {
        "rc": proc.returncode,
        "checks": int(summary.group(1)) if summary else None,
        "pass": int(summary.group(2)) if summary else None,
        "fail": int(summary.group(3)) if summary else None,
        "named_reds": red,
        "crashed_before_the_sheet_mounted": crash,
        "stdout_tail": out[-300:],
    }


ARMS = [
    {
        "name": "M1 the sheet is bypassed and the button stops the job directly",
        "file": PANEL,
        "find": '                onClick={openSurvey}',
        "replace": '                onClick={() => void abandon()}',
        "expect": "the walk cannot mount the sheet, so it must not pass",
    },
    {
        "name": "M2 the exit changes its mouth (继续 instead of the act's own words)",
        "file": SHEET,
        "find": "          {copy(zh, STOP_ACTION_KEY)}",
        "replace": '          {zh ? "继续" : "Continue"}',
        "expect": "G3 must go red while every other check stays green",
    },
    {
        "name": "M3 the survey blocks the act when nothing is picked",
        "file": SHEET,
        "find": "          disabled={busy}\n          onClick={() => onExit(picked, note)}",
        "replace": "          disabled={busy || picked.length === 0}\n          onClick={() => onExit(picked, note)}",
        "expect": "G4's 'the survey never blocks the destructive act' must go red",
    },
]


def main() -> int:
    originals = {path: (path.read_bytes(), hashlib.sha1(path.read_bytes()).hexdigest())
                 for path in {a["file"] for a in ARMS}}
    results = []
    for arm in ARMS:
        path = arm["file"]
        raw, before = originals[path]
        text = raw.decode("utf-8")
        if arm["find"] not in text:
            # An arm that cannot be applied is not a passed arm: it means the gate's bite is unmeasured.
            results.append({**{k: arm[k] for k in ("name", "expect")}, "applied": False,
                            "note": "ANCHOR_NOT_FOUND - this arm never ran and proves nothing"})
            continue
        path.write_bytes(text.replace(arm["find"], arm["replace"], 1).encode("utf-8"))
        built = build()
        reading = walk() if built["rc"] == 0 else {"rc": None, "skipped": "build failed"}
        path.write_bytes(raw)
        results.append({
            "name": arm["name"], "expect": arm["expect"], "applied": True,
            "build": built, "walk": reading,
            "restored_byte_identical": sha(path) == before,
        })
        if results[-1]["restored_byte_identical"] is not True:
            print("RESTORE FAILED for", path)
            break

    final_build = build()
    still_clean = all(sha(p) == h for p, (_, h) in originals.items())
    unapplied = [r["name"] for r in results if not r.get("applied")]
    payload = {
        "arms": results,
        "clean_rebuild_after_restoring": final_build,
        "all_files_back_at_their_starting_bytes": still_clean,
        "arms_that_never_ran": unapplied,
        "sha1_of_product_files_after_the_campaign": {
            str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in originals
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("arms", len(results), "restored_clean", still_clean, "build_rc", final_build["rc"],
          "unapplied", len(unapplied))
    for r in results:
        w = r.get("walk") or {}
        print(" ", r["name"][:58], "| applied", r.get("applied"), "| rc", w.get("rc"),
              "| fail", w.get("fail"), "| reds", [x[:34] for x in w.get("named_reds", [])][:3],
              "| restored", r.get("restored_byte_identical"))
    return 1 if (unapplied or not still_clean or final_build["rc"] != 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
