"""Counter-arms for ORD-0545 slice 3: the refusal-on-glass arms have to bite.

Two single-variable mutations, both restored from the bytes read at the start and re-hashed:

  M1  repoint FAILURE_SENTENCE's NO_ACTIVE_PLAN entry at another key that really exists in the table
      (`errUnnamed`).  The build stays green -- both names are in the union -- so if the arm is only
      reading whatever the screen paints, it should now see the *other* sentence and go red on the
      byte-for-byte comparison.  This is the difference between "the screen shows a sentence" and
      "the screen shows the sentence this refusal maps to".

  M2  paste a name this city's catalogue does not hold.  The parse then returns no addable row, and the
      arm must refuse to walk on: it may not claim a refusal it never reached.  Red here proves the
      arm's antecedent is checked, not assumed.

Control runs of the three arms bracket the mutations; the pair of green controls also proves the
restore.  Mutant-generation JSON evidence is deliberately NOT published -- it describes a tree that
does not ship -- so the tags used here are thrown away and the console readings below are the artifact.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/refusal_glass_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
SPEC = FRONTEND / "e2e/qoder-ord0545s3-refusal-on-glass-r1.spec.ts"
READOUTS = FRONTEND / ".." / "review" / "ord0545" / "readouts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
BASE_TIP = "569b8472b134e5562ef396e38681870b9c26536a"
CONFIG = "playwright.ord0545s3-refusal.config.ts"

PANEL_FROM = '  NO_ACTIVE_PLAN: "errNoActivePlan",'
PANEL_TO = '  NO_ACTIVE_PLAN: "errUnnamed",'
SPEC_FROM = 'const PASTED = "Central Food Hall";'
SPEC_TO = 'const PASTED = "Zzzyx not a place in this catalogue";'


def gate(tag: str) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_ORD0545_TAG": tag,
        "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
        "CITYNEXUS_ORD0545S3_PORT": "4915",
        "CITYNEXUS_ORD0545_BACKEND_PORT": "4911",
        "DEEPSEEK_API_KEY": "",
    })
    done = subprocess.run(
        ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG],
        cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=1200, env=env,
    )
    out = (done.stdout or "") + (done.stderr or "")
    collected = re.search(r"Running (\d+) tests", out)
    passed = re.search(r"(\d+) passed", out)
    failed = re.search(r"(\d+) failed", out)
    return {
        "rc": done.returncode,
        "tests_collected": int(collected.group(1)) if collected else 0,
        "passed": int(passed.group(1)) if passed else 0,
        "failed": int(failed.group(1)) if failed else 0,
        "red_lines": [ln.strip()[:150] for ln in out.splitlines() if ln.lstrip().startswith("x ")],
    }


def swap(path: pathlib.Path, old: str, new: str) -> bytes:
    original = path.read_bytes()
    text = original.decode("utf-8")
    assert old in text, f"{old!r} is not in {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    return original


def main() -> int:
    panel_before = PANEL.read_bytes()
    spec_before = SPEC.read_bytes()
    log: list[str] = [f"base_tip={BASE_TIP}", f"panel_sha={hashlib.sha256(panel_before).hexdigest()}",
                      f"spec_sha={hashlib.sha256(spec_before).hexdigest()}", ""]

    control_pre = gate("ctrlpre")
    log.append(f"control_pre: {control_pre}")

    # M1: mapping repointed to another real table key -- the build must stay green, the arm must go red.
    original = swap(PANEL, PANEL_FROM, PANEL_TO)
    tsc = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"],
        cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    m1 = gate("mutm1")
    PANEL.write_bytes(original)
    m1_restored = hashlib.sha256(PANEL.read_bytes()).hexdigest() == hashlib.sha256(panel_before).hexdigest()
    log.append(f"M1 tsc_rc={tsc.returncode} (green on purpose: both names are in the union)")
    log.append(f"M1 {m1} restored={m1_restored}")

    # M2: the arm must not walk into a refusal it never reached.
    original = swap(SPEC, SPEC_FROM, SPEC_TO)
    m2 = gate("mutm2")
    SPEC.write_bytes(original)
    m2_restored = hashlib.sha256(SPEC.read_bytes()).hexdigest() == hashlib.sha256(spec_before).hexdigest()
    log.append(f"M2 {m2} restored={m2_restored}")

    control_post = gate("ctrlpost")
    log.append(f"control_post: {control_post}")

    # Throw away the mutant-generation artifacts; only the control generations describe this tree.
    for tag in ("ctrlpre", "mutm1", "mutm2", "ctrlpost"):
        for path in (ROOT / "review/ord0545/readouts").glob(f"*_{tag}.json"):
            path.unlink()

    verdict = (
        control_pre["rc"] == 0 and control_pre["tests_collected"] == 3
        and m1["rc"] != 0 and m1["tests_collected"] == 3 and m1_restored
        and m2["rc"] != 0 and m2["tests_collected"] == 3 and m2_restored
        and control_post["rc"] == 0 and control_post["tests_collected"] == 3
    )
    log += ["", f"verdict = {'KILL_OK both mutations' if verdict else 'NOT_PROVEN'}"]
    out = DATA / "refusal_glass_counterarms.txt"
    out.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(log[-6:]))
    print(f"log={out}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
