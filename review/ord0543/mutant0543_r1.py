"""ORD-0543 mutants: prove the widening is what composes the day, and the real windows still bind it.

M1 removes the band fallback (a stop with no stated hours is skipped again) - the arms that need an
unsourced stop to be scheduled must go red.
M2 applies the band to *every* stop, i.e. ignores stated opening hours - the arm that pins a real
window must go red, which is what shows the widening did not replace evidence with a default.

Each mutant is put back and the file's blob hash is compared with the pre-mutant hash, so the
receipt states in bytes that nothing was left behind.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = Path("D:/moodle/_qoder_seed_ord0489/wt543")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
MODULE = "tests/test_ord0543_day_sequence_leg_r1.py"
TARGET = TREE / "backend/app/services.py"
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0543")
OUT.mkdir(parents=True, exist_ok=True)

BAND_USE = '''            window = _place_window(place)
            if window is None:
                if band is None:
                    continue
                opened, closed = band
            else:
                opened, closed = window'''
M1_TEXT = '''            window = _place_window(place)
            if window is None:
                continue'''
M2_TEXT = '''            window = _place_window(place)
            opened, closed = band if band is not None else (window or (day_start_minutes, day_end_minutes))'''


def read() -> str:
    return TARGET.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write(text: str) -> None:
    TARGET.write_bytes(text.encode("utf-8"))


def blob() -> str:
    return subprocess.run(["git", "-C", str(TREE), "hash-object", str(TARGET)],
                          capture_output=True, text=True).stdout.strip()


def pytest(modules: list[str]) -> dict:
    proc = subprocess.run([PY, "-m", "pytest", *modules, "-q", "--no-header", "-p", "no:cacheprovider"],
                          cwd=str(TREE / "backend"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    lines = [l for l in text.splitlines() if l.strip()]
    return {"cmd": f"pytest {' '.join(modules)} -q", "rc": proc.returncode,
            "tail": lines[-8:], "failed_nodes": [l for l in text.splitlines() if l.startswith("FAILED")],
            "named": [l for l in text.splitlines() if l.startswith("E   ")][:2]}


original = read()
before = blob()
report: dict = {"at": datetime.now(timezone.utc).isoformat(), "blob_before": before}
assert original.count(BAND_USE) == 1, "the band-fallback block was not found exactly once"

report["pass_0_baseline"] = pytest([MODULE])

# M1 - the widening taken back out
write(original.replace(BAND_USE, M1_TEXT))
report["M1"] = {"change": "a stop with no stated hours is skipped again (pre-fix behaviour)",
                "blob_mutated": blob()}
report["M1"]["run"] = pytest([MODULE])
write(original)
report["M1"]["restored_matches"] = blob() == before

# M2 - the band applied to every stop, stated hours ignored
text_m2 = read().replace(BAND_USE, M2_TEXT)
assert text_m2 != read()
write(text_m2)
report["M2"] = {"change": "the working band used for every stop, so stated open/close is ignored",
                "blob_mutated": blob()}
report["M2"]["run"] = pytest([MODULE])
write(original)
report["M2"]["restored_matches"] = blob() == before

report["pass_3_after_restores"] = pytest([MODULE])
report["blob_after"] = blob()
report["all_restored"] = report["blob_after"] == before and report["M1"]["restored_matches"] \
    and report["M2"]["restored_matches"]
report["git_status_backend_app"] = subprocess.run(
    ["git", "-C", str(TREE), "status", "--porcelain", "--", "backend/app"],
    capture_output=True, text=True).stdout.splitlines()

target = OUT / "mutants_M1_M2.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1)[:3600])
print("WROTE", target)
