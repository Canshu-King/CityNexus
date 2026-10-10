#!/usr/bin/env python3
"""Commander verification for ORD-0211 (C, commit 0a4cb23): does the backend suite really
open its own temporary database, and does that change what a planted working DB sees?

Three measurements, all read-only against the authoritative tree:

  M1 control (parent 0cd697b, no pin) : plant backend/citynexus.db, run one DB-writing door,
      and expect the planted file to MUTATE.  Without this, M2 could pass vacuously.
  M2 the delivery (0a4cb23)           : same plant, same door, and the planted file must be
      BYTE-IDENTICAL afterwards while the collection receipt names a temp-dir path.
  M3 the boundary that is a refusal   : declare CITYNEXUS_DATABASE_URL ending in `_live.db`
      (a throwaway path that does not exist - the guard must raise before anything opens it)
      and confirm the suite refuses to start rather than honouring the declaration.

Prints one JSON verdict per case; every verdict is computed from measured rows/bytes, never
written as a literal.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path("D:/moodle/_qoder_cmdr_ref_20260921")
OUT_ROOT = REPO / "live_checks" / "ord0211"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"

# The order under test, and the commit it sits on top of (its control).
SHA_PINNED = "0a4cb23"
SHA_CONTROL = "0cd697b"

# A door that definitely writes through the app's database engine.
DOOR = "tests/test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation"

CLEAN_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_DEMO_MODE",
    "CITYNEXUS_DATABASE_URL",
    "DATABASE_URL",
    "CITYNEXUS_LIVE_VALHALLA_URL",
    "CITYNEXUS_PHOTON_BASE_URL",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def export_tree(sha: str, dest: Path) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    tarball = Path(tempfile.gettempdir()) / f"ord0211_{sha}_{os.getpid()}.tar"
    if tarball.exists():
        tarball.unlink()
    proc = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", "-o", str(tarball), sha],
        capture_output=True,
        text=True,
        timeout=300,
    )
    members = 0
    extract_error = None
    try:
        with tarfile.open(tarball, "r") as tf:
            members = len(tf.getnames())
            tf.extractall(dest)
    except Exception as exc:  # noqa: BLE001
        extract_error = repr(exc)[:200]
    try:
        tarball.unlink(missing_ok=True)
    except OSError:
        pass  # a lock on our own temp file must not discard a good export
    backend = dest / "backend"
    conftest = backend / "tests" / "conftest.py"
    return {
        "sha": sha,
        "archive_exit": proc.returncode,
        "archive_stderr": proc.stderr.strip()[:200],
        "tar_members": members,
        "extract_error": extract_error,
        "backend_exists": backend.is_dir(),
        "conftest_present": conftest.is_file(),
        "conftest_bytes": conftest.stat().st_size if conftest.is_file() else None,
        "backend": str(backend),
    }


def plant_working_db(backend: Path) -> tuple[Path, str]:
    """A working ./citynexus.db with one marker row and a real schema table, so any run that
    opens it will mutate it (or at least be observed by its row set)."""
    db = backend / "citynexus.db"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE cmdr_plant (kind TEXT, marker TEXT)")
    con.execute("INSERT INTO cmdr_plant VALUES ('plant', 'ORD-0211-canary')")
    con.commit()
    con.close()
    return db, sha256(db)


def run_pytest(backend: Path, extra_env: dict | None = None) -> dict:
    env = dict(os.environ)
    for key in CLEAN_ENV_KEYS:
        env.pop(key, None)
    env.update(extra_env or {})
    proc = subprocess.run(
        [PYTHON, "-m", "pytest", DOOR, "--tb=line", "-p", "no:randomly", "-rA"],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    blob = proc.stdout + proc.stderr
    receipt = [ln for ln in blob.splitlines() if "ORD-0211 test database" in ln]
    tail = [ln for ln in blob.splitlines() if "passed" in ln or "failed" in ln or "error" in ln]
    # A red g3 names the operation ids it actually observed; count them from the measured line.
    op_ids = len(set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", blob)))
    return {
        "exit": proc.returncode,
        "receipt_line": receipt[0].strip() if receipt else None,
        "summary_line": tail[-1].strip() if tail else None,
        "distinct_uuids_in_output": op_ids,
        "refusal_message": next(
            (ln.strip() for ln in blob.splitlines() if "ORD-0211 boundary" in ln), None
        ),
        "output_tail": blob.strip()[-400:],
    }


def temp_path_named(receipt_line: str | None) -> bool:
    if not receipt_line:
        return False
    after = receipt_line.split("resolved=", 1)
    if len(after) < 2:
        return False
    target = after[1].split("|", 1)[0].strip()
    return "cnx_pytest_" in target.replace("\\", "/")


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    verdicts: list[dict] = []

    # ---- M1 control: no pin => the planted working DB is the run's target --------------------
    ctl = export_tree(SHA_CONTROL, REPO / "v_ord0211_control")
    ctl_db, ctl_before = plant_working_db(Path(ctl["backend"]))
    ctl_run = run_pytest(Path(ctl["backend"]))
    ctl_after = sha256(ctl_db)
    verdicts.append(
        {
            "case": "M1_control_no_pin",
            "sha": ctl["sha"],
            "backend": ctl["backend"],
            "run": ctl_run,
            "plant_sha_before": ctl_before,
            "plant_sha_after": ctl_after,
            "plant_mutated": ctl_after != ctl_before,
            "verdict": "HARNESS_INVALID"
            if ctl_run["exit"] not in (0, 1)
            else ("CONTROL_SHOWS_LEAK" if ctl_after != ctl_before else "CONTROL_DID_NOT_LEAK"),
        }
    )

    # ---- M2 the delivery: pin => planted working DB untouched, receipt names a temp path -----
    pinned = export_tree(SHA_PINNED, REPO / "v_ord0211_pinned")
    p = Path(pinned["backend"])
    pin_db, pin_before = plant_working_db(p)
    pin_run = run_pytest(p)
    pin_after = sha256(pin_db)
    temp_named = temp_path_named(pin_run["receipt_line"])
    # Did the run create a stray citynexus.db anywhere new, or a WAL beside our plant?
    sidecars = sorted(x.name for x in p.glob("citynexus.db*"))
    checks = {
        "plant_untouched": pin_after == pin_before,
        "receipt_names_temp_dir": temp_named,
    }
    informational = {
        # Informational only: this delivery is about WHICH database the suite opens, not about the
        # colour of the door it runs.  The door used here is a known-red product gate.
        "door_exit_code": pin_run["exit"],
        "door_colour": "GREEN" if pin_run["exit"] == 0 else "RED",
    }
    verdicts.append(
        {
            "case": "M2_pinned",
            "sha": pinned["sha"],
            "backend": pinned["backend"],
            "conftest_bytes": pinned["conftest_bytes"],
            "run": pin_run,
            "plant_sha_before": pin_before,
            "plant_sha_after": pin_after,
            "plant_untouched": pin_after == pin_before,
            "receipt_names_temp_dir": temp_named,
            "working_db_sidecars_after_run": sidecars,
            "checks": checks,
            "informational_not_a_condition": informational,
            "verdict": "PASS"
            if all(checks.values())
            else "FAIL[" + ",".join(k for k, v in checks.items() if not v) + "]",
        }
    )

    # ---- M3 the refusal branch: a declared `_live.db` target must stop the suite -------------
    fake = Path(tempfile.mkdtemp(prefix="cmdr_not_live_")) / "_live.db"
    guard_run = run_pytest(p, extra_env={"CITYNEXUS_DATABASE_URL": f"sqlite:///{fake.as_posix()}"})
    refused = guard_run["exit"] != 0 and guard_run["refusal_message"] is not None
    verdicts.append(
        {
            "case": "M3_refuses_declared_live_target",
            "declared_url": f"sqlite:///{fake.as_posix()}",
            "declared_path_existed_before": fake.exists(),
            "declared_path_exists_after": fake.exists(),
            "run": guard_run,
            "verdict": "REFUSES" if refused else "DOES_NOT_REFUSE",
        }
    )

    # ---- Cross-check the control's claim, computed not assumed -------------------------------
    m1 = next(v for v in verdicts if v["case"] == "M1_control_no_pin")
    m2 = next(v for v in verdicts if v["case"] == "M2_pinned")
    verdicts.append(
        {
            "case": "M4_conclusion",
            "control_leaked": m1["verdict"],
            "delivery": m2["verdict"],
            "non_vacuous": m1["plant_mutated"] is True,
            "note": "M2 only means anything because M1 shows the same plant does mutate a file "
            "when the pin is absent.",
        }
    )

    print(json.dumps(verdicts, ensure_ascii=False, indent=2))
    (OUT_ROOT / "receipt.json").write_text(
        json.dumps(verdicts, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
