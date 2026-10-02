"""Counter-arms for the ORD-0545 slice 4 walkthrough: the per-cell comparison has to bite.

The walkthrough claims each cell shows *this cell's* sentence, in *this locale's* half, with the numbers
the server actually answered.  Three ways that claim can be hollow, one mutation each:

  M1  make one cell bypass the table and print its key name instead (the ORD-0533 symptom, produced on
      purpose).  Expect red on that cell -- which is what proves the arm compares sentences, not merely
      "something is where the sentence should be".
  M2  swap two of the four parameters the counts line is built from (send `resolved` where `extracted`
      belongs).  The build stays green, because all four names exist; only the glass can catch it.
  M3  repoint the verify-warning cell at another real table key (`retry`).  Expect red on that cell: the
      stale-map guard and the text comparison must agree that it stopped saying what it means.

  What this tool learned the hard way: an earlier M1 edited the table's own wording, and the controls
  stayed green -- because this arm derives every expectation from the shipped table, a wording change is
  invisible to it by construction.  That claim belongs to the dictionary review, not to a screen gate, so
  M1 was replaced with a mutation that decouples a cell from its sentence.  Both readings are in the log.

Everything is restored from the bytes read at the start, re-hashed, and bracketed by green controls.
Mutant-generation evidence is not published; this receipt is.

Two things this tool now does because they burned it once: it reaps a vite left on its own frontend
port (a killed run orphaned one, and the next gate then hung for seven minutes on a port it could not
bind), and it writes the receipt after every step, so an interrupted run still leaves what it measured.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/walkthrough_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
TABLE = FRONTEND / "src/features/poiimport/poiImportCopy.ts"
PANEL = FRONTEND / "src/features/poiimport/PoiImportPanel.tsx"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
LOCK = DATA / "walkthrough_counterarm.lock"
RECEIPT = DATA / "walkthrough_counterarms.txt"
BASE_TIP = "4fac49f371da0820393d038700bddddafd1176d1"
CONFIG = "playwright.ord0545s4-walkthrough.config.ts"
FRONTEND_PORT = 4916
BACKEND_PORT = 4911

M1_OLD = 't("poiImport.cardMatched")'
M1_NEW = 't("poiImport.cardMutatedKey")'
M2_OLD = "extracted: parsed?.counts.extracted ?? 0,"
M2_NEW = "extracted: parsed?.counts.resolved ?? 0,"
M3_OLD = '{poiImportCopy(locale, "verifyWarning")}'
M3_NEW = '{poiImportCopy(locale, "retry")}'

CARD = FRONTEND / "src/components/PoiCandidateCard.tsx"
TRACKED = (CARD, PANEL)
MUTATIONS = (
    ("M1_card_cell_asks_for_a_key_nobody_defined", CARD, M1_OLD, M1_NEW),
    ("M2_counts_slot_swapped", PANEL, M2_OLD, M2_NEW),
    ("M3_verify_warning_repointed", PANEL, M3_OLD, M3_NEW),
)

LOG: list[str] = []


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def flush(extra: str = "") -> None:
    body = LOG + ([extra] if extra else [])
    RECEIPT.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")


def rows(port: int) -> list[list[str]]:
    out = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout
    found = []
    for line in out.splitlines():
        cols = line.split()
        if (
            len(cols) >= 5
            and cols[0].startswith("TCP")
            and cols[1].endswith(":" + str(port))
            and cols[3] == "LISTENING"
        ):
            found.append(cols)
    return found


def command_line(pid: str) -> str:
    got = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(pid) + "\").CommandLine"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    return got.strip()


def reap_orphan_frontend() -> list[str]:
    """Kill only a vite on THIS lane's own frontend port whose command line says so."""
    killed = []
    for cols in rows(FRONTEND_PORT):
        pid = cols[4]
        line = command_line(pid)
        if "vite.js" in line and ("--port " + str(FRONTEND_PORT)) in line:
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
            killed.append(pid)
    return killed


def preflight() -> None:
    """One instance at a time; and never sit on a port somebody else holds: reap ours, else abort."""
    if LOCK.exists():
        raise SystemExit("ABORT: another instance owns the lock " + str(LOCK))
    reap = reap_orphan_frontend()
    if rows(FRONTEND_PORT):
        raise SystemExit("ABORT: port " + str(FRONTEND_PORT) + " is held by something this tool does not own")
    if not rows(BACKEND_PORT):
        raise SystemExit("ABORT: this lane's backend on " + str(BACKEND_PORT) + " is not up")
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    LOG.append("preflight reaped_orphan_vite=" + str(reap) + " at=" + stamp())


def cleanup() -> None:
    reap_orphan_frontend()
    if LOCK.exists():
        LOCK.unlink()


def gate(tag: str) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_ORD0545_TAG": tag,
        "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
        "CITYNEXUS_ORD0545S4_PORT": str(FRONTEND_PORT),
        "CITYNEXUS_ORD0545_BACKEND_PORT": str(BACKEND_PORT),
        "DEEPSEEK_API_KEY": "",
    })
    started = time.time()
    try:
        done = subprocess.run(
            ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG],
            cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300, env=env,
        )
        out = (done.stdout or "") + (done.stderr or "")
        code = done.returncode
    except subprocess.TimeoutExpired as exp:
        # text=True means these arrive as str already; a bare decode() threw on exactly this path
        pieces = [exp.stdout, exp.stderr]
        out = "".join(x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "") for x in pieces)
        code = "TIMEOUT"
    # keep whatever the run said, green or not: a timeout without its output is not evidence
    (DATA / ("gate_" + tag + ".txt")).write_text(out, encoding="utf-8", newline="\n")
    collected = re.search(r"Running (\d+) tests", out)
    failed = re.search(r"(\d+) failed", out)
    passed = re.search(r"(\d+) passed", out)
    reading = {
        "measured_at": stamp(),
        "wall_seconds": round(time.time() - started, 1),
        "rc": code,
        "tests_collected": int(collected.group(1)) if collected else 0,
        "passed": int(passed.group(1)) if passed else 0,
        "failed": int(failed.group(1)) if failed else 0,
        "red_cells": sorted(set(re.findall(r"/ ([a-z_0-9]+) must paint", out))),
        "stale_map_failures": sorted(set(re.findall(r"([a-z_0-9]+): the shipped source no longer routes", out))),
    }
    reap_orphan_frontend()
    return reading


def patch(path: pathlib.Path, old: str, new: str) -> bytes:
    original = path.read_bytes()
    text = original.decode("utf-8")
    if old not in text:
        raise SystemExit("ABORT: the shipped text moved under this tool: " + old[:48])
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    return original


def main() -> int:
    preflight()
    try:
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in TRACKED}
        LOG.append("base_tip=" + BASE_TIP)
        LOG.append("started_at=" + stamp())
        LOG.append("card_before=" + before[CARD])
        LOG.append("panel_before=" + before[PANEL])
        flush()

        control_pre = gate("ctrlpre")
        LOG.append("control_pre " + str(control_pre))
        flush()

        outcomes = []
        for name, path, old, new in MUTATIONS:
            original = patch(path, old, new)
            try:
                reading = gate(name)
            finally:
                path.write_bytes(original)
            restored = hashlib.sha256(path.read_bytes()).hexdigest() == before[path]
            outcomes.append((name, reading, restored))
            LOG.append(name + " " + str(reading) + " restored=" + str(restored))
            flush()

        control_post = gate("ctrlpost")
        LOG.append("control_post " + str(control_post))

        # mutant generations describe a tree that does not ship, so their evidence files are dropped and
        # this receipt is the only artifact of them; the store behind all of it is this lane's own copy
        readouts = ROOT / "review/ord0545/readouts"
        for tag in ["ctrlpre", "ctrlpost"] + [name for name, _, _, _ in MUTATIONS]:
            for stray in readouts.glob("*_" + tag + ".json"):
                stray.unlink()

        verdict = (
            control_pre["rc"] == 0
            and control_pre["tests_collected"] == 2
            and control_post["rc"] == 0
            and all(r["rc"] != 0 and r["rc"] != "TIMEOUT" and r["failed"] >= 1 and restored
                    for (_, r, restored) in outcomes)
        )
        LOG.append("verdict = " + ("KILL_OK three mutations, controls green both sides" if verdict else "NOT_PROVEN"))
        LOG.append("ended_at=" + stamp())
        for path in TRACKED:
            if hashlib.sha256(path.read_bytes()).hexdigest() != before[path]:
                LOG.append("UNRESTORED " + path.name)
        flush()
        return 0 if verdict else 1
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
