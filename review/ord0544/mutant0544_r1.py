"""ORD-0544 mutants: take each fix out and show the named arm goes red, then put it back.

Two fixes, two mutants, one run:

  M1  restore the pre-fix parse in `PhotonCityAnchor.search` (`.json().get("features")` with the
      old three-class except).  The leg then escapes as `AttributeError`, the capture demotes to
      replay, the rows are keyed `openstreetmap-replay`, and the warm pass pays the network again -
      so `test_unreadable_anchor_answer_costs_one_leg_not_the_capture` must fail.
  M2  pin `outcome_qualifier` to `None`.  `test_already_current_says_which_fact_made_it_current`
      must fail on it, while the refusal arm keeps passing (a null is correct *there*), which is
      what shows the arm bites the value rather than the field's existence.

After each mutant the file is restored and its blob hash compared with the pre-mutant hash, so the
receipt says in bytes that nothing was left behind.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = Path("D:/moodle/_qoder_seed_ord0489/wt544")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
MODULE = "tests/test_ord0544_anchor_leg_shape_r1.py"
DISCOVERY = "tests/test_qoder_anywhere_discovery_truth.py"
REAL_CITY = TREE / "backend/app/integrations/discovery/real_city.py"
HYDRATION = TREE / "backend/app/catalog_hydration_operations.py"
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0544")
OUT.mkdir(parents=True, exist_ok=True)

FIXED_PARSE = '''            if not isinstance(payload, dict):'''
OLD_PARSE = '''            try:
                for feature in (response.json().get("features") or []):'''


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def blob(path: Path) -> str:
    return subprocess.run(["git", "-C", str(TREE), "hash-object", str(path)],
                          capture_output=True, text=True).stdout.strip()


def pytest(modules: list[str]) -> dict:
    proc = subprocess.run([PY, "-m", "pytest", *modules, "-q", "--no-header", "-p", "no:cacheprovider"],
                          cwd=str(TREE / "backend"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    tail = [line for line in text.splitlines() if line.strip()][-10:]
    return {"cmd": f"{PY} -m pytest {' '.join(modules)} -q --no-header -p no:cacheprovider",
            "rc": proc.returncode, "tail": tail,
            "failed_nodes": [l for l in text.splitlines() if l.startswith("FAILED")]}


report: dict = {"at": datetime.now(timezone.utc).isoformat(), "tree": str(TREE),
                "tree_head": subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                                            capture_output=True, text=True).stdout.strip()}
rc_before = blob(REAL_CITY)
hy_before = blob(HYDRATION)
report["blobs_before"] = {"real_city.py": rc_before, "catalog_hydration_operations.py": hy_before}

report["pass_0_baseline"] = pytest([MODULE])
report["pass_0_g16"] = pytest([DISCOVERY])

# ---- M1: make the unreadable body escape again ----
# Two edits, each checked to hit exactly once, and together they are the old behaviour: the guard
# stops rejecting a non-object body, and the except tuple loses `AttributeError` - so a list body
# reaches `.get("features")` and raises out of the leg instead of being recorded as one leg missing.
text = read(REAL_CITY)
assert text.count('            if not isinstance(payload, dict):') == 1
assert text.count('except (ValueError, KeyError, TypeError, AttributeError, IndexError):') == 1
text_m1 = text.replace('            if not isinstance(payload, dict):',
                       '            if payload is None:')
text_m1 = text_m1.replace('except (ValueError, KeyError, TypeError, AttributeError, IndexError):',
                          'except (ValueError, KeyError, TypeError):')
assert text_m1 != text
write(REAL_CITY, text_m1)
report["M1"] = {"guard_weakened_to": "if payload is None:",
                "except_tuple_restored_to": "(ValueError, KeyError, TypeError)",
                "blob_mutated": blob(REAL_CITY)}
report["M1"]["run"] = pytest([MODULE])
write(REAL_CITY, text)
report["M1"]["restored_blob_matches"] = blob(REAL_CITY) == rc_before

# ---- M2: pin the sub-word to null ----
hy_text = read(HYDRATION)
qualifier_block = '''            "outcome_qualifier": (
                OUTCOME_QUALIFIER_OFFLINE_SOURCE
                if applied is not None and int(applied.get("places_written") or 0) > 0
                else OUTCOME_QUALIFIER_ALREADY_HELD
                if outcome == OUTCOME_ALREADY_CURRENT
                else None
            ),'''
assert hy_text.count(qualifier_block) == 1, "M2 target not found exactly once"
write(HYDRATION, hy_text.replace(qualifier_block, '            "outcome_qualifier": None,'))
report["M2"] = {"what_was_pinned": "outcome_qualifier -> None", "blob_mutated": blob(HYDRATION)}
report["M2"]["run"] = pytest([MODULE])
write(HYDRATION, hy_text)
report["M2"]["restored_blob_matches"] = blob(HYDRATION) == hy_before

report["pass_3_after_restores"] = pytest([MODULE])
report["pass_3_g16"] = pytest([DISCOVERY])
report["blobs_after"] = {"real_city.py": blob(REAL_CITY), "catalog_hydration_operations.py": blob(HYDRATION)}
report["git_status_porcelain_lines"] = subprocess.run(
    ["git", "-C", str(TREE), "status", "--porcelain", "--", "backend/app"],
    capture_output=True, text=True).stdout.count("\n")

target = OUT / "mutants_M1_M2.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1)[:4000])
print("WROTE", target)
