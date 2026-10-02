"""ORD-0550 counter-examples r1 -- does the repaired anchor still bite, and what did the old anchor bite on?

Two things have to be shown, and they are opposite:

  * the old arms were red on bytes that were *legal* (a consumer that asks the settings object, a
    three-line export note above a table). That is the drift the commander ruled to repair, and the
    honest way to show it is to run the tip's own arm file against this tree in the same session --
    not to describe it;
  * the new arms must still go red on the thing each arm actually guards: a second inline copy of the
    request-path lock wait, and the forgiven entry leaving the named table.

The tip versions of the two test files are copied into `backend/tests_tiparm/` (a directory pytest only
collects when named, so it can never leak into the normal suite or into the delivery), and every file
this harness mutates is restored from the bytes it read first and verified by sha256.

usage: python ord0550_mutant_r1.py [case ...]
"""
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = pathlib.Path(os.environ.get("ORD0550_TREE") or str(LANE / "ord0550cut_00b5f25e"))
BACKEND = TREE / "backend"
TIPARM = BACKEND / "tests"  # the copies live beside the real ones so conftest fixtures and sibling imports resolve
TIPARM_NAMES = ["test_qoder_ord0296_write_deadline_tiparm_r1.py",
              "test_qoder_ord0479_dictionary_key_shape_tiparm_r1.py"]
OUT = LANE / "evidence/ord0550/mutant"
TIP = os.environ.get("ORD0550_TIP") or "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"
REPO = r"D:/moodle/CityNexus"
VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"

G4_TIP = "tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"
H01B_TIP = "tests/test_qoder_ord0479_dictionary_key_shape.py::test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable"
SITE_REL = "frontend/src/features/shared/SharedJourneyPanel.tsx"


def tip_bytes(rel: str) -> bytes:
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, rel)],
                          capture_output=True, check=True).stdout


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(paths_and_ids: list, label: str) -> dict:
    log = OUT / ("%s.log" % label)
    env = {k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                                                            "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY")}
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["NO_PROXY"] = "*"
    proc = subprocess.run([VENV, "-m", "pytest", *paths_and_ids, "--tb=line", "-q", "-rf"],
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    log.parent.mkdir(parents=True, exist_ok=True)
    io.open(log, "w", encoding="utf-8", newline="\n").write(proc.stdout + "\n" + proc.stderr)
    fails = sorted({line.split("::")[-1].split(" ")[0]
                    for line in proc.stdout.splitlines() if line.startswith("FAILED ")})
    totals = [line for line in proc.stdout.splitlines() if " passed" in line or " failed" in line]
    return {"rc": proc.returncode, "failed_ids": fails, "summary": totals[-1:], "log": str(log)}


CASES = {
    # baseline: no mutation. The tip arm reads today's tree and must be red (that IS the drift);
    # the repaired arm in the tree must be green.
    "none": [],
    # M1: a legitimate new consumer of the worker-wait shape. The closed filename list of the old arm
    # reddens on it; the number rule must not.
    "new_worker_short_wait_is_not_a_copy": [
        ("create", "backend/app/worker_wait_probe_r1.py",
         'from sqlalchemy import text\n\n\ndef wait(session):\n'
         '    session.execute(text("PRAGMA busy_timeout = 500"))\n'),
    ],
    # M2: the thing the arm actually guards -- a second inline copy of the request-path lock wait.
    "second_inline_copy_of_the_lock_wait": [
        ("create", "backend/app/inline_copy_probe_r1.py",
         'LOCK_WAIT = 30000\nbusy_timeout = 30000\n'),
    ],
    # M3: three lines of comment above the named table -- exactly what ORD-0528 did, and what moved
    # the pin from 45 to 47.
    "export_note_above_the_named_table": [
        ("before_line", SITE_REL, "export const REFUSAL_KEY",
         "// a note that pushes the table down three lines\n// (this is what ORD-0528 did)\n//\n"),
    ],
    # M4: the named anchor itself disappears -- the repaired arm must still go red, or it is decoration.
    "named_table_renamed": [
        ("replace", SITE_REL, "export const REFUSAL_KEY: Record<string, string> = {",
         "export const REFUSAL_KEYS_MOVED_AWAY: Record<string, string> = {"),
    ],
}


def apply(edit, originals):
    kind = edit[0]
    if kind == "create":
        _, rel, body = edit
        path = TREE / rel
        originals.setdefault(rel, None)
        path.write_text(body, encoding="utf-8", newline="\n")
        return {"op": "create", "path": rel}
    _, rel, anchor, payload = edit
    path = TREE / rel
    originals.setdefault(rel, path.read_bytes())
    text = path.read_text(encoding="utf-8")
    if kind == "before_line":
        hits = [i for i, line in enumerate(text.splitlines()) if line.startswith(anchor)]
        assert len(hits) == 1, (rel, anchor, hits)
        lines = text.splitlines()
        lines[hits[0]:hits[0]] = payload.rstrip("\n").splitlines()
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return {"op": "before_line", "path": rel, "anchor": anchor}
    assert text.count(anchor) == 1, (rel, anchor, text.count(anchor))
    path.write_text(text.replace(anchor, payload), encoding="utf-8", newline="\n")
    return {"op": "replace", "path": rel, "anchor": anchor}


def main() -> int:
    wanted = sys.argv[1:] or list(CASES)
    TIPARM.mkdir(parents=True, exist_ok=True)
    tip_g4 = TIPARM / TIPARM_NAMES[0]
    tip_h01b = TIPARM / TIPARM_NAMES[1]
    tip_g4.write_bytes(tip_bytes("backend/tests/test_qoder_ord0296_write_deadline.py"))
    tip_h01b.write_bytes(tip_bytes("backend/tests/test_qoder_ord0479_dictionary_key_shape.py"))
    report = {}
    try:
        for case in wanted:
            edits = CASES[case]
            originals: dict = {}
            applied = []
            try:
                for edit in edits:
                    applied.append(apply(edit, originals))
                new_arms = run([
                    "tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place",
                    "tests/test_qoder_ord0479_dictionary_key_shape.py::test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable",
                ], "%s_newarms" % case)
                old_arms = run([
                    "tests/test_qoder_ord0296_write_deadline_tiparm_r1.py::test_G4_the_lock_wait_is_written_in_exactly_one_place",
                    "tests/test_qoder_ord0479_dictionary_key_shape_tiparm_r1.py::test_H01b_the_shipped_tree_clears_and_every_exemption_is_re_derivable",
                ], "%s_tiparms" % case)
            finally:
                for rel, data in originals.items():
                    path = TREE / rel
                    if data is None:
                        if path.exists():
                            path.unlink()
                    else:
                        path.write_bytes(data)
            restored = []
            for rel, data in originals.items():
                if data is None:
                    restored.append((rel, not (TREE / rel).exists()))
                else:
                    restored.append((rel, digest(TREE / rel) == hashlib.sha256(data).hexdigest()))
            report[case] = {
                "applied": applied,
                "new_arms": new_arms,
                "tip_arms": old_arms,
                "restored": restored,
                "all_restored": all(ok for _, ok in restored),
            }
            sys.stdout.buffer.write(
                ("CASE=%s new_rc=%s new_failed=%s tip_rc=%s tip_failed=%s restored=%s\n"
                 % (case, new_arms["rc"], ",".join(new_arms["failed_ids"]) or "-",
                    old_arms["rc"], ",".join(old_arms["failed_ids"]) or "-",
                    report[case]["all_restored"])).encode("utf-8", "replace"))
    finally:
        for name in TIPARM_NAMES:
            path = TIPARM / name
            if path.exists():
                path.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    io.open(OUT / "mutant_r1_report.json", "w", encoding="utf-8").write(json.dumps(report, indent=1))
    print("REPORT=%s" % (OUT / "mutant_r1_report.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
