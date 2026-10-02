"""ORD-0550 -- the guardian file, alone, on both generations: is its red mine or the suite's?

Two arms of `test_sol_guardian_projection.py` swapped places between the tip run and the candidate run:
`..._carries_the_fields_the_panel_selects_on` greened, `test_guardian_status_lists_runs_newest_first`
went red. Neither file is touched by this order -- the only two files here are the write-deadline ruler
and the dictionary-key ruler -- but "not mine" has to be measured, not asserted: run the guardian file
by itself against each generation's bytes and record what it says. If it is quiet alone on both sides,
the red belongs to the shared-state ordering of the whole-suite run, which is a known shape of this file
and not something these two arms can cause.

usage: python ord0550_guardian_isolation_r1.py
"""
import io
import json
import os
import pathlib
import re
import subprocess

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = pathlib.Path(os.environ.get("ORD0550_TREE") or str(LANE / "ord0550cut_00b5f25e"))
BACKEND = TREE / "backend"
OUT = LANE / "evidence/ord0550"
VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REPO = r"D:/moodle/CityNexus"
TIP = os.environ.get("ORD0550_TIP") or "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"
MY_FILES = [
    "backend/tests/test_qoder_ord0296_write_deadline.py",
    "backend/tests/test_qoder_ord0479_dictionary_key_shape.py",
]
TARGET = "tests/test_sol_guardian_projection.py"


def tip_bytes(rel: str) -> bytes:
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, rel)],
                          capture_output=True, check=True).stdout


def run(label: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY")}
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["NO_PROXY"] = "*"
    proc = subprocess.run([VENV, "-m", "pytest", TARGET, "--tb=no", "-rf", "-q"],
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    io.open(OUT / ("guardian_alone_%s.log" % label), "w", encoding="utf-8", newline="\n").write(
        proc.stdout + "\n" + proc.stderr)
    text = proc.stdout
    return {"rc": proc.returncode,
            "failed": sorted(set(re.findall(r"^FAILED (\S+)$", text, re.M))),
            "totals": [line.strip() for line in text.splitlines() if " passed" in line or " failed" in line][-1:]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    originals = {rel: (TREE / rel).read_bytes() for rel in MY_FILES}
    report = {}
    try:
        report["candidate_bytes"] = run("candidate")
        for rel in MY_FILES:
            (TREE / rel).write_bytes(tip_bytes(rel))
        report["tip_bytes"] = run("tip")
    finally:
        restored = {}
        for rel, data in originals.items():
            (TREE / rel).write_bytes(data)
            restored[rel] = (TREE / rel).read_bytes() == data
        report["restored_ok"] = restored
    io.open(OUT / "guardian_isolation_r1.json", "w", encoding="utf-8").write(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1).encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
