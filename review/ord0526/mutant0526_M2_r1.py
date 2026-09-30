"""ORD-0526 mutant M2 · inflate the registered snapshot and show the row-count arm go red.

Not a simulated failure: the shipped registry entry is repointed at an inflated snapshot file inside
the tree, the real product path (`apply_registered_offline_source`) runs against a real store, and the
test module's own arm is what refuses.  Then the entry is restored, the inflated file is removed, the
arm is green again, and both command lines plus the module's file hash are in the receipt.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = Path("D:/moodle/_qoder_seed_ord0489/wt526")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
REG = TREE / "backend/app/catalog_sources.py"
TEST = TREE / "backend/tests/test_ord0526_offline_source_row_count_r1.py"
INFLATED = TREE / "data/replay/_ord0526_inflated_snapshot.json"
OUT = Path("D:/moodle/_qoder_seed_ord0489/evidence/ord0526")
SHIPPED = "data/replay/tianjin_real_snapshot.json"
LIE = "data/replay/_ord0526_inflated_snapshot.json"
MODULE = "tests/test_ord0526_offline_source_row_count_r1.py"


def sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def read_lf(path: Path) -> str:
    """Bytes in, newlines normalised - `Path.write_text` on Windows *adds* CRLF to LF source.

    The first run of this driver restored the registry correctly in content and still failed its own
    hash comparison, because every write through `write_text` flipped the file to CRLF.  A mutation
    run that leaves a product file re-encoded is not a revert, so all writes here go through bytes.
    """

    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write_lf(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def run_pytest() -> dict:
    proc = subprocess.run([PY, "-m", "pytest", MODULE, "-q", "--no-header", "-p", "no:cacheprovider"],
                          cwd=str(TREE / "backend"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    text = (proc.stdout or "") + (proc.stderr or "")
    tail = [line for line in text.splitlines() if line.strip()][-14:]
    return {"cmd": f"{PY} -m pytest {MODULE} -q --no-header -p no:cacheprovider",
            "rc": proc.returncode, "tail": tail}


reg_before = sha(REG)
test_before = sha(TEST)
report: dict = {"at": datetime.now(timezone.utc).isoformat(), "module": MODULE,
                "registry_sha_before": reg_before, "test_sha_before": test_before,
                "python": PY, "cwd": str(TREE / "backend")}

# 0 - the honest baseline really runs green first (a mutant that was already red proves nothing).
report["pass_1_honest"] = run_pytest()

# 1 - the lie: a snapshot that declares five usable rows, of which only three are distinct places.
base = json.loads((TREE / "data/replay/tianjin_real_snapshot.json").read_text(encoding="utf-8"))
rows = [dict(r) for r in base["candidates"][:3]]
rows.append(dict(rows[0]))
rows.append(dict(rows[1]))
lie_payload = {"city_code": base.get("city_code"), "city_name": base.get("city_name"),
               "captured_at": base.get("captured_at"), "candidates": rows}
INFLATED.parent.mkdir(parents=True, exist_ok=True)
write_lf(INFLATED, json.dumps(lie_payload, ensure_ascii=False))
report["inflated_file"] = {"path": str(INFLATED.relative_to(TREE).as_posix()),
                           "bytes": INFLATED.stat().st_size,
                           "rows_written": len(rows),
                           "distinct_external_ids": len({r["external_id"] for r in rows}),
                           "same_name_rows_reused_from": SHIPPED}

text = read_lf(REG)
assert text.count(f'relative_path="{SHIPPED}"') == 1, "registry line not found exactly once"
write_lf(REG, text.replace(f'relative_path="{SHIPPED}"', f'relative_path="{LIE}"'))
report["sabotage"] = {"line_changed_to": LIE, "registry_sha_mutated": sha(REG),
                      "product_files_touched": [str(REG.relative_to(TREE).as_posix())]}
report["pass_2_mutated"] = run_pytest()

# 2 - restore, remove the mutant artefact, prove the arm is green again and the bytes are back.
restored = read_lf(REG).replace(f'relative_path="{LIE}"', f'relative_path="{SHIPPED}"')
write_lf(REG, restored)
INFLATED.unlink()
report["pass_3_restored"] = run_pytest()
report["after"] = {"registry_sha_after": sha(REG), "registry_sha_matches_before": sha(REG) == reg_before,
                   "test_sha_after": sha(TEST), "test_sha_matches_before": sha(TEST) == test_before,
                   "inflated_file_removed": not INFLATED.exists()}

target = OUT / "mutant_M2_row_count.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1))
print("WROTE", target)
