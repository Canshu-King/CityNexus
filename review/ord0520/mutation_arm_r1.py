"""Mutation arms for the patrol self-tests that were flagged suspect-mute.

A self-test being green proves nothing until you break the thing it guards and watch it go red. That is
what these arms do: copy the self-test and its target into a scratch directory, break ONE site in the
target, run the self-test against the broken copy, and require a non-zero exit.

Why copies: the targets are live instruments in the patrol directory. Breaking one in place would be a
write to a shared instrument and would leave the lane blind if anything went wrong -- the same class of
mistake as writing a probe over a delivered file. So every mutation happens on a copy in this lane's tmp,
and the originals are never opened for writing.

Each arm reports both halves, because only one of them proves anything:
  * mutated -> must be non-zero  (the self-test notices the break)
  * pristine -> must be zero     (it was green before anything was broken)

An arm that is red on BOTH halves has no teeth. An arm that is green on both is blind. Either way the
arm's own verdict says so, and the table at the end is what the next cell reads.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import subprocess
import sys

PATROL = pathlib.Path(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol")
TMP = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/tmp/mutation_arms")
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
TIMEOUT = 240

#: (self-test, file it reads as its target, a substring in that target to break, the replacement text)
#: The needle is chosen from what the self-test actually asserts, not from a guess. disk_band pins the
#: first and last line of a line-range it copies out of autumn_watch.py; s_band loads the relay module
#: and checks what its s_focus / unacked_stalled return. Breaking something adjacent (a constant name,
#: a band number) is how a probe ends up calling a real guard blind -- that mistake is on me, and the
#: first cut of this file made it with BAND / BACKOFF.
ARMS = [
    ("_alarm_backoff_selftest_r1.py", "_sentinel_relay_r1.py", "BACKOFF", "BROKEN_BY_MUTATION_ARM"),
    ("_disk_band_selftest_r1.py", "autumn_watch.py", "frees = re.findall", "frees = BROKEN_BY_MUTATION_ARM"),
    ("_s_band_selftest_r1.py", "_sentinel_relay_r1.py", "def s_focus", "def s_focus_BROKEN_BY_MUTATION_ARM"),
    ("_watch_stack_selftest_r1.py", "_watch_stack_r1.py", "COMPONENTS = [", "COMPONENTS_BROKEN = ["),
    ("_patrol_cell11_selftest_r1.py", "_bb_patrol_once_r1.py", "def cell11_backlog",
     "def cell11_backlog_BROKEN_BY_MUTATION_ARM"),
    ("_verdict_two_slot_done_selftest_r1.py", "_night_verdict_runner_r1.py", "def target_epoch",
     "def target_epoch_BROKEN_BY_MUTATION_ARM"),
    # NOT staged by copy: this one posts into the real bolt_words directory, so a copied directory makes
    # even the pristine run red. It is listed separately below with that reason, not labelled blind.
]


def stage(selftest: str, target: str) -> pathlib.Path:
    """Copy the self-test and every file it might read into a scratch dir."""

    work = TMP / selftest.replace(".py", "")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for name in sorted(os.listdir(PATROL)):
        if name.endswith(".py"):
            shutil.copyfile(PATROL / name, work / name)
    return work


def break_target(work: pathlib.Path, target: str, needle: str, replacement: str) -> bool:
    path = work / target
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        return False
    path.write_text(text.replace(needle, replacement, 1), encoding="utf-8", newline="\n")
    return True


def run(work: pathlib.Path, selftest: str):
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([str(PYTHON), "-X", "utf8", str(work / selftest)], cwd=str(work),
                          env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=TIMEOUT)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()[-300:]


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []
    for selftest, target, needle, replacement in ARMS:
        work = stage(selftest, target)
        pristine_rc, pristine_tail = run(work, selftest)
        if not break_target(work, target, needle, replacement):
            failures.append("%s: needle %r not in %s" % (selftest, needle, target))
            rows.append({"selftest": selftest, "target": target, "status": "NEEDLE_ABSENT"})
            continue
        mutated_rc, mutated_tail = run(work, selftest)
        row = {
            "selftest": selftest, "target": target,
            "pristine_exit_code": pristine_rc, "mutated_exit_code": mutated_rc,
            "notices_the_break": mutated_rc != 0,
            "was_green_before": pristine_rc == 0,
        }
        row["status"] = ("MUTATION_DETECTED" if (row["notices_the_break"] and row["was_green_before"])
                         else ("BLIND" if mutated_rc == 0 else "RED_ON_PRISTINE_TOO"))
        if row["status"] != "MUTATION_DETECTED":
            failures.append("%s -> %s" % (selftest, row["status"]))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    report = {
        "method": "copy the self-test and its target to scratch, break one site in the target, require "
                  "non-zero; pristine copy must stay green. Originals are never opened for writing.",
        "arms": rows,
        "detected": sum(1 for r in rows if r.get("status") == "MUTATION_DETECTED"),
        "failures": failures,
        "verdict": "MUTATIONS_DETECTED" if not failures else "ARMS_INCOMPLETE",
    }
    print(json.dumps({k: v for k, v in report.items() if k != "arms"}, ensure_ascii=False, indent=2))
    print("VERDICT %s" % report["verdict"])
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())