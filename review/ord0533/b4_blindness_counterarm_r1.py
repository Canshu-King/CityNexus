"""Counter-check for the arm I just repaired: does B4 actually see the moved family now?

Before this round B4's union reader stopped at a semicolon inside my own comment, so it looked at 15
entries and reported "0 missing halves" on a table of 67 -- green because blind.  This script puts the
blindness back on purpose: it deletes the English half of one of the 52 moved sentences (`verifyWarning`)
and requires B4 to go red naming it.  The file is restored from the bytes read at the start and
re-hashed, and a control run afterwards has to be green again.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0533/b4_blindness_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
TABLE = FRONTEND / "src/features/poiimport/poiImportCopy.ts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
BASE_TIP = "e7ff7938ea41c5ac69afb1172acc4625159c7911"
VICTIM = "verifyWarning"
EN_LINE = '    en: "These matches are our guess'

import os

TAG = os.environ.get("CITYNEXUS_B4_COUNTER_TAG", "r8counter")


def gate(tag: str) -> tuple[int, str]:
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_ORD0533_TAG": tag,
            "CITYNEXUS_ORD0533_BASE_TIP": BASE_TIP,
            "CITYNEXUS_ORD0533_PORT": "4913",
            "CITYNEXUS_ORD0533_BACKEND_PORT": "4911",
            "DEEPSEEK_API_KEY": "",
        }
    )
    done = subprocess.run(
        ["node", "node_modules/@playwright/test/cli.js", "test", "-c", "playwright.ord0533-copygate.config.ts"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        env=env,
    )
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def main() -> int:
    original = TABLE.read_bytes()
    digest_before = hashlib.sha256(original).hexdigest()
    rc, out = gate(f"{TAG}_control_pre")
    pre_green = rc == 0
    lines = original.decode("utf-8").split("\n")
    keep, dropped = [], None
    inside = False
    for line in lines:
        if line.strip().startswith(f"{VICTIM}: {{"):
            inside = True
        if inside and dropped is None and line.startswith(EN_LINE):
            dropped = line
            inside = False
            continue
        keep.append(line)
    if dropped is None:
        print("ABORT: the victim line is not where this script thinks it is", flush=True)
        return 2
    TABLE.write_text("\n".join(keep), encoding="utf-8", newline="\n")
    mutant_rc, mutant_out = gate(TAG)
    named = VICTIM in mutant_out
    TABLE.write_bytes(original)
    restored = hashlib.sha256(TABLE.read_bytes()).hexdigest() == digest_before
    post_rc, _ = gate(f"{TAG}_control_post")
    log = DATA / f"b4_counterarm_{TAG}.txt"
    log.write_text(
        "\n".join(
            [
                f"base_tip={BASE_TIP}",
                f"control_pre rc={rc} green={pre_green}",
                f"mutant removed_line={dropped[:24]}... expected B4 red",
                f"mutant rc={mutant_rc} names_{VICTIM}={named}",
                f"restored_byte_identical={restored} digest={digest_before}",
                f"control_post rc={post_rc} green={post_rc == 0}",
                "",
                "---- mutant gate output (B4 only) ----",
                "\n".join(l for l in mutant_out.splitlines() if "B4" in l or VICTIM in l or "failed" in l or "passed" in l),
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    verdict = pre_green and mutant_rc != 0 and named and restored and post_rc == 0
    print(
        f"control_pre={pre_green} mutant_rc={mutant_rc} names={named} restored={restored} "
        f"control_post={post_rc == 0} verdict={'KILL_OK' if verdict else 'NOT_PROVEN'} log={log}",
        flush=True,
    )
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
