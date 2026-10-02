"""ORD-0550 -- the same suite on the tip's bytes, one instrument, same machine, same hour.

The commander's day18 reading was `9 failed, 1656 passed`; my candidate run came back `10 failed,
1655 passed`. Those two numbers are not a comparison: nine of the ten reds in each are the network and
guardian families, which answer to the campus link and to shared state, and his run was taken at a
different hour on a different tree. So this reverts *only* the two test files this order edits back to
the tip's bytes, runs the identical command, and restores them with the sha256 checked -- which is what
turns "I added a red" or "I removed a red" into something I am allowed to say.

usage: python ord0550_suite_tip_r1.py
"""
import hashlib
import io
import os
import pathlib
import re
import subprocess

TREE = pathlib.Path(os.environ.get("ORD0550_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0550cut_00b5f25e")
BACKEND = TREE / "backend"
EVID = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0550")
VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
REPO = r"D:/moodle/CityNexus"
TIP = os.environ.get("ORD0550_TIP") or "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"
FILES = [
    "backend/tests/test_qoder_ord0296_write_deadline.py",
    "backend/tests/test_qoder_ord0479_dictionary_key_shape.py",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reds(log: pathlib.Path):
    text = io.open(log, encoding="utf-8", errors="replace").read()
    return sorted({m for m in re.findall(r"^FAILED (\S+)$", text, re.M)}), text


def main() -> int:
    EVID.mkdir(parents=True, exist_ok=True)
    originals = {}
    for rel in FILES:
        path = TREE / rel
        originals[rel] = path.read_bytes()
        out = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, rel)],
                             capture_output=True, check=True)
        path.write_bytes(out.stdout)
    log = EVID / "suite_tip_r1.log"
    env = {k: v for k, v in os.environ.items()
           if k not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY")}
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["NO_PROXY"] = "*"
    try:
        proc = subprocess.run(
            [VENV, "-m", "pytest", "tests/",
             "--ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py", "--tb=no", "-rf", "-q"],
            cwd=str(BACKEND), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        restored = {}
        for rel, data in originals.items():
            (TREE / rel).write_bytes(data)
            restored[rel] = digest((TREE / rel).read_bytes()) == digest(data)
    io.open(log, "w", encoding="utf-8", newline="\n").write(proc.stdout + "\n" + proc.stderr)
    tip_reds, text = reds(log)
    cand_reds, _ = reds(EVID / "suite_cand_r1.log")
    totals = re.findall(r"^\s*(\d+) (passed|failed|skipped|xfailed)", text, re.M)
    report = io.open(EVID / "suite_diff_r1.txt", "w", encoding="utf-8", newline="\n")
    report.write("tip run totals: %s\n" % ", ".join("%s %s" % (n, k) for n, k in totals))
    report.write("candidate run totals: 10 failed, 1655 passed, 22 skipped, 1 xfailed\n")
    report.write("restored_ok: %s\n\n" % restored)
    report.write("red on TIP only (this order turned them green):\n")
    for item in sorted(set(tip_reds) - set(cand_reds)):
        report.write("  %s\n" % item)
    report.write("red on CANDIDATE only (this order added them):\n")
    for item in sorted(set(cand_reds) - set(tip_reds)):
        report.write("  %s\n" % item)
    report.write("red on both (%d):\n" % len(set(tip_reds) & set(cand_reds)))
    for item in sorted(set(tip_reds) & set(cand_reds)):
        report.write("  %s\n" % item)
    report.close()
    print(io.open(EVID / "suite_diff_r1.txt", encoding="utf-8").read().encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
